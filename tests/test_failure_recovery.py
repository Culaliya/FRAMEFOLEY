from __future__ import annotations

from pathlib import Path

import pytest

from framefoley_spike.b2 import StorageSpikeError, create_backend
from framefoley_spike.config import SpikeConfig
from framefoley_spike.genblaze_sfx import (
    CandidateAttempt,
    CandidateStage,
    LiveSpikeError,
    cached_demo_descriptor,
)
from framefoley_spike.provenance import scan_evidence_tree


def _config() -> SpikeConfig:
    return SpikeConfig("key-id", "secret-value", "private-bucket", "us-west-004", "eleven")


def test_invalid_b2_credentials_are_typed_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> None:
        raise RuntimeError("B2_APP_KEY=secret-value X-Amz-Signature=bad")

    monkeypatch.setattr("framefoley_spike.b2.S3StorageBackend.for_backblaze", fail)
    with pytest.raises(StorageSpikeError) as captured:
        create_backend(_config())
    assert captured.value.stage == "storage_preflight"
    assert captured.value.code == "b2_preflight_failed"
    assert "secret-value" not in str(captured.value)


@pytest.mark.parametrize("code", ["provider_timeout", "provider_model_error"])
def test_provider_failures_never_verify(code: str) -> None:
    attempt = CandidateAttempt()
    attempt.record_provider_failure(code)
    assert attempt.stage is CandidateStage.FAILED
    assert attempt.complete is False
    assert attempt.verified is False
    assert attempt.error_code == code


def test_storage_failure_after_generation_is_incomplete_and_retryable() -> None:
    attempt = CandidateAttempt()
    payload = b"real provider bytes retained locally"
    attempt.record_provider_success(payload)
    calls = 0

    def failing_upload(_payload: bytes) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("temporary B2 upload failure")

    with pytest.raises(LiveSpikeError):
        attempt.store(failing_upload)
    assert attempt.stage is CandidateStage.STORAGE_FAILED
    assert attempt.complete is False
    assert attempt.can_retry_storage_without_generation is True
    assert attempt.provider_attempts == 1

    attempt.store(lambda actual: actual == payload or None)
    attempt.mark_verified(True)
    assert attempt.complete is True
    assert attempt.provider_attempts == 1
    assert attempt.storage_attempts == 2
    assert calls == 1


def test_retry_budget_is_bounded() -> None:
    attempt = CandidateAttempt(max_provider_attempts=2)
    attempt.record_provider_success(b"first")
    attempt.record_provider_success(b"retry")
    with pytest.raises(LiveSpikeError) as captured:
        attempt.record_provider_success(b"forbidden-third")
    assert captured.value.code == "retry_budget_exhausted"
    assert attempt.provider_attempts == 2


def test_cached_demo_is_never_labeled_live() -> None:
    descriptor = cached_demo_descriptor("provider_unavailable")
    assert descriptor["mode"] == "DEMO_CACHE"
    assert descriptor["label"] == "DEMO CACHE"
    assert descriptor["live_generation"] is False


def test_evidence_secret_scan_detects_and_accepts(tmp_path: Path) -> None:
    safe = tmp_path / "safe.json"
    safe.write_text('{"status":"PASS","B2_APP_KEY":"[REDACTED]"}', encoding="utf-8")
    assert scan_evidence_tree(tmp_path) == {}
    unsafe = tmp_path / "unsafe.log"
    unsafe.write_text("X-Amz-Signature=secret", encoding="utf-8")
    assert "unsafe.log" in scan_evidence_tree(tmp_path)
