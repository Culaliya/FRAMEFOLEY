from __future__ import annotations

import wave
from pathlib import Path

from framefoley_spike.provenance import sha256_bytes, sha256_file
from framefoley_spike.qc import QcVerdict, inspect_audio, repair_audio


def test_sha256_is_stable(fixture_wav: Path) -> None:
    assert sha256_file(fixture_wav) == sha256_bytes(fixture_wav.read_bytes())
    assert sha256_file(fixture_wav) == sha256_file(fixture_wav)


def test_valid_fixture_is_pass_or_repairable(fixture_wav: Path) -> None:
    report = inspect_audio(fixture_wav)
    assert report.verdict in {QcVerdict.PASS, QcVerdict.REPAIRABLE}
    assert report.metrics.decode_ok is True
    assert report.metrics.sample_rate_hz == 48_000
    assert report.metrics.channels == 1


def test_silence_requires_regeneration(tmp_path: Path) -> None:
    path = tmp_path / "silence.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(b"\x00\x00" * int(0.6 * 48_000))
    report = inspect_audio(path)
    assert report.verdict is QcVerdict.REGENERATE
    assert "effectively_silent" in report.reasons


def test_corrupt_bytes_fail(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.wav"
    path.write_bytes(b"not an audio file")
    report = inspect_audio(path)
    assert report.verdict is QcVerdict.FAILED
    assert report.metrics.decode_ok is False


def test_repair_output_is_48khz_mono_wav(fixture_wav: Path, tmp_path: Path) -> None:
    before = inspect_audio(fixture_wav)
    repaired = tmp_path / "repaired.wav"
    repairs = repair_audio(fixture_wav, repaired, before)
    after = inspect_audio(repaired)
    assert "format_pcm_s16le_wav" in repairs
    assert after.verdict is QcVerdict.PASS
    assert after.metrics.sample_rate_hz == 48_000
    assert after.metrics.channels == 1
