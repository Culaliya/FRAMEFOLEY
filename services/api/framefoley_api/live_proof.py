"""Immutable LIVE evidence publication and zero-provider-call replay."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from genblaze_core import Manifest, StorageError
from pydantic import BaseModel, ValidationError

from framefoley_api.errors import PublicError
from framefoley_api.models import (
    FrameFoleyProject,
    GenerationCandidate,
    LiveProofCandidatePayloadV1,
    LiveProofEventV1,
    LiveProofIndexV1,
    ProjectPhase,
    ProjectState,
    ProofReplayMetadata,
    QcReport,
    SoundEvent,
    SourceClip,
)
from framefoley_api.repository import ProjectRepository
from framefoley_api.storage import ObjectStore, content_type_for_key

CURRENT_PROOF_VERSION = "live-v2"
PROOF_PREFIX_V1 = "framefoley/proof/live/v1/"
PROOF_PREFIX_V2 = "framefoley/proof/live/v2/"
PROOF_PREFIX = PROOF_PREFIX_V2
PROOF_INDEX_KEY = PROOF_PREFIX + "proof-index.json"
PROOF_CHECKSUMS_KEY = PROOF_PREFIX + "checksums.sha256"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def proof_prefix_for_version(proof_version: str) -> str:
    if proof_version == "live-v1":
        return PROOF_PREFIX_V1
    if proof_version == "live-v2":
        return PROOF_PREFIX_V2
    raise ValueError("unsupported LIVE proof version")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(payload: object) -> bytes:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _candidate_paths(variant: str) -> dict[str, str]:
    return {
        "record": f"candidates/{variant}/candidate.json",
        "raw": f"candidates/{variant}/raw-audio.mp3",
        "wav": f"candidates/{variant}/approved-audio.wav",
        "ogg": f"candidates/{variant}/approved-audio.ogg",
        "manifest": f"manifests/{variant}.json",
        "qc_before": f"qc/{variant}-before.json",
        "qc_after": f"qc/{variant}-after.json",
        "waveform": f"waveforms/{variant}.png",
    }


def required_proof_paths() -> set[str]:
    paths = {
        "proof-index.json",
        "source/original.mp4",
        "source/preview.mp4",
        "source/thumbnail.webp",
        "events/event.json",
    }
    for variant in ("clean", "character"):
        paths.update(_candidate_paths(variant).values())
    return paths


def _parse_checksums(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("proof checksums are not UTF-8") from exc
    checksums: dict[str, str] = {}
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("  ", maxsplit=1)
        if len(parts) != 2 or not _SHA256.fullmatch(parts[0]):
            raise ValueError("proof checksum line is invalid")
        relative = PurePosixPath(parts[1])
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != parts[1]:
            raise ValueError("proof checksum path is unsafe")
        if parts[1] in checksums:
            raise ValueError("proof checksum path is duplicated")
        checksums[parts[1]] = parts[0]
    if set(checksums) != required_proof_paths():
        raise ValueError("proof checksum inventory is incomplete or unexpected")
    return checksums


@dataclass(frozen=True)
class VerifiedLiveProof:
    index: LiveProofIndexV1
    objects: dict[str, bytes]
    checksums_sha256: str


class LiveProofService:
    """Verify the private immutable proof before any replay project is created."""

    def __init__(
        self,
        store: ObjectStore,
        repository: ProjectRepository,
        *,
        proof_version: str = CURRENT_PROOF_VERSION,
    ) -> None:
        self.store = store
        self.repository = repository
        self.proof_version = proof_version
        self.proof_prefix = proof_prefix_for_version(proof_version)
        self.proof_index_key = self.proof_prefix + "proof-index.json"
        self.proof_checksums_key = self.proof_prefix + "checksums.sha256"

    def available(self) -> bool:
        return self.store.exists(self.proof_index_key) and self.store.exists(
            self.proof_checksums_key
        )

    def verify(self) -> VerifiedLiveProof:
        try:
            checksum_bytes = self.store.get(self.proof_checksums_key)
            checksums = _parse_checksums(checksum_bytes)
            objects: dict[str, bytes] = {}
            for relative, expected_hash in checksums.items():
                key = self.proof_prefix + relative
                if not self.store.exists(key):
                    raise ValueError(f"proof object is missing: {relative}")
                payload = self.store.get(key)
                if _sha256(payload) != expected_hash:
                    raise ValueError(f"proof object hash mismatch: {relative}")
                objects[relative] = payload

            index = LiveProofIndexV1.model_validate_json(objects["proof-index.json"])
            if index.proof_version != self.proof_version:
                raise ValueError("proof index version does not match its immutable prefix")
            if _sha256(objects["source/preview.mp4"]) != _sha256(objects["source/original.mp4"]):
                raise ValueError("proof preview does not match the silent source")
            LiveProofEventV1.model_validate_json(objects["events/event.json"])

            for candidate in index.candidates:
                paths = _candidate_paths(candidate.variant)
                record = LiveProofCandidatePayloadV1.model_validate_json(objects[paths["record"]])
                if (
                    record.candidate_id != candidate.candidate_id
                    or record.variant != candidate.variant
                ):
                    raise ValueError("proof candidate record does not match the index")
                if _sha256(objects[paths["raw"]]) != candidate.asset_sha256:
                    raise ValueError("proof provider asset hash mismatch")
                if _sha256(objects[paths["wav"]]) != record.approved_wav_sha256:
                    raise ValueError("proof approved WAV hash mismatch")
                if _sha256(objects[paths["ogg"]]) != record.approved_ogg_sha256:
                    raise ValueError("proof approved OGG hash mismatch")
                if _sha256(objects[paths["waveform"]]) != record.waveform_sha256:
                    raise ValueError("proof waveform hash mismatch")
                manifest_bytes = objects[paths["manifest"]]
                if _sha256(manifest_bytes) != record.manifest_object_sha256:
                    raise ValueError("proof manifest object hash mismatch")
                manifest = Manifest.model_validate_json(manifest_bytes)
                if manifest.verify() is not True:
                    raise ValueError("Manifest.verify() returned false for proof replay")
                if manifest.canonical_hash != candidate.manifest_hash:
                    raise ValueError("proof canonical manifest hash mismatch")
                if manifest.run.run_id != candidate.run_id:
                    raise ValueError("proof run lineage mismatch")
                if len(manifest.run.steps) != 1:
                    raise ValueError("proof manifest must contain one bounded provider step")
                step = manifest.run.steps[0]
                if step.provider != index.provider or step.model != index.model:
                    raise ValueError("proof provider or model does not match the index")
                if not any(asset.sha256 == candidate.asset_sha256 for asset in step.assets):
                    raise ValueError("proof manifest does not cover the downloaded provider bytes")
                before = QcReport.model_validate_json(objects[paths["qc_before"]])
                after = QcReport.model_validate_json(objects[paths["qc_after"]])
                if before.verdict != candidate.qc_before or after.verdict != "pass":
                    raise ValueError("proof QC verdict does not match the index")
                if after.repairs != candidate.repairs:
                    raise ValueError("proof repair history does not match the index")
            return VerifiedLiveProof(
                index=index,
                objects=objects,
                checksums_sha256=_sha256(checksum_bytes),
            )
        except (
            KeyError,
            OSError,
            StorageError,
            ValueError,
            ValidationError,
            json.JSONDecodeError,
        ) as exc:
            raise PublicError(
                "LIVE_PROOF_INVALID",
                "The immutable LIVE evidence replay could not be verified from private storage.",
                retryable=False,
                status_code=503,
            ) from exc

    def hydrate_project(
        self, project: FrameFoleyProject, proof: VerifiedLiveProof
    ) -> FrameFoleyProject:
        """Clone verified private proof bytes into one isolated expiring project."""

        index = proof.index
        event_record = LiveProofEventV1.model_validate_json(proof.objects["events/event.json"])
        original_key = self.repository.put_object(
            project.id,
            "source/original.mp4",
            proof.objects["source/original.mp4"],
            content_type="video/mp4",
        )
        preview_key = self.repository.put_object(
            project.id,
            "source/preview.mp4",
            proof.objects["source/preview.mp4"],
            content_type="video/mp4",
        )
        thumbnail_key = self.repository.put_object(
            project.id,
            "source/thumbnail.webp",
            proof.objects["source/thumbnail.webp"],
            content_type="image/webp",
        )
        project.source = SourceClip(
            b2_key=original_key,
            preview_key=preview_key,
            mime_type="video/mp4",
            duration_seconds=12,
            width=1280,
            height=720,
            fps=30,
            sha256=_sha256(proof.objects["source/original.mp4"]),
            thumbnail_key=thumbnail_key,
            source_audio_stripped=True,
            origin="live_proof",
        )

        candidates: list[GenerationCandidate] = []
        for record in index.candidates:
            paths = _candidate_paths(record.variant)
            private_record = LiveProofCandidatePayloadV1.model_validate_json(
                proof.objects[paths["record"]]
            )
            candidate_suffix = f"events/{event_record.id}/candidates/{record.candidate_id}"
            raw_key = self.repository.put_object(
                project.id,
                f"{candidate_suffix}/raw-audio.mp3",
                proof.objects[paths["raw"]],
                content_type="audio/mpeg",
            )
            wav_key = self.repository.put_object(
                project.id,
                f"{candidate_suffix}/approved-audio.wav",
                proof.objects[paths["wav"]],
                content_type="audio/wav",
            )
            ogg_key = self.repository.put_object(
                project.id,
                f"{candidate_suffix}/approved-audio.ogg",
                proof.objects[paths["ogg"]],
                content_type="audio/ogg",
            )
            waveform_key = self.repository.put_object(
                project.id,
                f"{candidate_suffix}/waveform.png",
                proof.objects[paths["waveform"]],
                content_type="image/png",
            )
            manifest_key = self.repository.put_object(
                project.id,
                f"{candidate_suffix}/canonical-manifest.json",
                proof.objects[paths["manifest"]],
                content_type="application/json",
            )
            qc_before = QcReport.model_validate_json(proof.objects[paths["qc_before"]])
            qc_after = QcReport.model_validate_json(proof.objects[paths["qc_after"]])
            self.repository.put_object(
                project.id,
                f"{candidate_suffix}/qc-before.json",
                proof.objects[paths["qc_before"]],
                content_type="application/json",
            )
            self.repository.put_object(
                project.id,
                f"{candidate_suffix}/qc-after.json",
                proof.objects[paths["qc_after"]],
                content_type="application/json",
            )
            candidates.append(
                GenerationCandidate(
                    id=record.candidate_id,
                    variant=record.variant,
                    status="ready",
                    prompt=private_record.prompt,
                    provider=index.provider,
                    model=index.model,
                    source_label="LIVE",
                    parameters={
                        "proofVersion": index.proof_version,
                        "replayProviderCalls": 0,
                        "recordedProviderCalls": index.provider_call_count,
                        "durationSeconds": event_record.target_duration_seconds,
                    },
                    started_at=private_record.started_at,
                    ended_at=private_record.ended_at,
                    latency_seconds=record.latency_seconds,
                    genblaze_run_id=record.run_id,
                    manifest_uri=manifest_key,
                    manifest_hash=record.manifest_hash,
                    manifest_verified=True,
                    raw_asset_key=raw_key,
                    approved_wav_key=wav_key,
                    approved_ogg_key=ogg_key,
                    waveform_key=waveform_key,
                    asset_sha256=record.asset_sha256,
                    qc_before=qc_before,
                    qc_after=qc_after,
                    repairs=record.repairs,
                    retry_count=0,
                )
            )

        project.events = [
            SoundEvent(
                **event_record.model_dump(),
                candidates=candidates,
                approved_candidate_id=None,
            )
        ]
        project.state = ProjectState.AUDITION_READY
        project.phase = ProjectPhase.AUDITION
        project.generation_mode = "disabled"
        project.live_call_count = 0
        project.evidence_label = "LIVE EVIDENCE REPLAY"
        project.proof_replay = ProofReplayMetadata(
            proof_version=index.proof_version,
            captured_at=index.captured_at,
            recorded_provider_call_count=index.provider_call_count,
            replay_provider_call_count=0,
            b2_object_count=index.b2_object_count,
            cost_disclosure=index.cost_disclosure,
        )
        self.repository.put_object(
            project.id,
            "source/source-metadata.json",
            _json_bytes(project.source),
            content_type="application/json",
        )
        self.repository.put_object(
            project.id,
            f"events/{event_record.id}/event.json",
            _json_bytes(project.events[0]),
            content_type="application/json",
        )
        self.repository.save(project)
        return project


def write_immutable_proof_bundle(
    store: ObjectStore,
    index: LiveProofIndexV1,
    objects: dict[str, bytes],
) -> str:
    """Write an immutable proof bundle and return created/already-present status."""

    payloads = dict(objects)
    payloads["proof-index.json"] = _json_bytes(index)
    if set(payloads) != required_proof_paths():
        raise ValueError("proof publication payload is incomplete or unexpected")
    checksum_lines = [f"{_sha256(payloads[path])}  {path}" for path in sorted(payloads)]
    checksums = ("\n".join(checksum_lines) + "\n").encode("utf-8")
    full_payloads = {**payloads, "checksums.sha256": checksums}

    proof_prefix = proof_prefix_for_version(index.proof_version)
    existing = [path for path in full_payloads if store.exists(proof_prefix + path)]
    if existing:
        for path in existing:
            if store.get(proof_prefix + path) != full_payloads[path]:
                raise ValueError("immutable proof prefix already contains different bytes")
        if len(existing) == len(full_payloads):
            repository = ProjectRepository(store)
            LiveProofService(store, repository, proof_version=index.proof_version).verify()
            return "already-present"

    for path, payload in sorted(full_payloads.items()):
        store.put(
            proof_prefix + path,
            payload,
            content_type=content_type_for_key(path),
        )
    repository = ProjectRepository(store)
    LiveProofService(store, repository, proof_version=index.proof_version).verify()
    return "created"
