"""Deterministic FFmpeg/ffprobe audio inspection and repair."""

from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from framefoley_spike.provenance import sanitize_text, sha256_file

ANALYSIS_SAMPLE_RATE = 48_000
TARGET_MIN_SECONDS = 0.15
TARGET_MAX_SECONDS = 1.50
EFFECTIVE_SILENCE_RMS_DBFS = -50.0
LOW_GAIN_RMS_DBFS = -30.0
NEAR_CLIP_PEAK_DBFS = -0.5
LEADING_SILENCE_LIMIT_MS = 100.0
TRAILING_SILENCE_LIMIT_MS = 250.0
SILENCE_GATE_DBFS = -50.0
REPAIR_PEAK_TARGET_DBFS = -3.0
LIMITER_CEILING_DBFS = -1.0


class QcVerdict(StrEnum):
    PASS = "PASS"
    REPAIRABLE = "REPAIRABLE"
    REGENERATE = "REGENERATE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class QcMetrics:
    decode_ok: bool
    duration_seconds: float | None
    sample_rate_hz: int | None
    channels: int | None
    peak_dbfs: float | None
    rms_dbfs: float | None
    leading_silence_ms: float | None
    trailing_silence_ms: float | None
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QcReport:
    schema_version: int
    verdict: QcVerdict
    metrics: QcMetrics
    reasons: tuple[str, ...]
    thresholds: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload


class QcError(RuntimeError):
    pass


def _dbfs(amplitude: float) -> float:
    if amplitude <= 0.0:
        return -120.0
    return max(-120.0, 20.0 * math.log10(amplitude))


