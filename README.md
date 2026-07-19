# FRAMEFOLEY

**Your game already moves. Let it hit.**

FRAMEFOLEY turns an 8–15 second silent gameplay clip into a small,
provenance-backed sound kit. A creator marks one to three moments, generates two
sound-effect candidates per moment, chooses by ear, renders the approved mix,
and exports WAV, OGG, preview, QC, manifest, and provenance files.

This repository contains the bounded Phase 1 competition product authorized
after the Phase 0 **GO** in `docs/SPIKE_REPORT.md`. It is intentionally not a
chat app, DAW, account system, TTS tool, music generator, or multi-provider
platform.

## What is implemented

- Responsive Next.js App Router UI for source, cue, generation, audition, mix,
  export, and provenance.
- Original deterministic 12-second **JELLY RELAY** silent demo.
- Validated MP4/WebM upload, source normalization, thumbnail, and SHA-256.
- One to three accessible markers and four bounded style presets.
- Exactly two candidates per event through the Phase 0 Genblaze path.
- Deterministic ffprobe/FFmpeg QC, repair, waveform, WAV, and OGG derivatives.
- Web Audio A/B solo and in-context audition with explicit human approval.
- Authoritative server-side preview mix and deterministic ZIP export.
- HMAC project tokens and recoverable object-backed state; B2 is production's
  system of record.
- Shared JSON Schema v1 contracts and generated TypeScript types.
- Unit, integration, browser, recovery, security, and production-build checks.

## Architecture

```text
Browser (Next.js + Web Audio)
       | project-scoped HMAC token / SSE
       v
FastAPI state machine + deterministic media pipeline
       |                         |
       | live only               | fixed FFmpeg arrays
       v                         v
Genblaze -> ElevenLabs SFX      QC / repair / render / export
       |
       v
Private Backblaze B2 project prefix (durable production record)
```

No database is used. `project.json` plus immutable/source/derivative objects
under one private project prefix recover state after an API restart. Local
storage is a clearly labeled development and test adapter only.

See `docs/ARCHITECTURE.md` and `docs/B2_STORAGE_AND_RECOVERY.md`.

## Requirements

- Python 3.11+ (verified locally on Python 3.12)
- Node.js 20.9+ and pnpm 11.9.0
- FFmpeg and ffprobe
- Docker with Compose, optionally
- B2 and ElevenLabs credentials only for an explicitly authorized live gate

## Clean local setup

```bash
make install
cp .env.example .env
make check
```

If `python3` on the host is older than 3.11, point the bootstrap at an installed
3.11+ interpreter without changing the project requirement:

```bash
make install PYTHON_BIN=/path/to/python3.12
```

The default is safe and local:

```text
FRAMEFOLEY_STORAGE_MODE=local
GENERATION_MODE=demo
LIVE_GENERATION_ENABLED=false
```

Run the services in two terminals:

```bash
make api
make web
```

Open `http://localhost:3000`. API docs are available at
`http://localhost:8000/docs` outside production.

Or run the demo-mode stack:

```bash
docker compose up --build
```

## Verification commands

```bash
make contracts       # generated types match JSON Schema
make format-check
make lint
make type
make test            # Python + web unit/integration
make build           # Python compile + Next production build
make browser-test    # desktop/tablet/phone Playwright flow
make secret-scan
make check
```

## Live generation gate

Live calls require all B2/ElevenLabs environment values, B2 storage mode, the
server kill switch, and a separate command-level opt-in. The smoke command uses
one event and therefore two initial candidates; a deterministic QC retry can add
at most one call per candidate.

```bash
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make live-smoke
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make full-demo-generation
```

The second command uses all three demo events and therefore six initial calls.
Neither command is run by `make check`. Both record sanitized call count, cost
when the connector reports it, B2 object hashes, and manifest verification.

Exact live path:

```text
genblaze-core==0.3.4
genblaze-s3==0.3.4
genblaze-elevenlabs==0.3.1
ElevenLabsSFXProvider / eleven_text_to_sound_v2
```

## Evidence labels

- **LIVE** — real provider output reached B2 and its canonical manifest passed
  `Manifest.verify()`.
- **CACHED DEMO** — original bundled demo asset; never represented as live.
- **MOCKED** — local/fake test behavior; never production evidence.
- **OWNER-VERIFIED** — a setting or external account fact checked by the owner.
- **UNVERIFIED** — not yet proven from source or captured evidence.

The sanitized delivery pack is under `evidence/final/`. Phase 0 evidence remains
under `artifacts/phase0/` and is not relabeled as Phase 1 proof.

## Security and privacy

- Provider and B2 credentials remain API-side.
- Tokens are project-scoped, signed, expiring, and never logged in full.
- Object reads use short-lived signed app tokens without secret query strings in
  provenance.
- Prompts, MIME, paths, timestamps, event counts, gains, and schema versions are
  bounded and validated.
- FFmpeg is always invoked with argument arrays; user text never enters filters
  or paths.
- Anonymous project expiry defaults to 72 hours. The matching B2 lifecycle rule
  remains an owner-controlled deployment step.

See `docs/SECURITY_AND_COST.md` and `docs/OWNER_CHECKLIST.md` before publishing.

## Current publication status

Local implementation and reproducible evidence are distinct from external
publication. A public app URL, public/judge-accessible repository URL, provider
spend cap, B2 lifecycle rule, and judge access remain **UNVERIFIED** until the
owner performs or authorizes those external actions. No document in this repo
claims otherwise.
