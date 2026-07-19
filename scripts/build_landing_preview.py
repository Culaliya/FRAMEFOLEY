"""Build the small same-timeline JELLY RELAY landing comparison asset."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "apps" / "web" / "public" / "jelly-relay-approved-mix.mp4"


def main() -> int:
    source = ROOT / "demo" / "jelly-relay.mp4"
    cache = ROOT / "demo" / "cache" / "raw"
    sounds = [
        cache / "glass-landing-clean.wav",
        cache / "bubble-pop-clean.wav",
        cache / "route-confirm-clean.wav",
    ]
    required = [source, *sounds]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("landing preview inputs missing: " + ", ".join(missing))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".building.mp4")
    arguments = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
    ]
    for sound in sounds:
        arguments.extend(["-i", str(sound)])
    arguments.extend(
        [
            "-filter_complex",
            "[1:a]adelay=1600:all=1,volume=0.92[a1];"
            "[2:a]adelay=5200:all=1,volume=0.92[a2];"
            "[3:a]adelay=8850:all=1,volume=0.92[a3];"
            "[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,"
            "alimiter=limit=0.92,apad=pad_dur=12[mix]",
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            "12",
            "-movflags",
            "+faststart",
            str(temporary),
        ]
    )
    try:
        subprocess.run(arguments, check=True, timeout=45)
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Landing comparison built: {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