def _run(arguments: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(arguments, check=False, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QcError(sanitize_text(str(exc))) from exc


def inspect_audio(
    path: Path,
    *,
    duration_window: tuple[float, float] = (TARGET_MIN_SECONDS, TARGET_MAX_SECONDS),
) -> QcReport:
    """Decode through FFmpeg and classify fixed technical thresholds."""

    digest = sha256_file(path)
    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if ffprobe is None or ffmpeg is None:
        metrics = QcMetrics(False, None, None, None, None, None, None, None, digest)
        return _report(QcVerdict.FAILED, metrics, ("ffmpeg_or_ffprobe_missing",))

    probe = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels:format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    if probe.returncode != 0:
        metrics = QcMetrics(False, None, None, None, None, None, None, None, digest)
        return _report(QcVerdict.FAILED, metrics, ("ffprobe_decode_failed",))

    try:
        parsed = json.loads(probe.stdout.decode("utf-8"))
        stream = parsed["streams"][0]
        duration = float(parsed["format"]["duration"])
        sample_rate = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        metrics = QcMetrics(False, None, None, None, None, None, None, None, digest)
        return _report(QcVerdict.FAILED, metrics, ("ffprobe_metadata_invalid",))

    decoded = _run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            str(ANALYSIS_SAMPLE_RATE),
            "-f",
            "f32le",
            "pipe:1",
        ]
    )
    if decoded.returncode != 0 or len(decoded.stdout) < 4:
        metrics = QcMetrics(
            False,
            duration,
            sample_rate,
            channels,
            None,
            None,
            None,
            None,
            digest,
        )
        return _report(QcVerdict.FAILED, metrics, ("ffmpeg_decode_failed",))

    sample_count = len(decoded.stdout) // 4
    samples = tuple(
        value[0] for value in struct.iter_unpack("<f", decoded.stdout[: sample_count * 4])
    )
    peak = max(abs(value) for value in samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    gate = 10.0 ** (SILENCE_GATE_DBFS / 20.0)
    audible = [index for index, value in enumerate(samples) if abs(value) >= gate]
    if audible:
        leading_ms = audible[0] * 1000.0 / ANALYSIS_SAMPLE_RATE
        trailing_ms = (len(samples) - audible[-1] - 1) * 1000.0 / ANALYSIS_SAMPLE_RATE
    else:
        leading_ms = duration * 1000.0
        trailing_ms = duration * 1000.0

    metrics = QcMetrics(
        decode_ok=True,
        duration_seconds=round(duration, 6),
        sample_rate_hz=sample_rate,
        channels=channels,
        peak_dbfs=round(_dbfs(peak), 3),
        rms_dbfs=round(_dbfs(rms), 3),
        leading_silence_ms=round(leading_ms, 3),
        trailing_silence_ms=round(trailing_ms, 3),
        sha256=digest,
    )
    return classify_metrics(metrics, duration_window=duration_window)


def classify_metrics(
    metrics: QcMetrics,
    *,
    duration_window: tuple[float, float] = (TARGET_MIN_SECONDS, TARGET_MAX_SECONDS),
) -> QcReport:
    if not metrics.decode_ok:
        return _report(QcVerdict.FAILED, metrics, ("decode_failed",))

    assert metrics.duration_seconds is not None
    assert metrics.rms_dbfs is not None
    assert metrics.peak_dbfs is not None
    assert metrics.leading_silence_ms is not None
    assert metrics.trailing_silence_ms is not None
    assert metrics.sample_rate_hz is not None
    assert metrics.channels is not None

    regenerate: list[str] = []
    target_min_seconds, target_max_seconds = duration_window
    if not target_min_seconds <= metrics.duration_seconds <= target_max_seconds:
        regenerate.append("duration_outside_spike_window")
    if metrics.rms_dbfs < EFFECTIVE_SILENCE_RMS_DBFS:
        regenerate.append("effectively_silent")
    if regenerate:
        return _report(
            QcVerdict.REGENERATE,
            metrics,
            tuple(regenerate),
            duration_window=duration_window,
        )

    repairable: list[str] = []
    if metrics.leading_silence_ms > LEADING_SILENCE_LIMIT_MS:
        repairable.append("trim_leading_silence")
    if metrics.trailing_silence_ms > TRAILING_SILENCE_LIMIT_MS:
        repairable.append("trim_trailing_silence")
    if metrics.peak_dbfs >= NEAR_CLIP_PEAK_DBFS:
        repairable.append("limit_near_clipping")
    if metrics.rms_dbfs < LOW_GAIN_RMS_DBFS:
        repairable.append("raise_low_gain")
    if metrics.sample_rate_hz != ANALYSIS_SAMPLE_RATE:
        repairable.append("resample_48000_hz")
    if metrics.channels != 1:
        repairable.append("downmix_mono")
    if repairable:
        return _report(
            QcVerdict.REPAIRABLE,
            metrics,
            tuple(repairable),
            duration_window=duration_window,
        )
    return _report(QcVerdict.PASS, metrics, (), duration_window=duration_window)


def _report(
    verdict: QcVerdict,
    metrics: QcMetrics,
    reasons: tuple[str, ...],
    *,
    duration_window: tuple[float, float] = (TARGET_MIN_SECONDS, TARGET_MAX_SECONDS),
) -> QcReport:
    target_min_seconds, target_max_seconds = duration_window
    return QcReport(
        schema_version=1,
        verdict=verdict,
        metrics=metrics,
        reasons=reasons,
        thresholds={
            "target_min_seconds": target_min_seconds,
            "target_max_seconds": target_max_seconds,
            "effectively_silent_rms_dbfs_below": EFFECTIVE_SILENCE_RMS_DBFS,
            "near_clip_peak_dbfs_at_or_above": NEAR_CLIP_PEAK_DBFS,
            "leading_silence_limit_ms": LEADING_SILENCE_LIMIT_MS,
            "trailing_silence_limit_ms": TRAILING_SILENCE_LIMIT_MS,
            "silence_gate_dbfs": SILENCE_GATE_DBFS,
            "repair_peak_target_dbfs": REPAIR_PEAK_TARGET_DBFS,
            "limiter_ceiling_dbfs": LIMITER_CEILING_DBFS,
        },
    )


def repair_audio(source: Path, destination: Path, before: QcReport) -> tuple[str, ...]:
    """Trim, normalize where needed, limit, and emit 48 kHz mono PCM WAV."""

    if before.verdict in {QcVerdict.FAILED, QcVerdict.REGENERATE}:
        raise QcError(f"cannot repair verdict {before.verdict.value}")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise QcError("ffmpeg not installed")

    peak = before.metrics.peak_dbfs or -120.0
    rms = before.metrics.rms_dbfs or -120.0
    gain_db = 0.0
    if peak >= NEAR_CLIP_PEAK_DBFS:
        gain_db = REPAIR_PEAK_TARGET_DBFS - peak
    elif rms < LOW_GAIN_RMS_DBFS:
        gain_db = min(12.0, -24.0 - rms)

    filters = (
        "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:"
        "start_silence=0.01:stop_periods=-1:stop_duration=0:stop_threshold=-50dB:"
        f"stop_silence=0.05,volume={gain_db:.3f}dB,alimiter=limit=0.891251:attack=5:release=50"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = _run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-af",
            filters,
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        timeout=45,
    )
    if completed.returncode != 0:
        error = sanitize_text(completed.stderr.decode("utf-8", errors="replace"))
        raise QcError(f"ffmpeg repair failed: {error[:300]}")
    repairs = list(before.reasons)
    if "format_pcm_s16le_wav" not in repairs:
        repairs.append("format_pcm_s16le_wav")
    return tuple(repairs)


def render_waveform(source: Path, destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise QcError("ffmpeg not installed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = _run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-filter_complex",
            "aformat=channel_layouts=mono,showwavespic=s=1200x320:colors=0xB7FF3C",
            "-frames:v",
            "1",
            str(destination),
        ],
        timeout=45,
    )
    if completed.returncode != 0:
        error = sanitize_text(completed.stderr.decode("utf-8", errors="replace"))
        raise QcError(f"waveform render failed: {error[:300]}")
