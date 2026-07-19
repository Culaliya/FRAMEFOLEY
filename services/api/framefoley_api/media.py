"""Fixed-array ffprobe/FFmpeg media validation and transformations."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from framefoley_api.errors import PublicError
from framefoley_spike.provenance import sanitize_text

MAX_SOURCE_BYTES = 30 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}


@dataclass(frozen=True)
class VideoInspection:
    duration_seconds: float
    width: int
    height: int
    fps: float
    has_audio: bool


@dataclass(frozen=True)
class PreparedSource:
    inspection: VideoInspection
    original: bytes
    preview: bytes
    thumbnail: bytes
    sha256: str


def _run(arguments: list[str], *, timeout: int) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(arguments, check=False, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PublicError("MEDIA_TOOL_FAILED", sanitize_text(str(exc)), status_code=500) from exc


def _required_tool(name: str) -> str:
    value = shutil.which(name)
    if not value:
        raise PublicError("MEDIA_TOOL_MISSING", f"{name} is not installed.", status_code=503)
    return value


def inspect_video(path: Path) -> VideoInspection:
    completed = _run(
        [
            _required_tool("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        timeout=30,
    )
    if completed.returncode != 0:
        raise PublicError(
            "SOURCE_DECODE_FAILED",
            "The uploaded video could not be decoded.",
            status_code=422,
        )
    try:
        payload = json.loads(completed.stdout)
        video = next(stream for stream in payload["streams"] if stream["codec_type"] == "video")
        numerator, denominator = video["avg_frame_rate"].split("/", 1)
        fps = float(numerator) / float(denominator)
        return VideoInspection(
            duration_seconds=float(payload["format"]["duration"]),
            width=int(video["width"]),
            height=int(video["height"]),
            fps=fps,
            has_audio=any(stream["codec_type"] == "audio" for stream in payload["streams"]),
        )
    except (KeyError, StopIteration, TypeError, ValueError, ZeroDivisionError) as exc:
        raise PublicError(
            "SOURCE_METADATA_INVALID",
            "Video metadata is incomplete.",
            status_code=422,
        ) from exc


def validate_video(inspection: VideoInspection, size_bytes: int) -> None:
    if size_bytes > MAX_SOURCE_BYTES:
        raise PublicError(
            "SOURCE_TOO_LARGE", "Video must be no larger than 30 MB.", status_code=422
        )
    if not 8 <= inspection.duration_seconds <= 15:
        raise PublicError(
            "SOURCE_DURATION_INVALID",
            "Video must be between 8 and 15 seconds.",
            status_code=422,
        )
    if min(inspection.width, inspection.height) < 480:
        raise PublicError("SOURCE_RESOLUTION_LOW", "Video must be at least 480p.", status_code=422)
    if inspection.width > 1920 or inspection.height > 1080:
        raise PublicError(
            "SOURCE_RESOLUTION_HIGH",
            "Video must be no larger than 1080p.",
            status_code=422,
        )


def prepare_source(payload: bytes, mime_type: str) -> PreparedSource:
    suffix = ALLOWED_VIDEO_TYPES.get(mime_type)
    if suffix is None:
        raise PublicError(
            "SOURCE_MIME_INVALID",
            "Only MP4 and WebM videos are accepted.",
            status_code=422,
        )
    if len(payload) > MAX_SOURCE_BYTES:
        raise PublicError(
            "SOURCE_TOO_LARGE", "Video must be no larger than 30 MB.", status_code=422
        )
    with TemporaryDirectory(prefix="framefoley-source-") as temporary:
        root = Path(temporary)
        source = root / f"source{suffix}"
        preview = root / "preview.mp4"
        thumbnail_png = root / "thumbnail.png"
        source.write_bytes(payload)
        inspection = inspect_video(source)
        validate_video(inspection, len(payload))
        normalized = _run(
            [
                _required_tool("ffmpeg"),
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-vf",
                "scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(preview),
            ],
            timeout=90,
        )
        if normalized.returncode != 0:
            raise PublicError(
                "SOURCE_NORMALIZE_FAILED",
                "Video normalization failed.",
                status_code=422,
            )
        captured = _run(
            [
                _required_tool("ffmpeg"),
                "-y",
                "-v",
                "error",
                "-ss",
                "1.0",
                "-i",
                str(preview),
                "-frames:v",
                "1",
                "-vf",
                "scale=960:-2",
                "-c:v",
                "png",
                str(thumbnail_png),
            ],
            timeout=45,
        )
        if captured.returncode != 0:
            raise PublicError(
                "SOURCE_THUMBNAIL_FAILED",
                "Video thumbnail creation failed.",
                status_code=422,
            )
        thumbnail_buffer = io.BytesIO()
        with Image.open(thumbnail_png) as image:
            image.save(thumbnail_buffer, format="WEBP", quality=86, method=6)
        return PreparedSource(
            inspection=inspection,
            original=payload,
            preview=preview.read_bytes(),
            thumbnail=thumbnail_buffer.getvalue(),
            sha256=hashlib.sha256(payload).hexdigest(),
        )


def convert_wav_to_ogg(source: Path, destination: Path) -> None:
    common = [
        _required_tool("ffmpeg"),
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-ar",
        "48000",
    ]
    completed = _run(
        [
            *common,
            "-ac",
            "1",
            "-c:a",
            "libvorbis",
            "-q:a",
            "5",
            str(destination),
        ],
        timeout=45,
    )
    if completed.returncode != 0:
        completed = _run(
            [
                *common,
                "-ac",
                "2",
                "-c:a",
                "vorbis",
                "-strict",
                "experimental",
                "-q:a",
                "5",
                str(destination),
            ],
            timeout=45,
        )
    if completed.returncode != 0:
        raise PublicError(
            "AUDIO_CONVERT_FAILED",
            "Approved OGG conversion failed.",
            status_code=500,
        )
