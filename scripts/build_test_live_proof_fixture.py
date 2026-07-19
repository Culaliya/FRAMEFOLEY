"""Build a deterministic local-only proof fixture for Phase 2 tests.

This script never contacts a provider or B2. Its output lives under ignored
local test storage and is never production evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from framefoley_api.generation import _api_qc
from framefoley_api.live_proof import write_immutable_proof_bundle
from framefoley_api.media import convert_wav_to_ogg
from framefoley_api.models import (
    LiveProofCandidatePayloadV1,
    LiveProofCandidateV1,
    LiveProofEventV1,
    LiveProofIndexV1,
)
from framefoley_api.storage import LocalObjectStore
from genblaze_core import Manifest

from framefoley_spike.qc import inspect_audio

ROOT = Path(__file__).resolve().parents[1]
COST_DISCLOSURE = (
    "The provider reported USD 0.00 for the recorded gate; this is not evidence "
    "that an ElevenLabs account spend or usage cap is active."
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(output: Path) -> str:
    raw_path = ROOT / "artifacts" / "phase0" / "work" / "live" / "provider-output.mp3"
    approved_path = ROOT / "artifacts" / "phase0" / "repaired-sfx.wav"
    waveform_path = ROOT / "artifacts" / "phase0" / "waveform.png"
    manifest_path = ROOT / "artifacts" / "phase0" / "manifest.json"
    source_path = ROOT / "demo" / "jelly-relay.mp4"
    thumbnail_path = ROOT / "demo" / "jelly-relay-thumbnail.webp"
    event_payload = json.loads((ROOT / "demo" / "jelly-relay-events.json").read_text())[0]

    raw = raw_path.read_bytes()
    approved = approved_path.read_bytes()
    waveform = waveform_path.read_bytes()
    ogg_path = output.parent / "phase2-proof-fixture.ogg"
    ogg_path.parent.mkdir(parents=True, exist_ok=True)
    approved_path_copy = output.parent / "phase2-proof-fixture.wav"
    approved_path_copy.write_bytes(approved)
    convert_wav_to_ogg(approved_path_copy, ogg_path)
    ogg = ogg_path.read_bytes()
    approved_path_copy.unlink(missing_ok=True)
    ogg_path.unlink(missing_ok=True)

    original_manifest = Manifest.model_validate_json(manifest_path.read_bytes())
    if original_manifest.verify() is not True:
        raise ValueError("the retained Phase 0 LIVE manifest no longer verifies")
    second_run = original_manifest.run.model_copy(deep=True)
    second_run.run_id = "22222222-2222-4222-8222-222222222222"
    second_run.steps[0].run_id = second_run.run_id
    second_run.steps[0].step_id = "33333333-3333-4333-8333-333333333333"
    second_run.steps[0].assets[0].asset_id = "44444444-4444-4444-8444-444444444444"
    second_manifest = Manifest.from_run(second_run)
    if second_manifest.verify() is not True:
        raise ValueError("the local proof contract manifest did not verify")

    before = _api_qc(inspect_audio(raw_path))
    repairs = ["trim_trailing_silence", "raise_low_gain", "resample_48000_hz", "downmix_mono"]
    after = _api_qc(inspect_audio(approved_path), repairs=tuple(repairs))
    if before.verdict not in {"pass", "repairable"} or after.verdict != "pass":
        raise ValueError("the local proof audio fixture does not pass deterministic QC")

    safe_event = LiveProofEventV1.model_validate(event_payload)
    source = source_path.read_bytes()
    thumbnail = thumbnail_path.read_bytes()
    objects: dict[str, bytes] = {
        "source/original.mp4": source,
        "source/preview.mp4": source,
        "source/thumbnail.webp": thumbnail,
        "events/event.json": (
            json.dumps(
                safe_event.model_dump(mode="json", by_alias=True, exclude_none=True),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode(),
    }
    started = datetime(2026, 7, 19, 6, 13, 10, tzinfo=UTC)
    proof_candidates: list[LiveProofCandidateV1] = []
    manifests = {"clean": original_manifest, "character": second_manifest}
    candidate_ids = {"clean": "cand_proofclean01", "character": "cand_proofchar02"}
    for offset, variant_value in enumerate(("clean", "character")):
        variant = cast(Literal["clean", "character"], variant_value)
        manifest = manifests[variant]
        manifest_bytes = manifest.to_canonical_json().encode("utf-8")
        candidate_id = candidate_ids[variant]
        objects[f"candidates/{variant}/raw-audio.mp3"] = raw
        objects[f"candidates/{variant}/approved-audio.wav"] = approved
        objects[f"candidates/{variant}/approved-audio.ogg"] = ogg
        objects[f"manifests/{variant}.json"] = manifest_bytes
        objects[f"qc/{variant}-before.json"] = (
            json.dumps(before.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
            + "\n"
        ).encode()
        objects[f"qc/{variant}-after.json"] = (
            json.dumps(after.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
            + "\n"
        ).encode()
        objects[f"waveforms/{variant}.png"] = waveform
        private_record = LiveProofCandidatePayloadV1(
            candidate_id=candidate_id,
            variant=variant,
            prompt=manifest.run.steps[0].prompt,
            approved_wav_sha256=_sha256(approved),
            approved_ogg_sha256=_sha256(ogg),
            waveform_sha256=_sha256(waveform),
            manifest_object_sha256=_sha256(manifest_bytes),
            started_at=started + timedelta(seconds=offset * 12),
            ended_at=started + timedelta(seconds=4.2 + offset * 12),
        )
        objects[f"candidates/{variant}/candidate.json"] = (
            json.dumps(
                private_record.model_dump(mode="json", by_alias=True),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode()
        proof_candidates.append(
            LiveProofCandidateV1(
                candidate_id=candidate_id,
                variant=variant,
                run_id=manifest.run.run_id,
                asset_sha256=_sha256(raw),
                manifest_hash=manifest.canonical_hash,
                manifest_verified=True,
                qc_before=cast(Literal["pass", "repairable"], before.verdict),
                qc_after="pass",
                repairs=repairs,
                latency_seconds=4.2 + offset,
            )
        )
    index = LiveProofIndexV1(
        proof_version="live-v1",
        captured_at=datetime(2026, 7, 19, 6, 13, 40, tzinfo=UTC),
        source_label="LIVE",
        provider="elevenlabs-sfx",
        model="eleven_text_to_sound_v2",
        provider_call_count=2,
        event_count=1,
        candidate_count=2,
        b2_object_count=24,
        candidates=proof_candidates,
        cost_disclosure=COST_DISCLOSURE,
    )
    store = LocalObjectStore(output)
    return write_immutable_proof_bundle(store, index, objects)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".data" / "e2e" / "objects",
        help="LocalObjectStore root for the ignored fixture.",
    )
    args = parser.parse_args()
    status = build(args.output)
    print(f"Local MOCKED proof contract fixture: {status}; providerCalls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
