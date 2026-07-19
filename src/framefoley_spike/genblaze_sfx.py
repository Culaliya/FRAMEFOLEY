"""One-call live ElevenLabs SFX path and explicit failure/recovery state."""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from genblaze_core import KeyStrategy, Manifest, Modality, ObjectStorageSink, Pipeline
from genblaze_core.providers import RetryPolicy
from genblaze_elevenlabs import ElevenLabsSFXProvider

from framefoley_spike.b2 import StorageSpikeError, create_backend, safe_object_key, spike_prefix
from framefoley_spike.config import SpikeConfig, resolved_package_versions
from framefoley_spike.provenance import (
    DerivativeRecord,
    sanitize_text,
    sha256_bytes,
    sha256_file,
)
from framefoley_spike.qc import QcVerdict, inspect_audio, render_waveform, repair_audio

PIPELINE_NAME = "framefoley-phase0-sfx"
MODEL = "eleven_text_to_sound_v2"
PROMPT = (
    "A short soft rubber creature landing on a thin glass platform, "
    "a rounded low thump with one tiny crystalline tick, "
    "playful sci-fi arcade sound effect, "
    "dry close perspective, "
    "no music, no speech, no cinematic boom."
)
TARGET_DURATION_SECONDS = 0.8


class CandidateStage(StrEnum):
    READY_FOR_PROVIDER = "ready_for_provider"
    PROVIDER_SUCCEEDED = "provider_succeeded"
    STORAGE_FAILED = "storage_failed"
    STORED = "stored"
    VERIFIED = "verified"
    FAILED = "failed"


class LiveSpikeError(RuntimeError):
    def __init__(self, stage: str, code: str, message: str) -> None:
        self.stage = stage
        self.code = code
        self.safe_message = sanitize_text(message)
        super().__init__(f"{stage}/{code}: {self.safe_message}")


@dataclass
class CandidateAttempt:
    """State proving storage retry can reuse provider bytes."""

    stage: CandidateStage = CandidateStage.READY_FOR_PROVIDER
    provider_attempts: int = 0
    storage_attempts: int = 0
    local_bytes: bytes | None = None
    asset_sha256: str | None = None
    verified: bool = False
    error_code: str | None = None
    max_provider_attempts: int = 2
    max_storage_attempts: int = 2

    def record_provider_success(self, payload: bytes) -> None:
        if self.provider_attempts >= self.max_provider_attempts:
            raise LiveSpikeError(
                "provider", "retry_budget_exhausted", "provider retry budget exhausted"
            )
        self.provider_attempts += 1
        self.local_bytes = payload
        self.asset_sha256 = sha256_bytes(payload)
        self.stage = CandidateStage.PROVIDER_SUCCEEDED
        self.error_code = None

    def record_provider_failure(self, code: str) -> None:
        self.provider_attempts += 1
        self.stage = CandidateStage.FAILED
        self.verified = False
        self.error_code = code

    def store(self, uploader: Callable[[bytes], None]) -> None:
        if self.local_bytes is None:
            raise LiveSpikeError("storage", "bytes_unavailable", "provider bytes are unavailable")
        if self.storage_attempts >= self.max_storage_attempts:
            raise LiveSpikeError(
                "storage", "retry_budget_exhausted", "storage retry budget exhausted"
            )
        self.storage_attempts += 1
        try:
            uploader(self.local_bytes)
        except Exception as exc:
            self.stage = CandidateStage.STORAGE_FAILED
            self.verified = False
            self.error_code = "storage_upload_failed"
            raise LiveSpikeError("storage", self.error_code, str(exc)) from exc
        self.stage = CandidateStage.STORED
        self.error_code = None

    def mark_verified(self, manifest_verified: bool) -> None:
        if self.stage is not CandidateStage.STORED or not manifest_verified:
            self.verified = False
            raise LiveSpikeError(
                "manifest", "verification_failed", "manifest verification returned false"
            )
        self.verified = True
        self.stage = CandidateStage.VERIFIED

    @property
    def complete(self) -> bool:
        return self.stage is CandidateStage.VERIFIED and self.verified

    @property
    def can_retry_storage_without_generation(self) -> bool:
        return (
            self.stage is CandidateStage.STORAGE_FAILED
            and self.local_bytes is not None
            and self.storage_attempts < self.max_storage_attempts
        )


