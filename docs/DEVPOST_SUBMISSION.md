# Devpost submission copy

The English sections below are paste-ready after the owner replaces only the
explicit URL/status placeholders and confirms the final LIVE evidence. They do
not claim a second provider, active external spend cap, or rights warranty.

## Project name

FRAMEFOLEY

## Tagline

Your game already moves. Let it hit.

## Inspiration

Small games often look alive long before they sound alive. A jump lands, an
enemy pops, or a crystal confirms a route, but the creator is still scrubbing
through generic sound libraries and losing the connection between the frame and
the final file. We wanted to make Foley selection feel like part of editing the
game itself—and make AI-generated audio inspectable instead of mysterious.

## What it does

FRAMEFOLEY turns an 8–15 second silent gameplay clip into a compact,
provenance-backed sound kit. The creator uploads a clip or opens our original
JELLY RELAY demo, marks up to three exact moments, chooses a sonic style, and
generates two sound-effect candidates for each moment. They can audition A/B
alone or directly in the video, approve by ear, trim gain, render the final
preview, and export WAV, OGG, waveforms, QC reports, manifests, hashes, and a
human-readable provenance record.

The product deliberately stays narrow: no chat box, no automatic scene
understanding, no music or speech generation, and no pretend “AI knows best”
button. Deterministic code performs technical checks; the developer makes the
creative decision.

## How we built it

The responsive editor is built with Next.js, TypeScript, Tailwind CSS, and the
Web Audio API. A FastAPI service owns a strict project state machine, validates
source video with ffprobe, strips source audio, builds bounded prompts, and
coordinates live SFX generation through Genblaze.

Genblaze orchestrates the verified ElevenLabs Sound Effects provider path. Its
`ObjectStorageSink` writes generated assets and canonical manifests to a private
Backblaze B2 project prefix. FRAMEFOLEY then downloads the B2 asset, re-hashes
it, calls `Manifest.verify()`, and performs deterministic audio inspection and
repair with fixed FFmpeg argument arrays. B2 also stores the source, metadata,
event state, QC records, repaired derivatives, waveforms, mixed preview,
provenance, and deterministic ZIP export.

Shared JSON Schema v1 contracts generate the frontend types. Anonymous project
tokens are expiring, HMAC-signed, and restricted to one project prefix. Project
state recovers from B2 without a database.

## Challenges we ran into

The hardest part was preserving truth across several boundaries. A provider
response is not yet a durable asset; an uploaded object is not yet hash-verified;
a technically valid sound is not necessarily right for the frame; and a
repaired derivative must not mutate or impersonate a canonical generation
record. We designed each boundary as a separate, testable state rather than
optimistically moving the UI forward.

Audio quality was another practical challenge. Short effects can be decodable
but too quiet, padded with silence, stereo when the kit expects mono, or near
clipping. Our QC measures fixed thresholds, records before/after reports, and
allows one bounded regeneration only when deterministic repair cannot solve the
problem.

## Accomplishments that we're proud of

- A complete clip-to-sound-kit workflow that still fits on one clear product
  spine.
- Honest visual labels for LIVE, CACHED DEMO, repair, B2 storage, and manifest
  verification.
- A/B audition at the exact gameplay timestamp with human approval as a real
  gate.
- Durable, restart-recoverable B2 state without adding an unnecessary database.
- Deterministic preview and ZIP outputs with SHA-256 identities.
- Original code-generated JELLY RELAY footage and procedural demo sounds, with
  no borrowed game footage or stock media.
- Automated unit, integration, failure-recovery, desktop, tablet, phone,
  accessibility, build, and secret-scan evidence.

## What we learned

Provenance becomes useful when it is visible during the creative workflow, not
buried as a compliance file at the end. We also learned to separate four facts
that AI demos often blend together: who generated an asset, where it is durably
stored, whether it passes technical QC, and whether a human actually likes it.
Genblaze and B2 gave us a clean way to make those distinctions concrete.

## What's next for FRAMEFOLEY

The competition build is intentionally complete and small. After judging, we
would validate one focused extension at a time: reusable personal style cards,
timeline export adapters for common engines, and better comparison shortcuts.
We would not expand to music, dialogue, or automatic scene understanding until
the core frame-to-Foley decision remains as fast and inspectable as it is now.

## Providers and models

- Orchestration: `genblaze-core==0.3.4`
- Object storage adapter: `genblaze-s3==0.3.4`
- Provider adapter: `genblaze-elevenlabs==0.3.1`
- Provider: ElevenLabs Sound Effects
- Model: `eleven_text_to_sound_v2`
- Secondary provider: none

## Exact Genblaze use

Every LIVE candidate is a Genblaze `Pipeline` step. FRAMEFOLEY uses the official
ElevenLabs SFX adapter and passes a deterministic prompt, model, audio modality,
and bounded duration. The pipeline persists through `ObjectStorageSink` with
zero hidden retries. The app requires the canonical manifest to verify, retains
run and lineage IDs, and never forges or edits canonical Genblaze records.

## Exact Backblaze B2 use

B2 is the private production system of record, not a backup screenshot. Each
anonymous project has an isolated prefix containing project state, original and
normalized clip, thumbnail, source metadata, event records, every generated
asset and Genblaze manifest, QC before/after, repaired WAV/OGG, waveform,
approved copies, render and mix map, provenance JSON/HTML, and the final ZIP.
The API can recover a project after process restart by loading its schema-v1
project record from B2.

## Built with

Next.js, React, TypeScript, Tailwind CSS, Web Audio API, FastAPI, Pydantic,
Genblaze, ElevenLabs Sound Effects, Backblaze B2, FFmpeg/ffprobe, JSON Schema,
pytest, Vitest, Playwright, and Docker.

## Verified public URLs

```text
LIVE APP: https://framefoley-culaliya.onrender.com
SOURCE REPOSITORY: https://github.com/Culaliya/FRAMEFOLEY
DEMO VIDEO: https://raw.githubusercontent.com/Culaliya/FRAMEFOLEY/main/evidence/final/video/framefoley-demo.mp4
```

Deployed source commit:
`4a4d994eeaa07507d4da8189b92ac2f14c4ba586`.

The Render Free deployment may cold-start after inactivity. The public build
uses the clearly labeled cached demo with B2 persistence; the separate LIVE
evidence records the bounded ElevenLabs/Genblaze verification run.
