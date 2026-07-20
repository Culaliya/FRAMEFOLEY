# Devpost submission copy

The English sections below are paste-ready. Replace only the explicit final
video URL after the owner verifies signed-out YouTube/Vimeo playback. This copy
does not claim a second provider, automatic scene understanding, an active
external spend cap, or a rights warranty.

## Project name

FRAMEFOLEY

## Tagline

Your game already moves. Let it hit.

## Inspiration

Small games often look alive long before they sound alive. A jump lands, an
enemy pops, or a crystal confirms a route, but the creator is still scrubbing
through generic sound libraries and losing the connection between the frame and
the final file. We wanted Foley selection to feel like part of editing the game
itself—and AI-generated audio to be inspectable instead of mysterious.

## What it does

FRAMEFOLEY turns an 8–15 second silent gameplay clip into a compact,
provenance-backed sound kit. A creator marks up to three exact moments, locks one
bounded sonic style, compares two sound-effect candidates for each moment, and
approves the creative winner by ear. FRAMEFOLEY then renders the selected Foley
at the exact timestamps and exports WAV, OGG, waveforms, QC reports, manifests,
hashes, a mixed preview, and human-readable provenance.

The public three-cue JELLY RELAY workflow uses original CACHED DEMO candidates,
so anonymous traffic cannot spend provider credit. Custom clip upload is
available in a self-hosted LIVE build; it is not falsely promised by the
zero-provider-spend public deployment.

The public app also includes LIVE EVIDENCE REPLAY. It contains two real
Genblaze/ElevenLabs outputs from an authorized LIVE run, stored in private
Backblaze B2 and re-verified from B2 before each replay project opens. A judge
can hear both candidates, inspect their lineage, approve one, render, export,
and inspect provenance. Opening the replay makes zero new provider calls.

The product deliberately stays narrow: no chat box, no automatic scene
understanding or cue detection, no music or speech generation, and no “AI knows
best” button. Deterministic code performs technical checks. Human approval
remains the creative authority.

## How we built it

The responsive editor is built with Next.js, TypeScript, CSS, and the Web Audio
API. A FastAPI service owns a strict capability contract and project state
machine, validates source video with ffprobe, strips source audio, builds bounded
prompts, and coordinates the self-hosted LIVE SFX path through Genblaze.

Genblaze orchestrates the verified ElevenLabs Sound Effects provider path. Its
`ObjectStorageSink` writes generated assets and canonical manifests to a private
Backblaze B2 project prefix. FRAMEFOLEY downloads the B2 asset, re-hashes it,
calls the official `Manifest.verify()`, and performs deterministic audio
inspection and repair with fixed FFmpeg argument arrays.

B2 is the system of record for project state, source media, generated or cached
candidate media, canonical manifests, QC before and after, repaired derivatives,
waveforms, human approvals, the mixed preview, deterministic ZIP export, and
provenance. Anonymous project tokens are expiring, HMAC-signed, and restricted
to one private project prefix. Project state recovers from B2 without a
database.

The immutable LIVE proof bundle has a strict safe index and checksum inventory.
The replay API re-downloads and hashes every proof object, validates two
canonical manifests, verifies provider/model/run/asset/QC lineage, and fails
closed on any missing, modified, or relabeled record. It then clones the bytes
into an isolated expiring project without touching the provider path.

## Challenges we ran into

The hardest part was preserving truth across boundaries. A provider response is
not yet a durable asset; an uploaded object is not yet hash-verified; a
technically valid sound is not necessarily right for the frame; and a repaired
derivative must not mutate or impersonate a canonical generation record. We
designed each boundary as a separate, testable state.

We also had to make a public demo safe without making it misleading. Enabling
anonymous LIVE generation would create uncontrolled spend, while showing an
upload button in demo mode created a path that could not finish. A server-owned
capability contract now removes that dead end. CACHED DEMO proves the complete
three-cue product workflow; LIVE EVIDENCE REPLAY makes the real provider proof
audible and inspectable without a fresh call.

