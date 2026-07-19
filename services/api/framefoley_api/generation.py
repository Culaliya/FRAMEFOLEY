"""Bounded generation modes and deterministic cached-demo processing."""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from genblaze_core import KeyStrategy, Manifest, Modality, ObjectStorageSink, Pipeline
from genblaze_core.providers import RetryPolicy
from genblaze_elevenlabs import ElevenLabsSFXProvider
from genblaze_s3 import S3StorageBackend

from framefoley_api.errors import PublicError
from framefoley_api.events import EventLog
from framefoley_api.media import convert_wav_to_ogg
from framefoley_api.models import (
    ApiError,
    FrameFoleyProject,
    GenerationCandidate,
    ProjectState,
    QcReport,
    QcVerdictValue,
    SoundEvent,
)
from framefoley_api.prompting import EVENT_WINDOWS, build_prompt
from framefoley_api.repository import ProjectRepository, project_prefix
from framefoley_api.settings import Settings
from framefoley_api.state import transition
from framefoley_spike.qc import QcReport as SpikeQcReport
from framefoley_spike.qc import QcVerdict, inspect_audio, render_waveform, repair_audio

LIVE_MODEL = "eleven_text_to_sound_v2"
LIVE_PROVIDER = "elevenlabs-sfx"
LIVE_PIPELINE_NAME = "framefoley-phase1-sfx"


def _candidate_id() -> str:
    return "cand_" + secrets.token_hex(6)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _candidate_error(error: Exception) -> ApiError:
    if isinstance(error, PublicError):
        return ApiError(
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            request_id="req_pipeline0000",
        )
    return ApiError(
        code="CANDIDATE_PIPELINE_FAILED",
        message="The candidate could not complete deterministic processing.",
        retryable=False,
        request_id="req_pipeline0000",
    )


def _api_qc(report: SpikeQcReport, *, repairs: tuple[str, ...] = ()) -> QcReport:
    metrics = report.metrics
    verdict_map: dict[QcVerdict, QcVerdictValue] = {
        QcVerdict.PASS: "pass",
        QcVerdict.REPAIRABLE: "repairable",
        QcVerdict.REGENERATE: "regenerate",
        QcVerdict.FAILED: "failed",
    }
    return QcReport(
        verdict=verdict_map[report.verdict],
        duration_seconds=metrics.duration_seconds or 0.0,
        sample_rate_hz=metrics.sample_rate_hz or 1,
        channels=metrics.channels or 1,
        peak_dbfs=metrics.peak_dbfs if metrics.peak_dbfs is not None else -120.0,
        rms_dbfs=metrics.rms_dbfs if metrics.rms_dbfs is not None else -120.0,
        leading_silence_ms=metrics.leading_silence_ms or 0.0,
        trailing_silence_ms=metrics.trailing_silence_ms or 0.0,
        reasons=list(report.reasons),
        repairs=list(repairs),
        sha256=metrics.sha256,
    )


