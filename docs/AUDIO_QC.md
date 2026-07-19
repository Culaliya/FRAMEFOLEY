# Deterministic audio QC

Provider output never chooses its own technical verdict. FRAMEFOLEY decodes and
measures audio through ffprobe/FFmpeg, then classifies fixed thresholds in
Python. No LLM participates.

## Metrics

- decode success;
- duration;
- source sample rate and channels;
- mono-decoded peak and RMS dBFS at 48 kHz;
- leading/trailing silence using a -50 dBFS gate;
- SHA-256 of the inspected bytes.

## Duration windows

| Event type | Allowed technical window |
| --- | ---: |
| UI | 0.08–0.80 s |
| Impact | 0.15–1.50 s |
| Creature | 0.25–2.50 s |
| Ambience | 3.00–8.00 s |

## Classification thresholds

- `REGENERATE`: duration outside its event window or RMS below -50 dBFS.
- `FAILED`: ffprobe/FFmpeg missing, invalid metadata, or decode failure.
- `REPAIRABLE`: leading silence >100 ms, trailing silence >250 ms, peak at or
  above -0.5 dBFS, RMS below -30 dBFS, sample rate not 48 kHz, or not mono.
- `PASS`: none of the above.

## Repair

The fixed-array repair pipeline:

1. trims lead/trail at the -50 dBFS gate while retaining a tiny edge;
2. applies bounded gain only when near clipping or low gain requires it;
3. limits at -1 dBFS ceiling;
4. downmixes to mono;
5. resamples to 48 kHz;
6. writes PCM signed 16-bit WAV;
7. re-inspects and requires `PASS`;
8. derives OGG and a deterministic waveform image.

The UI describes this honestly: technical trim/gain/format changed; generated
content was not replaced. A derivative record links original run/hash to
approved derivative/hash. Canonical Genblaze manifests are never modified.

## Retry

Only `FAILED`/`REGENERATE` candidates can consume one generation retry, and only
while the per-project retry budget remains. Repair failure does not create an
unbounded loop. Provider and pipeline retries are both configured to zero
beyond the explicit application retry.

## Render

Approved WAVs are gain-bounded from -12 to +6 dB, delayed to exact event
timestamps, mixed without normalization, padded/trimmed to source duration,
limited, and encoded H.264/AAC. User text never enters FFmpeg paths or filters.
