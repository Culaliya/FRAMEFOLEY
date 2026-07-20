"""Publish the final-version LIVE evidence into an immutable private B2 replay bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Literal, cast

from framefoley_api.live_proof import LiveProofService, write_immutable_proof_bundle
from framefoley_api.models import (
    FrameFoleyProject,
    LiveProofCandidatePayloadV1,
    LiveProofCandidateV1,
    LiveProofEventV1,
    LiveProofIndexV1,
    QcReport,
)
from framefoley_api.repository import ProjectRepository
from framefoley_api.settings import Settings
from framefoley_api.storage import B2ObjectStore
from genblaze_core import Manifest

from framefoley_spike.provenance import sanitize_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_EVIDENCE = ROOT / "evidence" / "paid-live-v2"
PHASE2_EVIDENCE = ROOT / "evidence" / "phase2"
VIDEO_AUDIO_CACHE = ROOT / ".data" / "phase2-video-live"


def _load_json(source_evidence: Path, name: str) -> dict[str, Any]:
    payload = json.loads((source_evidence / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain one JSON object")
    return payload


def _resolve_source_evidence(requested: Path) -> Path:
    source = (ROOT / requested).resolve() if not requested.is_absolute() else requested.resolve()
    evidence_root = (ROOT / "evidence").resolve()
    if source == evidence_root or not source.is_relative_to(evidence_root):
        raise ValueError("proof source evidence must be a named directory under evidence/")
    return source


def _cost_disclosure(calls: dict[str, Any]) -> str:
    reported = calls.get("actualCostUsd")
    value = f"{float(reported):.8f}" if isinstance(reported, int | float) else "UNAVAILABLE"
    return (
        f"The connector recorded provider cost USD {value}; this is not evidence "
        "that an ElevenLabs account spend or usage cap is active."
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(name: str, payload: object) -> None:
    PHASE2_EVIDENCE.mkdir(parents=True, exist_ok=True)
    (PHASE2_EVIDENCE / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(source_evidence: Path, proof_version: Literal["live-v1", "live-v2"]) -> int:
    if os.getenv("FRAMEFOLEY_ALLOW_PROOF_PUBLISH") != "1":
        print(
            "ERROR: set FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1 to authorize "
            "the no-provider-call proof publication.",
            file=sys.stderr,
        )
        return 2
    if proof_version == "live-v2" and os.getenv("FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED") != "1":
        print(
            "ERROR: live-v2 publication requires the explicit owner paid-rights gate.",
            file=sys.stderr,
        )
        return 2

    settings = Settings.from_env()
    settings.require_b2()
    calls = _load_json(source_evidence, "LIVE_CALLS_SANITIZED.json")
    manifests = _load_json(source_evidence, "MANIFEST_VERIFICATION.json")
    object_map = _load_json(source_evidence, "B2_OBJECT_MAP.json")
    provider_call_count = calls.get("providerCallCount")
    if (
        calls.get("evidenceLabel") != "LIVE"
        or not isinstance(provider_call_count, int)
        or not 2 <= provider_call_count <= 4
    ):
        raise ValueError("source LIVE call evidence is missing or relabeled")
    if calls.get("candidateCount") != 2 or calls.get("readyVerifiedCandidateCount") != 2:
        raise ValueError("source LIVE evidence does not contain two ready verified candidates")
    if manifests.get("allReadyLiveCandidatesVerified") is not True:
        raise ValueError("source canonical manifest evidence is not verified")
    if object_map.get("evidenceLabel") != "LIVE" or object_map.get("objectCount", 0) < 1:
        raise ValueError("source B2 evidence is missing or relabeled")

    expected_objects = {
        str(record["key"]): str(record["sha256"])
        for record in object_map.get("objects", [])
        if isinstance(record, dict) and "key" in record and "sha256" in record
    }
    project_id = str(calls["projectId"])
    project_key = f"framefoley/v1/projects/{project_id}/project.json"
    store = B2ObjectStore(settings)

    def fetch(key: str) -> bytes:
        expected = expected_objects.get(key)
        if expected is None:
            raise ValueError("required source object is absent from the sanitized B2 inventory")
        payload = store.get(key)
        if _sha256(payload) != expected:
            raise ValueError("B2 source object no longer matches the recorded final-version hash")
        return payload

    try:
        project = FrameFoleyProject.model_validate_json(fetch(project_key))
        if project.id != project_id or len(project.events) < 1:
            raise ValueError("source LIVE project identity or event data is invalid")
        event = project.events[0]
        if len(event.candidates) != 2:
            raise ValueError(
                "source LIVE project must contain exactly two candidates for event one"
            )
        evidence_candidates = {
            str(record["candidateId"]): record
            for record in calls.get("candidates", [])
            if isinstance(record, dict) and "candidateId" in record
        }
        manifest_records = {
            str(record["candidateId"]): record
            for record in manifests.get("records", [])
            if isinstance(record, dict) and "candidateId" in record
        }

        objects: dict[str, bytes] = {
            "source/original.mp4": fetch(project.source.b2_key if project.source else ""),
            "source/preview.mp4": fetch(project.source.preview_key if project.source else ""),
            "source/thumbnail.webp": fetch(project.source.thumbnail_key if project.source else ""),
        }
        if project.source is None or project.source.origin != "demo":
            raise ValueError("the recorded LIVE gate source is not the bounded JELLY RELAY clip")
        safe_event = LiveProofEventV1(
            id=event.id,
            slug=event.slug,
            title=event.title,
            type=event.type,
            timestamp_seconds=event.timestamp_seconds,
            target_duration_seconds=event.target_duration_seconds,
            intensity=event.intensity,
            material_note=event.material_note,
        )
        objects["events/event.json"] = (
            json.dumps(
                safe_event.model_dump(mode="json", by_alias=True, exclude_none=True),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

        proof_candidates: list[LiveProofCandidateV1] = []
        for candidate in project.events[0].candidates:
            record = evidence_candidates.get(candidate.id)
            manifest_record = manifest_records.get(candidate.id)
            if record is None or manifest_record is None:
                raise ValueError("candidate is missing from sanitized LIVE evidence")
            if (
                candidate.source_label != "LIVE"
                or candidate.status != "ready"
                or candidate.manifest_verified is not True
                or record.get("sourceLabel") != "LIVE"
                or record.get("manifestVerified") is not True
                or manifest_record.get("manifestVerifyReturned") is not True
            ):
                raise ValueError("a non-LIVE or unverified candidate cannot enter the proof bundle")
            required_values = (
                candidate.raw_asset_key,
                candidate.approved_wav_key,
                candidate.approved_ogg_key,
                candidate.waveform_key,
                candidate.manifest_uri,
                candidate.asset_sha256,
                candidate.manifest_hash,
                candidate.genblaze_run_id,
                candidate.qc_before,
                candidate.qc_after,
                candidate.started_at,
                candidate.ended_at,
                candidate.latency_seconds,
            )
            if any(value is None for value in required_values):
                raise ValueError("source LIVE candidate is missing required replay metadata")
            if (
                record.get("assetSha256") != candidate.asset_sha256
                or record.get("manifestHash") != candidate.manifest_hash
                or record.get("runId") != candidate.genblaze_run_id
            ):
                raise ValueError("candidate lineage does not match sanitized LIVE evidence")

            variant = str(candidate.variant)
            candidate_prefix = str(candidate.approved_wav_key).rsplit("/", maxsplit=1)[0]
            raw = fetch(str(candidate.raw_asset_key))
            approved_wav = fetch(str(candidate.approved_wav_key))
            approved_ogg = fetch(str(candidate.approved_ogg_key))
            waveform = fetch(str(candidate.waveform_key))
            manifest_bytes = fetch(str(candidate.manifest_uri))
            qc_before_bytes = fetch(candidate_prefix + "/qc-before.json")
            qc_after_bytes = fetch(candidate_prefix + "/qc-after.json")
            manifest = Manifest.model_validate_json(manifest_bytes)
            if manifest.verify() is not True:
                raise ValueError("Manifest.verify() returned false during proof publication")
            if (
                manifest.canonical_hash != candidate.manifest_hash
                or manifest.run.run_id != candidate.genblaze_run_id
                or not any(
                    asset.sha256 == candidate.asset_sha256
                    for step in manifest.run.steps
                    for asset in step.assets
                )
            ):
                raise ValueError("canonical manifest does not cover the recorded candidate")
            qc_before = QcReport.model_validate_json(qc_before_bytes)
            qc_after = QcReport.model_validate_json(qc_after_bytes)
            if qc_before.verdict not in {"pass", "repairable"} or qc_after.verdict != "pass":
                raise ValueError("recorded LIVE candidate does not pass deterministic QC")
            if qc_after.repairs != candidate.repairs:
                raise ValueError("recorded repair history is inconsistent")
            assert candidate.latency_seconds is not None
            assert candidate.started_at is not None
            assert candidate.ended_at is not None
            qc_before_verdict = cast(Literal["pass", "repairable"], qc_before.verdict)

            objects[f"candidates/{variant}/raw-audio.mp3"] = raw
            objects[f"candidates/{variant}/approved-audio.wav"] = approved_wav
            objects[f"candidates/{variant}/approved-audio.ogg"] = approved_ogg
            objects[f"manifests/{variant}.json"] = manifest_bytes
            objects[f"qc/{variant}-before.json"] = qc_before_bytes
            objects[f"qc/{variant}-after.json"] = qc_after_bytes
            objects[f"waveforms/{variant}.png"] = waveform
            private_record = LiveProofCandidatePayloadV1(
                candidate_id=candidate.id,
                variant=candidate.variant,
                prompt=candidate.prompt,
                approved_wav_sha256=_sha256(approved_wav),
                approved_ogg_sha256=_sha256(approved_ogg),
                waveform_sha256=_sha256(waveform),
                manifest_object_sha256=_sha256(manifest_bytes),
                started_at=candidate.started_at,
                ended_at=candidate.ended_at,
            )
            objects[f"candidates/{variant}/candidate.json"] = (
                json.dumps(
                    private_record.model_dump(mode="json", by_alias=True),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            proof_candidates.append(
                LiveProofCandidateV1(
                    candidate_id=candidate.id,
                    variant=candidate.variant,
                    run_id=str(candidate.genblaze_run_id),
                    asset_sha256=_sha256(raw),
                    manifest_hash=str(candidate.manifest_hash),
                    manifest_verified=True,
                    qc_before=qc_before_verdict,
                    qc_after="pass",
                    repairs=candidate.repairs,
                    latency_seconds=candidate.latency_seconds,
                )
            )

        index = LiveProofIndexV1(
            proof_version=proof_version,
            captured_at=calls["recordedAt"],
            source_label="LIVE",
            provider="elevenlabs-sfx",
            model="eleven_text_to_sound_v2",
            provider_call_count=provider_call_count,
            event_count=1,
            candidate_count=2,
            b2_object_count=int(object_map["objectCount"]),
            candidates=proof_candidates,
            cost_disclosure=_cost_disclosure(calls),
            rights_evidence_label=("OWNER-VERIFIED" if proof_version == "live-v2" else None),
            paid_plan_tier="starter" if proof_version == "live-v2" else None,
            sfx_explore_sharing_disabled=(True if proof_version == "live-v2" else None),
        )
        status = write_immutable_proof_bundle(store, index, objects)
        verified = LiveProofService(
            store,
            ProjectRepository(store),
            proof_version=proof_version,
        ).verify()
        VIDEO_AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
        for proof_candidate in verified.index.candidates:
            relative = f"candidates/{proof_candidate.variant}/approved-audio.wav"
            (VIDEO_AUDIO_CACHE / f"{proof_candidate.variant}.wav").write_bytes(
                verified.objects[relative]
            )
        sanitized_index = verified.index.model_dump(mode="json", by_alias=True)
        verification = {
            "schemaVersion": 1,
            "evidenceLabel": "LIVE EVIDENCE REPLAY",
            "proofVersion": verified.index.proof_version,
            "publicationStatus": status,
            "providerCallsDuringPublication": 0,
            "providerCallsDuringReplayOpen": 0,
            "candidateCount": verified.index.candidate_count,
            "manifestVerifyTrueCount": 2,
            "assetHashMatchCount": 2,
            "b2RedownloadHashMatch": True,
            "proofChecksumsSha256": verified.checksums_sha256,
            "storage": "BACKBLAZE B2",
            "candidates": [
                {
                    "candidateId": candidate.candidate_id,
                    "assetSha256": candidate.asset_sha256,
                    "manifestHash": candidate.manifest_hash,
                    "manifestVerifyReturned": True,
                    "b2DownloadedAssetHashMatched": True,
                }
                for candidate in verified.index.candidates
            ],
            "costDisclosure": verified.index.cost_disclosure,
        }
        _write_json("LIVE_PROOF_INDEX_SANITIZED.json", sanitized_index)
        _write_json("LIVE_PROOF_VERIFICATION.json", verification)
        _write_json("LIVE_PROOF_PUBLICATION.json", verification)
        print(
            "LIVE proof publication PASS: "
            f"status={status} candidates=2 manifests=2 assetHashes=2 providerCalls=0"
        )
        return 0
    finally:
        store.backend.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-evidence",
        type=Path,
        default=DEFAULT_SOURCE_EVIDENCE,
        help="Secret-safe LIVE gate output directory under evidence/.",
    )
    parser.add_argument(
        "--proof-version",
        choices=("live-v1", "live-v2"),
        default="live-v2",
    )
    args = parser.parse_args()
    try:
        source_evidence = _resolve_source_evidence(args.source_evidence)
        proof_version = cast(Literal["live-v1", "live-v2"], args.proof_version)
        return run(source_evidence, proof_version)
    except Exception as exc:
        print(
            f"LIVE proof publication stopped safely: {type(exc).__name__}: "
            f"{sanitize_text(str(exc))}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