class GenerationService:
    def __init__(
        self,
        settings: Settings,
        repository: ProjectRepository,
        events: EventLog,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.events = events

    def generate(self, project: FrameFoleyProject) -> FrameFoleyProject:
        if self.settings.generation_mode == "disabled":
            raise PublicError(
                "LIVE_GENERATION_DISABLED",
                "Live generation is closed. The cached demo project remains available.",
                status_code=503,
            )
        if len(project.events) not in {1, 2, 3}:
            raise PublicError(
                "EVENT_COUNT_INVALID",
                "Add between one and three events.",
                status_code=409,
            )
        transition(project, ProjectState.GENERATING)
        self.repository.save(project)
        self.events.publish(project.id, "project.state", {"state": "generating"})
        if self.settings.generation_mode == "demo":
            return self._generate_cached_demo(project)
        return self._generate_live(project)

    def _publish_candidate(
        self,
        project: FrameFoleyProject,
        event: SoundEvent,
        candidate: GenerationCandidate,
    ) -> None:
        self.events.publish(
            project.id,
            "candidate.status",
            {"status": candidate.status, "sourceLabel": candidate.source_label},
            event_id=event.id,
            candidate_id=candidate.id,
        )
        self.repository.save(project)

    def _generate_cached_demo(self, project: FrameFoleyProject) -> FrameFoleyProject:
        if project.source is None or project.source.origin != "demo":
            raise PublicError(
                "DEMO_MODE_SOURCE_REQUIRED",
                "Demo generation is limited to the built-in JELLY RELAY project.",
                status_code=409,
            )
        project.evidence_label = "CACHED DEMO"
        failures = 0
        for event in project.events:
            event.candidates = []
            for variant in ("clean", "character"):
                started_at = datetime.now(UTC)
                candidate = GenerationCandidate(
                    id=_candidate_id(),
                    variant=variant,
                    status="generating",
                    prompt=build_prompt(event, project.style, variant),
                    provider="framefoley-demo-cache",
                    model="deterministic-original-v1",
                    source_label="CACHED DEMO",
                    parameters={
                        "cacheVersion": "deterministic-original-v1",
                        "durationSeconds": event.target_duration_seconds,
                        "modality": "audio",
                    },
                    started_at=started_at,
                    manifest_verified=False,
                )
                event.candidates.append(candidate)
                self._publish_candidate(project, event, candidate)
                try:
                    started_clock = time.monotonic()
                    self._process_cached_candidate(project, event, candidate)
                    candidate.ended_at = datetime.now(UTC)
                    candidate.latency_seconds = round(time.monotonic() - started_clock, 3)
                    self._publish_candidate(project, event, candidate)
                except Exception as exc:
                    failures += 1
                    candidate.ended_at = datetime.now(UTC)
                    candidate.status = "failed"
                    candidate.error = _candidate_error(exc)
                    self._publish_candidate(project, event, candidate)
                    if isinstance(exc, PublicError):
                        continue
                    raise
        ready_count = sum(
            candidate.status == "ready"
            for event in project.events
            for candidate in event.candidates
        )
        if ready_count == 0:
            transition(project, ProjectState.GENERATION_FAILED)
        elif failures:
            transition(project, ProjectState.GENERATION_PARTIAL)
        else:
            transition(project, ProjectState.AUDITION_READY)
        self.repository.save(project)
        self.events.publish(project.id, "project.state", {"state": str(project.state)})
        return project

    def _process_cached_candidate(
        self,
        project: FrameFoleyProject,
        event: SoundEvent,
        candidate: GenerationCandidate,
    ) -> None:
        source = (
            self.settings.repo_root
            / "demo"
            / "cache"
            / "raw"
            / f"{event.slug}-{candidate.variant}.wav"
        )
        if not source.is_file():
            raise PublicError(
                "DEMO_CACHE_MISSING",
                "Cached demo audio is unavailable.",
                status_code=503,
            )
        suffix = f"events/{event.id}/candidates/{candidate.id}"
        raw_key = self.repository.put_object(
            project.id, f"{suffix}/raw-audio.wav", source.read_bytes(), content_type="audio/wav"
        )
        candidate.raw_asset_key = raw_key
        candidate.asset_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        candidate.status = "stored"
        self._publish_candidate(project, event, candidate)
        with TemporaryDirectory(prefix="framefoley-demo-candidate-") as temporary:
            root = Path(temporary)
            raw = root / "raw.wav"
            approved = root / "approved.wav"
            ogg = root / "approved.ogg"
            waveform = root / "waveform.png"
            shutil.copyfile(source, raw)
            before = inspect_audio(raw)
            candidate.qc_before = _api_qc(before)
            candidate.status = "checking"
            self._publish_candidate(project, event, candidate)
            if before.verdict in {QcVerdict.FAILED, QcVerdict.REGENERATE}:
                raise PublicError(
                    "DEMO_CACHE_QC_FAILED",
                    "Cached demo audio failed QC.",
                    status_code=500,
                )
            repairs: tuple[str, ...] = ()
            if before.verdict is QcVerdict.REPAIRABLE:
                repairs = repair_audio(raw, approved, before)
            else:
                shutil.copyfile(raw, approved)
            after = inspect_audio(approved)
            if after.verdict is not QcVerdict.PASS:
                raise PublicError(
                    "DEMO_CACHE_REPAIR_FAILED",
                    "Cached demo repair failed QC.",
                    status_code=500,
                )
            render_waveform(approved, waveform)
            convert_wav_to_ogg(approved, ogg)
            candidate.qc_after = _api_qc(after, repairs=repairs)
            candidate.repairs = list(repairs)
            candidate.approved_wav_key = self.repository.put_object(
                project.id,
                f"{suffix}/approved-audio.wav",
                approved.read_bytes(),
                content_type="audio/wav",
            )
            candidate.approved_ogg_key = self.repository.put_object(
                project.id,
                f"{suffix}/approved-audio.ogg",
                ogg.read_bytes(),
                content_type="audio/ogg",
            )
            candidate.waveform_key = self.repository.put_object(
                project.id,
                f"{suffix}/waveform.png",
                waveform.read_bytes(),
                content_type="image/png",
            )
        manifest = {
            "schemaVersion": 1,
            "sourceLabel": "CACHED DEMO",
            "provider": candidate.provider,
            "model": candidate.model,
            "prompt": candidate.prompt,
            "assetSha256": candidate.asset_sha256,
            "createdAt": datetime.now(UTC).isoformat(),
            "notice": "Application cache record; not a canonical Genblaze manifest.",
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        manifest_key = self.repository.put_object(
            project.id,
            f"{suffix}/cache-manifest.json",
            manifest_bytes,
            content_type="application/json",
        )
        candidate.manifest_uri = manifest_key
        candidate.manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        candidate.status = "ready"
        self._publish_candidate(project, event, candidate)
        self.events.publish(
            project.id,
            "candidate.qc",
            {
                "verdict": candidate.qc_after.verdict if candidate.qc_after else "failed",
                "repairs": candidate.repairs,
            },
            event_id=event.id,
            candidate_id=candidate.id,
        )

    def _generate_live(self, project: FrameFoleyProject) -> FrameFoleyProject:
        project.evidence_label = "LIVE"
        try:
            self.settings.require_live()
            backend = S3StorageBackend.for_backblaze(
                bucket=cast(str, self.settings.b2_bucket),
                region=cast(str, self.settings.b2_region),
                key_id=cast(str, self.settings.b2_key_id),
                app_key=cast(str, self.settings.b2_app_key),
                auto_lifecycle=False,
                preflight=True,
            )
        except Exception as exc:
            raise PublicError(
                "LIVE_CONFIGURATION_INVALID",
                f"Live generation preflight failed: {exc}",
                status_code=503,
            ) from exc

        sink = ObjectStorageSink(
            backend,
            prefix=f"{project_prefix(project.id)}genblaze",
            key_strategy=KeyStrategy.HIERARCHICAL,
            max_upload_workers=1,
        )
        failures = 0
        try:
            with TemporaryDirectory(prefix="framefoley-phase1-provider-") as temporary:
                provider = ElevenLabsSFXProvider(
                    api_key=cast(str, self.settings.elevenlabs_api_key),
                    output_dir=Path(temporary),
                    retry_policy=RetryPolicy(max_attempts=1, jitter="none"),
                )
                for event in project.events:
                    event.candidates = []
                    for variant in ("clean", "character"):
                        candidate = GenerationCandidate(
                            id=_candidate_id(),
                            variant=variant,
                            status="generating",
                            prompt=build_prompt(event, project.style, variant),
                            provider=LIVE_PROVIDER,
                            model=LIVE_MODEL,
                            source_label="LIVE",
                            parameters={
                                "durationSeconds": max(
                                    0.5, min(30.0, event.target_duration_seconds)
                                ),
                                "modality": "audio",
                                "maxProviderAttempts": 1,
                            },
                            manifest_verified=False,
                        )
                        event.candidates.append(candidate)
                        self._publish_candidate(project, event, candidate)
                        try:
                            self._process_live_candidate(
                                project,
                                event,
                                candidate,
                                provider=provider,
                                sink=sink,
                                backend=backend,
                            )
                        except Exception as exc:
                            failures += 1
                            candidate.status = "failed"
                            candidate.error = _candidate_error(exc)
                            self._publish_candidate(project, event, candidate)
        finally:
            sink.close()
            backend.close()

        ready_count = sum(
            candidate.status == "ready"
            for event in project.events
            for candidate in event.candidates
        )
        if ready_count == 0:
            transition(project, ProjectState.GENERATION_FAILED)
        elif failures:
            transition(project, ProjectState.GENERATION_PARTIAL)
        else:
            transition(project, ProjectState.AUDITION_READY)
        self.repository.save(project)
        self.events.publish(project.id, "project.state", {"state": str(project.state)})
        return project

    def _process_live_candidate(
        self,
        project: FrameFoleyProject,
        event: SoundEvent,
        candidate: GenerationCandidate,
        *,
        provider: ElevenLabsSFXProvider,
        sink: ObjectStorageSink,
        backend: S3StorageBackend,
    ) -> None:
        duration_window = EVENT_WINDOWS[str(event.type)]
        suffix = f"events/{event.id}/candidates/{candidate.id}"
        while True:
            if project.live_call_count >= 12:
                raise PublicError(
                    "GENERATION_QUOTA_REACHED",
                    "This project has reached its twelve-call hard ceiling.",
                    status_code=429,
                )
            project.live_call_count += 1
            candidate.started_at = datetime.now(UTC)
            started_clock = time.monotonic()
            candidate.status = "generating"
            self._publish_candidate(project, event, candidate)
            try:
                result = (
                    Pipeline(LIVE_PIPELINE_NAME, project_id=project.id)
                    .step(
                        provider,
                        model=LIVE_MODEL,
                        prompt=candidate.prompt,
                        modality=Modality.AUDIO,
                        duration_seconds=max(0.5, min(30.0, event.target_duration_seconds)),
                    )
                    .run(
                        sink=sink,
                        timeout=45,
                        pipeline_timeout=60,
                        max_retries=0,
                        raise_on_failure=True,
                        _owns_sink=False,
                    )
                )
            except Exception as exc:
                raise PublicError(
                    "PROVIDER_CALL_FAILED",
                    f"The Genblaze provider call failed: {exc}",
                    retryable=False,
                    status_code=502,
                ) from exc
            candidate.ended_at = datetime.now(UTC)
            candidate.latency_seconds = round(time.monotonic() - started_clock, 3)
            if not result.manifest.verify():
                raise PublicError(
                    "MANIFEST_VERIFICATION_FAILED",
                    "Manifest.verify() returned false for the live candidate.",
                    status_code=502,
                )
            step = result.run.steps[0]
            if not step.assets:
                raise PublicError(
                    "PROVIDER_ASSET_MISSING",
                    "The live provider returned no audio asset.",
                    status_code=502,
                )
            asset = step.assets[0]
            asset_key = backend.key_from_url(asset.url)
            if asset_key is None or not asset_key.startswith(project_prefix(project.id)):
                raise PublicError(
                    "DURABLE_ASSET_KEY_INVALID",
                    "The Genblaze asset did not resolve inside the private project prefix.",
                    status_code=502,
                )
            manifest_key = sink.manifest_key_for(result.run)
            raw_bytes = backend.get(asset_key)
            raw_hash = hashlib.sha256(raw_bytes).hexdigest()
            if not asset.sha256 or raw_hash != asset.sha256:
                raise PublicError(
                    "DURABLE_ASSET_HASH_MISMATCH",
                    "The B2-downloaded live asset did not match its Genblaze hash.",
                    status_code=502,
                )
            stored_manifest = Manifest.model_validate_json(backend.get(manifest_key))
            if not stored_manifest.verify():
                raise PublicError(
                    "STORED_MANIFEST_VERIFICATION_FAILED",
                    "The canonical manifest downloaded from B2 did not verify.",
                    status_code=502,
                )

            candidate.genblaze_run_id = result.run.run_id
            candidate.raw_asset_key = asset_key
            candidate.asset_sha256 = raw_hash
            candidate.manifest_uri = manifest_key
            candidate.manifest_hash = stored_manifest.canonical_hash
            candidate.manifest_verified = True
            candidate.cost_usd = step.cost_usd
            candidate.status = "stored"
            self._publish_candidate(project, event, candidate)

            with TemporaryDirectory(prefix="framefoley-live-candidate-") as temporary:
                root = Path(temporary)
                raw = root / "provider-output.mp3"
                approved = root / "approved.wav"
                ogg = root / "approved.ogg"
                waveform = root / "waveform.png"
                raw.write_bytes(raw_bytes)
                before = inspect_audio(raw, duration_window=duration_window)
                candidate.qc_before = _api_qc(before)
                candidate.status = "checking"
                self._publish_candidate(project, event, candidate)
                if before.verdict in {QcVerdict.FAILED, QcVerdict.REGENERATE}:
                    if candidate.retry_count == 0 and project.retry_budget_remaining > 0:
                        retry_reason = before.reasons[0] if before.reasons else "decode_failed"
                        project.retry_budget_remaining -= 1
                        candidate.retry_count = 1
                        candidate.parent_run_id = result.run.run_id
                        candidate.prompt = build_prompt(
                            event,
                            project.style,
                            candidate.variant,
                            retry_reason=retry_reason,
                        )
                        candidate.status = "retrying"
                        self._publish_candidate(project, event, candidate)
                        continue
                    raise PublicError(
                        "GENERATION_QC_REJECTED",
                        "The live candidate failed deterministic QC and has no retry remaining.",
                        status_code=422,
                    )

                repairs = repair_audio(raw, approved, before)
                after = inspect_audio(approved, duration_window=duration_window)
                if after.verdict is not QcVerdict.PASS:
                    raise PublicError(
                        "GENERATION_REPAIR_FAILED",
                        "The live candidate did not pass QC after deterministic repair.",
                        status_code=500,
                    )
                render_waveform(approved, waveform)
                convert_wav_to_ogg(approved, ogg)
                candidate.qc_after = _api_qc(after, repairs=repairs)
                candidate.repairs = list(repairs)
                candidate.approved_wav_key = self.repository.put_object(
                    project.id,
                    f"{suffix}/approved-audio.wav",
                    approved.read_bytes(),
                    content_type="audio/wav",
                )
                candidate.approved_ogg_key = self.repository.put_object(
                    project.id,
                    f"{suffix}/approved-audio.ogg",
                    ogg.read_bytes(),
                    content_type="audio/ogg",
                )
                candidate.waveform_key = self.repository.put_object(
                    project.id,
                    f"{suffix}/waveform.png",
                    waveform.read_bytes(),
                    content_type="image/png",
                )
                self.repository.put_object(
                    project.id,
                    f"{suffix}/qc-before.json",
                    _json_bytes(candidate.qc_before.model_dump(mode="json", by_alias=True)),
                    content_type="application/json",
                )
                self.repository.put_object(
                    project.id,
                    f"{suffix}/qc-after.json",
                    _json_bytes(candidate.qc_after.model_dump(mode="json", by_alias=True)),
                    content_type="application/json",
                )
                self.repository.put_object(
                    project.id,
                    f"{suffix}/derivative.json",
                    _json_bytes(
                        {
                            "schemaVersion": 1,
                            "sourceLabel": "LIVE",
                            "genblazeRunId": candidate.genblaze_run_id,
                            "parentRunId": candidate.parent_run_id,
                            "canonicalManifestHash": candidate.manifest_hash,
                            "originalAssetSha256": candidate.asset_sha256,
                            "approvedAssetSha256": candidate.qc_after.sha256,
                            "repairs": candidate.repairs,
                        }
                    ),
                    content_type="application/json",
                )
            candidate.status = "ready"
            candidate.error = None
            self._publish_candidate(project, event, candidate)
            self.events.publish(
                project.id,
                "candidate.qc",
                {"verdict": "pass", "repairs": candidate.repairs},
                event_id=event.id,
                candidate_id=candidate.id,
            )
            return
