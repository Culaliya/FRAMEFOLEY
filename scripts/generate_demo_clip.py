"""Generate FRAMEFOLEY's deterministic original JELLY RELAY demo assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

WIDTH = 1280
HEIGHT = 720
FPS = 30
DURATION_SECONDS = 12
SAMPLE_RATE = 48_000

EVENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "evt_landing01",
        "slug": "glass-landing",
        "title": "Jelly lands on glass",
        "type": "impact",
        "timestampSeconds": 1.6,
        "targetDurationSeconds": 0.72,
        "intensity": "medium",
        "materialNote": "Soft gelatin weight on a thin glass platform.",
    },
    {
        "id": "evt_bubble02",
        "slug": "bubble-pop",
        "title": "Bubble enemy pops",
        "type": "creature",
        "timestampSeconds": 5.2,
        "targetDurationSeconds": 0.72,
        "intensity": "medium",
        "materialNote": "Elastic bubble skin collapsing into tiny glitter.",
    },
    {
        "id": "evt_crystal03",
        "slug": "route-confirm",
        "title": "Route crystal confirms",
        "type": "ui",
        "timestampSeconds": 8.85,
        "targetDurationSeconds": 0.36,
        "intensity": "soft",
        "materialNote": "Small luminous crystal with a readable confirmation tick.",
    },
)

STARS = tuple(
    (random.Random(8_501 + index).randrange(WIDTH), random.Random(9_701 + index).randrange(420))
    for index in range(96)
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ease(value: float) -> float:
    bounded = min(1.0, max(0.0, value))
    return bounded * bounded * (3.0 - 2.0 * bounded)


def _jelly_position(time_seconds: float) -> tuple[float, float, float]:
    segments = (
        (0.0, 1.6, (100.0, 420.0), (360.0, 420.0), 118.0),
        (1.6, 5.2, (360.0, 420.0), (720.0, 360.0), 94.0),
        (5.2, 8.85, (720.0, 360.0), (1030.0, 320.0), 82.0),
        (8.85, 12.0, (1030.0, 320.0), (1160.0, 320.0), 34.0),
    )
    for start, end, origin, target, arc in segments:
        if time_seconds <= end:
            progress = _ease((time_seconds - start) / (end - start))
            x = origin[0] + (target[0] - origin[0]) * progress
            baseline = origin[1] + (target[1] - origin[1]) * progress
            y = baseline - math.sin(progress * math.pi) * arc
            landing = min(abs(time_seconds - end), 0.16) / 0.16
            squash = 1.0 - (1.0 - landing) * 0.22
            return x, y, squash
    return 1160.0, 320.0, 1.0


def _draw_background(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#090B0C")
    draw.rectangle((0, 460, WIDTH, HEIGHT), fill="#101617")
    for index, (x, y) in enumerate(STARS):
        pulse = 0.5 + 0.5 * math.sin(time_seconds * 1.4 + index * 0.7)
        color = "#59E5E2" if index % 7 == 0 else "#6E7778"
        radius = 1 + int(pulse > 0.82)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    for y in range(470, HEIGHT, 34):
        draw.line((0, y, WIDTH, y), fill="#1C2728", width=1)
    for x in range(-180, WIDTH + 180, 150):
        draw.line((WIDTH // 2, 450, x, HEIGHT), fill="#172021", width=1)


def _draw_platforms(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    platforms = (
        (20, 485, 260, 522, "#263334"),
        (292, 482, 448, 500, "#59E5E2"),
        (560, 425, 780, 461, "#263334"),
        (900, 380, 1135, 416, "#263334"),
    )
    for left, top, right, bottom, color in platforms:
        draw.rectangle((left, top, right, bottom), fill=color)
        draw.line((left + 8, top + 5, right - 8, top + 5), fill="#ECE7DB", width=2)
        draw.line((left + 10, bottom + 5, right - 14, bottom + 5), fill="#101617", width=7)
    impact = max(0.0, 1.0 - abs(time_seconds - 1.6) / 0.24)
    if impact > 0:
        for offset in (16, 34, 54):
            width = 2 if offset < 50 else 1
            draw.arc(
                (370 - offset, 466 - offset / 4, 370 + offset, 490 + offset / 4),
                190,
                350,
                fill="#D8FF57",
                width=width,
            )


def _draw_bubble(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    delta = time_seconds - 5.2
    if delta < 0:
        pulse = 1.0 + 0.08 * math.sin(time_seconds * 4.0)
        radius = 48 * pulse
        draw.ellipse((685 - radius, 312 - radius, 685 + radius, 312 + radius), fill="#FF5B4A")
        draw.ellipse((697 - radius * 0.32, 294 - radius * 0.42, 697, 294), fill="#ECE7DB")
        draw.ellipse((670, 306, 676, 312), fill="#090B0C")
        draw.ellipse((692, 306, 698, 312), fill="#090B0C")
    elif delta < 0.8:
        spread = 26 + delta * 120
        for index in range(14):
            angle = index * math.tau / 14 + 0.18
            x = 685 + math.cos(angle) * spread
            y = 312 + math.sin(angle) * spread * 0.72
            size = max(1, int(6 - delta * 5))
            color = "#FF5B4A" if index % 2 == 0 else "#D8FF57"
            draw.polygon(
                ((x, y - size), (x + size, y), (x, y + size), (x - size, y)),
                fill=color,
            )


def _draw_crystal(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    active = time_seconds >= 8.85
    pulse = 0.5 + 0.5 * math.sin(max(0.0, time_seconds - 8.85) * 7.0)
    center_x, center_y = 1040, 270
    glow = int(18 + (34 * pulse if active else 0))
    if active:
        draw.ellipse(
            (center_x - glow, center_y - glow, center_x + glow, center_y + glow),
            outline="#D8FF57",
            width=4,
        )
        draw.line((790, center_y, center_x - 34, center_y), fill="#D8FF57", width=5)
    draw.polygon(
        (
            (center_x, center_y - 44),
            (center_x + 31, center_y),
            (center_x, center_y + 48),
            (center_x - 31, center_y),
        ),
        fill="#59E5E2" if not active else "#D8FF57",
    )
    draw.line((center_x, center_y - 34, center_x, center_y + 34), fill="#ECE7DB", width=3)


def _draw_jelly(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    x, y, squash = _jelly_position(time_seconds)
    body_width = 92 / squash
    body_height = 82 * squash
    draw.ellipse((x - 48, y + 48, x + 48, y + 64), fill="#050707")
    draw.rounded_rectangle(
        (x - body_width / 2, y - body_height / 2, x + body_width / 2, y + body_height / 2),
        radius=28,
        fill="#A6F5C7",
        outline="#D8FF57",
        width=4,
    )
    draw.ellipse((x - 23, y - 9, x - 15, y - 1), fill="#090B0C")
    draw.ellipse((x + 15, y - 9, x + 23, y - 1), fill="#090B0C")
    draw.arc((x - 17, y - 3, x + 17, y + 23), 12, 168, fill="#090B0C", width=3)
    draw.rounded_rectangle((x - 50, y + 27, x - 8, y + 45), radius=8, fill="#59E5E2")


def render_frame(frame_index: int) -> Image.Image:
    time_seconds = frame_index / FPS
    image = Image.new("RGB", (WIDTH, HEIGHT), "#090B0C")
    draw = ImageDraw.Draw(image)
    _draw_background(draw, time_seconds)
    _draw_platforms(draw, time_seconds)
    _draw_bubble(draw, time_seconds)
    _draw_crystal(draw, time_seconds)
    _draw_jelly(draw, time_seconds)
    scanline_y = int((time_seconds * 86) % HEIGHT)
    draw.line((0, scanline_y, WIDTH, scanline_y), fill="#1C2D2D", width=2)
    return image


def generate_video(output: Path, thumbnail: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    assert process.stderr is not None
    for frame_index in range(FPS * DURATION_SECONDS):
        frame = render_frame(frame_index)
        process.stdin.write(frame.tobytes())
        if frame_index == FPS * 6:
            frame.save(thumbnail, "WEBP", quality=92, method=6)
    process.stdin.close()
    error = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait(timeout=120)
    if return_code != 0:
        raise RuntimeError(f"ffmpeg demo encoding failed: {error[:400]}")


def _sound_sample(
    kind: str, variant: str, local_time: float, random_source: random.Random
) -> float:
    character = variant == "character"
    decay = math.exp(-local_time * (4.4 if character else 6.4))
    noise = random_source.uniform(-1.0, 1.0)
    if kind == "glass-landing":
        low = math.sin(math.tau * (142 if character else 176) * local_time)
        tick = math.sin(math.tau * 1_480 * local_time) * math.exp(-local_time * 18)
        return decay * (0.56 * low + 0.12 * noise) + 0.18 * tick
    if kind == "bubble-pop":
        chirp_frequency = (780 if character else 980) - local_time * 420
        chirp = math.sin(math.tau * chirp_frequency * local_time)
        return decay * (0.33 * chirp + 0.34 * noise)
    tones = (920.0, 1_240.0, 1_660.0) if character else (1_120.0, 1_680.0)
    tone = sum(math.sin(math.tau * frequency * local_time) for frequency in tones) / len(tones)
    return decay * (0.48 * tone + 0.08 * noise)


def generate_demo_audio(output: Path, kind: str, variant: str, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    leading = 0.14 if kind == "glass-landing" and variant == "clean" else 0.018
    total = int(duration * SAMPLE_RATE)
    random_source = random.Random(f"framefoley:{kind}:{variant}")
    frames = bytearray()
    for index in range(total):
        time_seconds = index / SAMPLE_RATE
        sample = 0.0
        if time_seconds >= leading:
            sample = _sound_sample(kind, variant, time_seconds - leading, random_source)
        pcm = max(-32768, min(32767, round(sample * 19_800)))
        frames.extend(struct.pack("<h", pcm))
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(frames))


def generate_all(output_dir: Path) -> dict[str, Any]:
    video = output_dir / "jelly-relay.mp4"
    thumbnail = output_dir / "jelly-relay-thumbnail.webp"
    events_path = output_dir / "jelly-relay-events.json"
    generate_video(video, thumbnail)
    events_path.write_text(json.dumps(EVENTS, indent=2) + "\n", encoding="utf-8")
    audio_assets: list[dict[str, Any]] = []
    durations = {
        "glass-landing": (0.72, 0.94),
        "bubble-pop": (0.62, 0.88),
        "route-confirm": (0.28, 0.42),
    }
    for event in EVENTS:
        for index, variant in enumerate(("clean", "character")):
            path = output_dir / "cache" / "raw" / f"{event['slug']}-{variant}.wav"
            generate_demo_audio(
                path,
                str(event["slug"]),
                variant,
                durations[str(event["slug"])][index],
            )
            audio_assets.append(
                {
                    "eventId": event["id"],
                    "eventSlug": event["slug"],
                    "variant": variant,
                    "path": path.relative_to(output_dir).as_posix(),
                    "sha256": _sha256(path),
                    "sourceLabel": "CACHED DEMO",
                }
            )
    provenance = {
        "schemaVersion": 1,
        "title": "JELLY RELAY",
        "generator": "scripts/generate_demo_clip.py",
        "deterministic": True,
        "thirdPartyAssets": [],
        "video": {
            "path": video.name,
            "sha256": _sha256(video),
            "durationSeconds": DURATION_SECONDS,
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "audioStreams": 0,
        },
        "thumbnail": {"path": thumbnail.name, "sha256": _sha256(thumbnail)},
        "audio": audio_assets,
    }
    (output_dir / "jelly-relay-assets.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="demo")
    args = parser.parse_args()
    provenance = generate_all(Path(args.output_dir))
    print(json.dumps({"status": "PASS", "video": provenance["video"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
