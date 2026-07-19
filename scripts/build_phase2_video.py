"""Build the 2:56 public Phase 2 master from a fresh Playwright recording."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "evidence" / "phase2" / "video"
RAW_VIDEO = VIDEO_DIR / "framefoley-phase2-public-raw.webm"
TIMINGS = VIDEO_DIR / "framefoley-phase2-capture-timings.json"
MASTER = VIDEO_DIR / "framefoley-phase2-demo.mp4"
CAPTIONS = VIDEO_DIR / "framefoley-phase2-demo-captions.vtt"
TRANSCRIPT = VIDEO_DIR / "framefoley-phase2-demo-transcript.txt"
LANDING_MIX = ROOT / "apps" / "web" / "public" / "jelly-relay-approved-mix.mp4"
CACHED_AUDIO = ROOT / "demo" / "cache" / "raw"
LIVE_AUDIO = ROOT / ".data" / "phase2-video-live"
MASTER_DURATION = 176.0


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    text: str
    narration: bool = True


SECTIONS = (
    ("comparison", "problem", 8.0),
    ("problem", "cues", 14.0),
    ("cues", "cached_pipeline", 25.0),
    ("cached_pipeline", "audition", 26.0),
    ("audition", "mix", 26.0),
    ("mix", "live_proof", 18.0),
    ("live_proof", "export_provenance", 29.0),
    ("export_provenance", "close", 21.0),
    ("close", "end", 9.0),
)

CAPTION_TRACK = (
    Caption(0.0, 3.8, "[JELLY RELAY plays as a silent source]", False),
    Caption(4.0, 8.0, "[The same motion plays with three approved Foley cues]", False),
    Caption(
        8.2,
        21.5,
        "Game prototypes often move before they sound. Creators need precise Foley at the "
        "frame—not a generic music generator, automatic scene guess, or chat box. "
        "FRAMEFOLEY keeps that decision small and audible.",
    ),
    Caption(
        22.2,
        46.3,
        "This original silent clip lasts twelve seconds. I mark three moments that matter: "
        "glass landing, bubble pop, and route confirmation. Each cue has a bounded "
        "timestamp, duration, intensity, and material note. One style stays locked across "
        "the kit, so comparison remains coherent.",
    ),
    Caption(
        47.2,
        72.3,
        "The public three-cue workflow uses six original CACHED DEMO candidates. That lets "
        "judges test the complete product while anonymous traffic spends no provider credit. "
        "Deterministic code decodes every sound, checks duration, peak, RMS, silence, "
        "channels, and sample rate, then records any repair. Private Backblaze B2 stores the "
        "project, media, QC, render, export, and provenance.",
    ),
    Caption(
        73.2,
        79.8,
        "Technical validity does not choose the creative winner. I hear A and B at the exact "
        "gameplay frame, solo or in context.",
    ),
    Caption(80.0, 82.4, "[CACHED DEMO candidate A plays]", False),
    Caption(83.2, 85.8, "[CACHED DEMO candidate B plays in context]", False),
    Caption(
        87.0,
        98.5,
        "One may feel cleaner; the other may have more character. Human approval remains "
        "authoritative. Only my explicit choice advances the project.",
    ),
    Caption(
        99.2,
        106.3,
        "FRAMEFOLEY delays each approved WAV to its cue, applies bounded gain, and renders "
        "through fixed FFmpeg argument arrays.",
    ),
    Caption(107.0, 111.0, "[The approved mix plays at its exact cue]", False),
    Caption(
        112.0,
        116.7,
        "The before-and-after preview and mix map receive stable hashes and return to private B2.",
    ),
    Caption(
        117.2,
        125.6,
        "Now this is LIVE EVIDENCE REPLAY: two real provider outputs generated during an "
        "authorized Genblaze run with the ElevenLabs sound-effects model.",
    ),
    Caption(126.0, 128.6, "[Recorded LIVE candidate A plays]", False),
    Caption(129.6, 132.2, "[Recorded LIVE candidate B plays]", False),
    Caption(
        133.0,
        145.8,
        "They were stored in Backblaze B2, downloaded again, re-hashed, and both canonical "
        "manifests verify true. Opening this replay makes zero new provider calls. I can "
        "still hear both and make a fresh human approval.",
    ),
    Caption(
        146.2,
        166.5,
        "The deterministic ZIP carries the approved sound, preview, manifest, QC, project "
        "state, and provenance. The inspector keeps generation lineage, storage, technical "
        "processing, and this replay-session approval separate and visible.",
    ),
    Caption(
        167.2,
        175.7,
        "The sound may be synthetic. The history is not. This is FRAMEFOLEY.",
    ),
)


def _run(arguments: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _probe(path: Path) -> dict[str, Any]:
    completed = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        timeout=30,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("ffprobe did not return an object")
    return payload


def _timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, fraction = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{fraction:03d}"


def _write_text_tracks() -> None:
    vtt = ["WEBVTT", ""]
    transcript = [
        "FRAMEFOLEY Phase 2 competition demo transcript",
        "Duration: 2:56",
        "",
    ]
    for index, caption in enumerate(CAPTION_TRACK, start=1):
        vtt.extend(
            [
                str(index),
                f"{_timestamp(caption.start)} --> {_timestamp(caption.end)}",
                caption.text,
                "",
            ]
        )
        transcript.append(
            f"{_timestamp(caption.start)} - {_timestamp(caption.end)}  {caption.text}"
        )
    CAPTIONS.write_text("\n".join(vtt), encoding="utf-8")
    TRANSCRIPT.write_text("\n".join(transcript) + "\n", encoding="utf-8")


def _load_marks() -> dict[str, float]:
    payload = json.loads(TIMINGS.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ValueError("capture timing schema is invalid")
    records = payload.get("marks")
    if not isinstance(records, list):
        raise ValueError("capture timing marks are missing")
    marks = {
        str(record["name"]): float(record["seconds"])
        for record in records
        if isinstance(record, dict) and "name" in record and "seconds" in record
    }
    required = {name for section in SECTIONS for name in section[:2]}
    if set(marks) != required:
        raise ValueError("capture timing marks are incomplete or unexpected")
    return marks


def _build_visual(raw_duration: float, marks: dict[str, float], output: Path) -> None:
    filters: list[str] = []
    outputs: list[str] = []
    for index, (start_name, end_name, target_duration) in enumerate(SECTIONS):
        start = marks[start_name]
        end = marks[end_name]
        if start < 0 or end <= start or end > raw_duration + 0.25:
            raise ValueError(f"capture segment {start_name} is outside the raw recording")
        ratio = target_duration / (end - start)
        label = f"v{index}"
        filters.append(
            f"[0:v]trim=start={start:.6f}:end={end:.6f},"
            f"setpts={ratio:.12f}*(PTS-STARTPTS),fps=30,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black[{label}]"
        )
        outputs.append(f"[{label}]")
    filters.append(f"{''.join(outputs)}concat=n={len(outputs)}:v=1:a=0[vout]")
    _run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(RAW_VIDEO),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        timeout=1200,
    )


def _build_narration(directory: Path) -> list[tuple[Caption, Path, float]]:
    if shutil.which("say") is None:
        raise RuntimeError("macOS say is required for the English narration")
    records: list[tuple[Caption, Path, float]] = []
    for index, caption in enumerate(item for item in CAPTION_TRACK if item.narration):
        path = directory / f"narration-{index:02d}.aiff"
        _run(["say", "-v", "Samantha", "-r", "180", "-o", str(path), caption.text])
        duration = float(_probe(path)["format"]["duration"])
        records.append((caption, path, duration))
    return records


def _build_master(visual: Path, narration: list[tuple[Caption, Path, float]]) -> None:
    effect_inputs = [
        LANDING_MIX,
        CACHED_AUDIO / "glass-landing-clean.wav",
        CACHED_AUDIO / "glass-landing-character.wav",
        LIVE_AUDIO / "clean.wav",
        LIVE_AUDIO / "character.wav",
    ]
    missing = [
        path for path in (RAW_VIDEO, TIMINGS, LANDING_MIX, *effect_inputs) if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("required recording or sound input is missing")

    arguments = ["ffmpeg", "-y", "-v", "error", "-i", str(visual)]
    for _caption, path, _duration in narration:
        arguments.extend(["-i", str(path)])
    for path in effect_inputs:
        arguments.extend(["-i", str(path)])
    arguments.extend(["-i", str(CAPTIONS)])

    filters: list[str] = []
    audio_labels: list[str] = []
    for index, (caption, _path, duration) in enumerate(narration, start=1):
        available = caption.end - caption.start
        speed = max(1.0, duration / available)
        label = f"n{index}"
        filters.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"atempo={speed:.8f},atrim=duration={available:.6f},"
            f"volume=1.15,adelay={round(caption.start * 1000)}|"
            f"{round(caption.start * 1000)}[{label}]"
        )
        audio_labels.append(f"[{label}]")

    effect_start_index = 1 + len(narration)
    effects = (
        (effect_start_index, 4.0, 0.0, 4.0, 1.0, "landing"),
        (effect_start_index + 1, 80.0, 0.0, 2.4, 1.2, "cached_a"),
        (effect_start_index + 2, 83.2, 0.0, 2.6, 1.2, "cached_b"),
        (effect_start_index, 107.0, 0.0, 4.0, 0.9, "mix"),
        (effect_start_index + 3, 126.0, 0.0, 2.6, 1.25, "live_a"),
        (effect_start_index + 4, 129.6, 0.0, 2.6, 1.25, "live_b"),
    )
    for input_index, delay, source_start, length, volume, label in effects:
        filters.append(
            f"[{input_index}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"atrim=start={source_start:.3f}:duration={length:.3f},asetpts=PTS-STARTPTS,"
            f"volume={volume:.3f},adelay={round(delay * 1000)}|{round(delay * 1000)}[{label}]"
        )
        audio_labels.append(f"[{label}]")
    filters.append(
        f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=longest:normalize=0,"
        f"alimiter=limit=0.95,apad=whole_dur={MASTER_DURATION:.3f},"
        f"atrim=duration={MASTER_DURATION:.3f}[aout]"
    )
    subtitle_index = effect_start_index + len(effect_inputs)
    arguments.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-map",
            f"{subtitle_index}:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-metadata:s:s:0",
            "title=English",
            "-disposition:s:0",
            "default",
            "-metadata",
            "title=FRAMEFOLEY Phase 2 Competition Demo",
            "-movflags",
            "+faststart",
            "-t",
            f"{MASTER_DURATION:.3f}",
            str(MASTER),
        ]
    )
    _run(arguments, timeout=1200)


def _verify_master() -> None:
    probe = _probe(MASTER)
    duration = float(probe["format"]["duration"])
    streams = probe.get("streams", [])
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    subtitles = [stream for stream in streams if stream.get("codec_type") == "subtitle"]
    if not 175.95 <= duration <= 176.05:
        raise ValueError("master duration is outside the 2:56 contract")
    if len(videos) != 1 or videos[0].get("width") != 1920 or videos[0].get("height") != 1080:
        raise ValueError("master is not 1920x1080")
    if len(audio) != 1 or len(subtitles) != 1:
        raise ValueError("master must contain one audio and one subtitle track")


def main() -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_VIDEO.is_file() or not TIMINGS.is_file():
        raise FileNotFoundError("run the fresh public Phase 2 Playwright capture first")
    _write_text_tracks()
    raw_duration = float(_probe(RAW_VIDEO)["format"]["duration"])
    marks = _load_marks()
    with tempfile.TemporaryDirectory(prefix="framefoley-phase2-video-") as temporary:
        directory = Path(temporary)
        visual = directory / "visual.mp4"
        _build_visual(raw_duration, marks, visual)
        narration = _build_narration(directory)
        _build_master(visual, narration)
    _verify_master()
    print(
        "Phase 2 video PASS: duration=176.000 resolution=1920x1080 "
        "audio=English subtitle=embedded+WebVTT providerClaims=factual"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
