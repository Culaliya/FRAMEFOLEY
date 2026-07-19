"""Deterministic original audio fixture used by the zero-cost spike."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48_000
DURATION_SECONDS = 0.6
LEADING_SILENCE_SECONDS = 0.12
TRAILING_SILENCE_SECONDS = 0.12


def generate_fixture(path: Path) -> Path:
    """Write a 48 kHz mono decaying sine + filtered-noise WAV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    total = int(SAMPLE_RATE * DURATION_SECONDS)
    signal_start = int(SAMPLE_RATE * LEADING_SILENCE_SECONDS)
    signal_end = total - int(SAMPLE_RATE * TRAILING_SILENCE_SECONDS)
    random_source = random.Random(4_860_600)
    filtered_noise = 0.0
    frames = bytearray()

    for index in range(total):
        sample = 0.0
        if signal_start <= index < signal_end:
            local_time = (index - signal_start) / SAMPLE_RATE
            normalized = (index - signal_start) / max(1, signal_end - signal_start)
            envelope = math.exp(-4.2 * normalized)
            white = random_source.uniform(-1.0, 1.0)
            filtered_noise = 0.86 * filtered_noise + 0.14 * white
            sine = math.sin(2.0 * math.pi * 178.0 * local_time)
            sample = envelope * (0.54 * sine + 0.19 * filtered_noise)
        pcm = max(-32768, min(32767, round(sample * 32767.0)))
        frames.extend(struct.pack("<h", pcm))

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(bytes(frames))
    return path
