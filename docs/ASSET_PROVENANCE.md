# Asset provenance

## Original FRAMEFOLEY assets

| Asset | Origin | Reproduction |
| --- | --- | --- |
| `demo/jelly-relay.mp4` | Original geometric animation generated locally from code | `python scripts/generate_demo_clip.py` |
| `demo/jelly-relay-thumbnail.webp` | Deterministic frame from the same generator | Same command |
| `demo/jelly-relay-events.json` | Original event metadata specified for FRAMEFOLEY | Same command |
| `demo/cache/raw/*.wav` | Original procedural synthesis (oscillators/noise/envelopes), not provider output | Same command |
| `apps/web/public/framefoley-mark.svg` | Original simple vector mark made for this product | Stored as source SVG |
| UI visual system | Original CSS shapes, film rails, timeline, waveform framing, and palette | `apps/web/app/globals.css` |

JELLY RELAY contains no third-party footage, recognizable character, stock
photo, music, embedded audio, or downloaded game asset. The MP4 is silent.
Generated-asset checksums and generator parameters are recorded in
`demo/jelly-relay-assets.json`.

## Fonts and icons

The UI downloads no font file. It uses platform/system font stacks (Inter only
when already available on the viewer's system) and standard fallback families.
UI icons come from the pinned `lucide-react` package under its upstream license;
the repository does not redistribute a separate icon asset pack.

## Live generated audio

Live candidate provenance records ElevenLabs SFX model/provider through
Genblaze, canonical manifest, B2 object key, hashes, prompt, parameters, QC, and
human approval. Deterministic derivatives preserve lineage and are not labeled
as raw provider output.

## Cached demo audio

Procedural demo WAVs are labeled `CACHED DEMO`. Their application cache record
is explicitly non-canonical and `manifestVerified=false`. They exist so the
complete product can be judged without spending credits or opening live calls.

## Rights limitation and owner check

Provenance explains origin and transformation; it is not legal clearance. The
owner must verify current ElevenLabs plan/terms for public competition use and
retain any required notices. FRAMEFOLEY should not advertise ownership or
exclusivity beyond what those current terms support.