Short effects introduced practical QC problems: decodable audio can still be
too quiet, padded with silence, stereo when the kit expects mono, or near
clipping. Fixed thresholds record before/after reports and allow one bounded
regeneration only when deterministic repair cannot solve the problem.

## Accomplishments that we're proud of

- A complete clip-to-sound-kit workflow on one clear product spine.
- An instant silent-versus-approved-Foley moment before the editor workflow.
- Exact truth labels: CACHED DEMO, LIVE EVIDENCE REPLAY, and LIVE.
- Two real provider outputs that remain audible, private, hash-verified, and
  canonical-manifest verified without opening a new provider call.
- A/B audition at the exact gameplay timestamp with human approval as a real
  gate.
- Durable, restart-recoverable B2 state without an unnecessary database.
- Deterministic preview and ZIP outputs with SHA-256 identities.
- Original code-generated JELLY RELAY footage and procedural cached sounds,
  with no borrowed game footage, stock media, music, or dialogue.
- Automated unit, integration, tamper, recovery, cold-start, SSE, desktop,
  tablet, phone, accessibility, build, and secret-scan evidence.

## What we learned

Provenance becomes useful when it is visible during the creative workflow, not
buried as a compliance file at the end. We learned to separate generation,
durable storage, deterministic technical validity, and human creative approval.
We also learned that “safe demo” and “real proof” do not need to contradict each
other when the replay boundary is explicit and mechanically verified.

## What's next for FRAMEFOLEY

The competition build is intentionally complete and bounded. The immediate
work after submission is operational: keep the public deployment and final
video reachable during judging, preserve the immutable evidence, and gather
judge feedback on whether the silent-to-Foley decision is understandable in the
first thirty seconds. No broader product phase is implied by this submission.

## Providers and models

- Orchestration: `genblaze-core==0.3.4`
- Object storage adapter: `genblaze-s3==0.3.4`
- Provider adapter: `genblaze-elevenlabs==0.3.1`
- Provider: ElevenLabs Sound Effects
- Model: `eleven_text_to_sound_v2`
- Secondary provider: none

## Exact Genblaze use

Every LIVE candidate is one bounded Genblaze `Pipeline` step. FRAMEFOLEY uses
the official ElevenLabs SFX adapter with a deterministic prompt, model, audio
modality, and bounded duration. The pipeline persists through
`ObjectStorageSink` with zero hidden retries. The app requires the canonical
manifest to verify, retains run lineage and hashes, and never forges or edits a
canonical Genblaze record.

The two candidates in LIVE EVIDENCE REPLAY were generated during the recorded,
authorized LIVE gate. The public replay re-verifies those Genblaze manifests
and B2 bytes. It does not call Genblaze or ElevenLabs again.

## Exact Backblaze B2 use

B2 is the private production system of record, not a backup screenshot. Each
anonymous project has an isolated prefix containing project state, source and
normalized clip, thumbnail, source metadata, event records, candidate assets,
canonical manifests where applicable, QC, repaired WAV/OGG, waveform, approved
copies, render and mix map, provenance, and the final ZIP. The API recovers a
project after process restart by loading its schema-v1 record from B2.

The versioned private proof prefix separately preserves the authorized LIVE
source, two candidate assets, manifests, QC, waveforms, metadata, and a complete
checksum inventory. The browser never receives this prefix or B2 credentials.

## Built with

Next.js, React, TypeScript, Web Audio API, FastAPI, Pydantic, Genblaze,
ElevenLabs Sound Effects, Backblaze B2, FFmpeg/ffprobe, JSON Schema, pytest,
Vitest, Playwright, and Docker.

## Public URLs

```text
LIVE APP: https://framefoley-culaliya.onrender.com
SOURCE REPOSITORY: https://github.com/Culaliya/FRAMEFOLEY
FINAL VIDEO: [OWNER-VERIFIED YOUTUBE OR VIMEO URL]
```

Deployed source commit: `[FINAL DEPLOYED COMMIT FROM PHASE 2 EVIDENCE]`.

The Render Free deployment may cold-start after inactivity. FRAMEFOLEY retries
readiness for up to ninety seconds, reports factual stages, and falls back to
the public video and source when the interactive API is temporarily unavailable.
