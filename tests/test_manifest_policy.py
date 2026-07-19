from __future__ import annotations

from pathlib import Path

import pytest
from genblaze_core import Asset, AudioMetadata, Manifest, Modality, Pipeline
from genblaze_core.testing import MockProvider

from framefoley_spike.genblaze_sfx import CandidateAttempt, LiveSpikeError
from framefoley_spike.provenance import DerivativeRecord, sha256_file


def _manifest_for(path: Path) -> tuple[Manifest, str, str]:
    digest = sha256_file(path)
    asset = Asset(
        url="fixture://framefoley/test.wav",
        media_type="audio/wav",
        sha256=digest,
        size_bytes=path.stat().st_size,
    )
    asset.audio = AudioMetadata(sample_rate=48_000, channels=1, codec="pcm_s16le")
    result = (
        Pipeline("manifest-policy-test")
        .step(
            MockProvider(name="fixture", assets=[asset]),
            model="fixture-v1",
            prompt="deterministic fixture",
            modality=Modality.AUDIO,
        )
        .run(timeout=10, max_retries=0, raise_on_failure=True)
    )
    return result.manifest, result.run.run_id, asset.asset_id


def test_manifest_round_trip_verifies(fixture_wav: Path) -> None:
    manifest, _, _ = _manifest_for(fixture_wav)
    assert manifest.verify() is True
    restored = Manifest.model_validate_json(manifest.to_canonical_json())
    assert restored.verify() is True
    assert restored.canonical_hash == manifest.canonical_hash


def test_false_manifest_cannot_be_labeled_verified(fixture_wav: Path) -> None:
    manifest, _, _ = _manifest_for(fixture_wav)
    manifest.canonical_hash = "0" * 64
    assert manifest.verify() is False
    attempt = CandidateAttempt()
    attempt.record_provider_success(fixture_wav.read_bytes())
    attempt.store(lambda _payload: None)
    with pytest.raises(LiveSpikeError):
        attempt.mark_verified(manifest.verify())
    assert attempt.complete is False
    assert attempt.verified is False


def test_repair_history_references_original_run_and_asset(fixture_wav: Path) -> None:
    manifest, run_id, asset_id = _manifest_for(fixture_wav)
    record = DerivativeRecord(
        schema_version=1,
        original_run_id=run_id,
        original_asset_id=asset_id,
        original_asset_sha256=sha256_file(fixture_wav),
        canonical_manifest_hash=manifest.canonical_hash,
        derivative_sha256="a" * 64,
        repairs=("trim_leading_silence",),
    )
    payload = record.to_dict()
    assert payload["original_run_id"] == run_id
    assert payload["original_asset_id"] == asset_id
    assert payload["canonical_manifest_hash"] == manifest.canonical_hash