def require_live_acknowledgement() -> None:
    if os.getenv("FRAMEFOLEY_ALLOW_LIVE_CALL") != "1":
        raise LiveSpikeError(
            "budget",
            "live_call_not_acknowledged",
            "set FRAMEFOLEY_ALLOW_LIVE_CALL=1 to authorize one provider call",
        )


def cached_demo_descriptor(reason_code: str) -> dict[str, Any]:
    """Honest future fallback metadata; never claims a cached run was live."""

    return {
        "mode": "DEMO_CACHE",
        "live_generation": False,
        "reason_code": reason_code,
        "label": "DEMO CACHE",
    }


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def provider_transfer_dir() -> Path:
    """Return a retained staging directory allowed by Genblaze file transfers."""

    return Path(tempfile.gettempdir()).resolve() / "framefoley-phase0-provider"


def run_live_sfx(config: SpikeConfig, work_dir: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Perform exactly one no-retry SFX call after B2 preflight succeeds."""

    require_live_acknowledgement()
    config.require_live()
    prefix = spike_prefix()
    backend = create_backend(config)  # Must pass before any provider spend.
    sink = ObjectStorageSink(
        backend,
        prefix=prefix,
        key_strategy=KeyStrategy.HIERARCHICAL,
        max_upload_workers=1,
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    provider_output_dir = provider_transfer_dir()
    provider_output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    provider_output_dir.chmod(0o700)
    provider = ElevenLabsSFXProvider(
        api_key=cast(str, config.elevenlabs_api_key),
        output_dir=provider_output_dir,
        retry_policy=RetryPolicy(max_attempts=1, jitter="none"),
    )
    started_at = datetime.now(UTC)
    started_clock = time.monotonic()
    try:
        result = (
            Pipeline(PIPELINE_NAME)
            .step(
                provider,
                model=MODEL,
                prompt=PROMPT,
                modality=Modality.AUDIO,
                duration_seconds=TARGET_DURATION_SECONDS,
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
        ended_at = datetime.now(UTC)
        latency = time.monotonic() - started_clock
        if not result.manifest.verify():
            raise LiveSpikeError(
                "manifest", "verification_failed", "Manifest.verify() returned false"
            )

        step = result.run.steps[0]
        asset = step.assets[0]
        asset_key = backend.key_from_url(asset.url)
        if asset_key is None:
            raise LiveSpikeError("storage", "durable_key_missing", "asset URL did not map to B2")
        manifest_key = sink.manifest_key_for(result.run)
        downloaded = backend.get(asset_key)
        downloaded_hash = sha256_bytes(downloaded)
        if downloaded_hash != asset.sha256:
            raise LiveSpikeError("storage", "download_hash_mismatch", "B2 asset hash mismatch")

        stored_manifest = Manifest.model_validate_json(backend.get(manifest_key))
        if not stored_manifest.verify():
            raise LiveSpikeError(
                "manifest", "stored_manifest_verification_failed", "B2 manifest did not verify"
            )

        raw_path = work_dir / "provider-output.mp3"
        raw_path.write_bytes(downloaded)
        before = inspect_audio(raw_path)
        if before.verdict in {QcVerdict.FAILED, QcVerdict.REGENERATE}:
            raise LiveSpikeError(
                "qc", "live_audio_rejected", f"deterministic QC verdict {before.verdict.value}"
            )
        repaired_path = work_dir.parent / "repaired-sfx.wav"
        repairs = repair_audio(raw_path, repaired_path, before)
        after = inspect_audio(repaired_path)
        if after.verdict is not QcVerdict.PASS:
            raise LiveSpikeError(
                "qc", "repair_did_not_pass", f"post-repair verdict {after.verdict.value}"
            )
        waveform_path = work_dir.parent / "waveform.png"
        render_waveform(repaired_path, waveform_path)

        derivative = DerivativeRecord(
            schema_version=1,
            original_run_id=result.run.run_id,
            original_asset_id=asset.asset_id,
            original_asset_sha256=cast(str, asset.sha256),
            canonical_manifest_hash=stored_manifest.canonical_hash,
            derivative_sha256=sha256_file(repaired_path),
            repairs=repairs,
        )
        application_prefix = safe_object_key(prefix, "application")
        application_objects = {
            safe_object_key(application_prefix, "qc-before.json"): (
                _json_bytes(before.to_dict()),
                "application/json",
            ),
            safe_object_key(application_prefix, "repaired-sfx.wav"): (
                repaired_path.read_bytes(),
                "audio/wav",
            ),
            safe_object_key(application_prefix, "qc-after.json"): (
                _json_bytes(after.to_dict()),
                "application/json",
            ),
            safe_object_key(application_prefix, "derivative.json"): (
                _json_bytes(derivative.to_dict()),
                "application/json",
            ),
            safe_object_key(application_prefix, "waveform.png"): (
                waveform_path.read_bytes(),
                "image/png",
            ),
        }
        for key, (payload, content_type) in application_objects.items():
            backend.put(key, payload, content_type=content_type)

        page = backend.list(prefix)
        inventory = {
            "schema_version": 1,
            "status": "PASS",
            "operation": "live_sfx_sink_head_list_backend_read_rehash",
            "prefix": f"{prefix}/",
            "run_id": result.run.run_id,
            "manifest_verified": True,
            "manifest_canonical_hash": stored_manifest.canonical_hash,
            "downloaded_sha256": downloaded_hash,
            "hash_match": True,
            "objects": [
                {
                    "key": entry.key,
                    "size_bytes": entry.size,
                    "last_modified": entry.last_modified.astimezone(UTC).isoformat(),
                    "etag": entry.etag.strip('"'),
                }
                for entry in page.entries
            ],
            "required_objects": {
                "asset_key": asset_key,
                "manifest_key": manifest_key,
                "application_keys": sorted(application_objects),
            },
        }
        live = {
            "schema_version": 1,
            "status": "PASS",
            "provider": "elevenlabs-sfx",
            "provider_class": "ElevenLabsSFXProvider",
            "model": MODEL,
            "pipeline_name": PIPELINE_NAME,
            "prompt": PROMPT,
            "target_duration_seconds": TARGET_DURATION_SECONDS,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "latency_seconds": round(latency, 3),
            "run_id": result.run.run_id,
            "step_status": str(step.status),
            "error_code": None,
            "b2_asset_key": asset_key,
            "b2_manifest_key": manifest_key,
            "asset_sha256": asset.sha256,
            "downloaded_sha256": downloaded_hash,
            "manifest_canonical_hash": stored_manifest.canonical_hash,
            "manifest_verified": True,
            "audio_qc_before": before.to_dict(),
            "audio_qc_after": after.to_dict(),
            "cost": {
                "usd": step.cost_usd,
                "availability": "reported" if step.cost_usd is not None else "unavailable",
                "note": None
                if step.cost_usd is not None
                else "genblaze-elevenlabs 0.3.1 does not ship SFX registry pricing",
            },
            "package_versions": resolved_package_versions(),
        }
        return live, inventory, stored_manifest.to_canonical_json()
    except LiveSpikeError:
        raise
    except StorageSpikeError as exc:
        raise LiveSpikeError(exc.stage, exc.code, exc.safe_message) from exc
    except Exception as exc:
        raise LiveSpikeError("pipeline", "external_operation_failed", str(exc)) from exc
    finally:
        sink.close()
