# FRAMEFOLEY

**Your game already moves. Let it hit.**

FRAMEFOLEY turns an 8–15 second silent gameplay clip into a small,
provenance-backed sound kit. A creator marks one to three moments, generates two
sound-effect candidates per moment, chooses by ear, renders the approved mix,
and exports WAV, OGG, preview, QC, manifest, and provenance files.

This repository contains the bounded competition build. It is intentionally
not a chat app, DAW, account system, TTS tool, music generator, or
multi-provider platform.

## What is implemented

- Responsive Next.js App Router UI for source, cue, generation, audition, mix,
  export, and provenance.
- Original deterministic 12-second **JELLY RELAY** silent demo.
- Instant silent-versus-approved-Foley landing comparison.
- Server-owned deployment capabilities; the public zero-spend build never
  advertises a custom-upload path it cannot complete.
- Validated MP4/WebM upload, source normalization, thumbnail, and SHA-256 in a
  self-hosted LIVE build.
- One to three accessible markers and four bounded style presets.
- Exactly two candidates per event through the Phase 0 Genblaze path.
- Deterministic ffprobe/FFmpeg QC, repair, waveform, WAV, and OGG derivatives.
- Web Audio A/B solo and in-context audition with explicit human approval.
- Authoritative server-side preview mix and deterministic ZIP export.
- HMAC project tokens and recoverable object-backed state; B2 is production's
  system of record.
- Immutable **LIVE EVIDENCE REPLAY**: two authorized Genblaze/ElevenLabs
  outputs are re-downloaded, re-hashed, canonical-manifest verified, and opened
  for A/B approval with zero new provider calls.
- Bounded Render cold-start readiness and SSE-to-authoritative-state recovery.
- Shared JSON Schema v1 contracts and generated TypeScript types.
- Unit, integration, browser, recovery, security, and production-build checks.

## Architecture

```text
Browser (Next.js + Web Audio)
       | project-scoped HMAC token / SSE
       v
FastAPI state machine + deterministic media pipeline
       |                         |                         |
       | self-hosted LIVE        | fixed FFmpeg arrays     | zero-call replay
       v                         v                         v
Genblaze -> ElevenLabs SFX      QC / repair / render      immutable B2 proof
       \__________________________|_________________________/
                                  v
              Private Backblaze B2 (durable system of record)
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
make phase2-proof-test
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

The anonymous public deployment does not expose this gate. Its capability
contract reports `customUploadCanComplete=false` and
`anonymousProviderSpendEnabled=false`.

Exact live path:

```text
genblaze-core==0.3.4
genblaze-s3==0.3.4
genblaze-elevenlabs==0.3.1
ElevenLabsSFXProvider / eleven_text_to_sound_v2
```

## Immutable LIVE proof replay

The versioned private proof bundle is published only from the already
authorized, final-version LIVE artifacts. Publication requires a separate B2
opt-in and imports no ElevenLabs credential:

```bash
./scripts/run_phase2_proof_publish_securely.sh
# equivalent fail-closed command:
FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1 make publish-live-proof
```

The command re-downloads and hashes every source object, requires both canonical
manifests to return true from `Manifest.verify()`, and then writes
`framefoley/proof/live/v1/`. Opening `POST /v1/projects/live-proof` verifies the
private bundle again, creates an isolated expiring project, and makes zero
provider calls.

## Evidence labels

- **LIVE** — real provider output reached B2 and its canonical manifest passed
  `Manifest.verify()`.
- **LIVE EVIDENCE REPLAY** — verified recorded LIVE outputs copied into a new
  private replay project; opening it makes zero provider calls.
- **CACHED DEMO** — original bundled demo asset; never represented as live.
- **MOCKED** — local/fake test behavior; never production evidence.
- **OWNER-VERIFIED** — a setting or external account fact checked by the owner.
- **UNVERIFIED** — not yet proven from source or captured evidence.

The current submission pack is under `evidence/phase2/`. The earlier delivery
pack remains under `evidence/final/`, and Phase 0 evidence remains under
`artifacts/phase0/`; historical evidence is never relabeled.

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

The public competition surfaces are:

- **Live app:** <https://framefoley-culaliya.onrender.com>
- **API readiness:** <https://framefoley-api-culaliya.onrender.com/readyz>
- **Public source:** <https://github.com/Culaliya/FRAMEFOLEY>
- **Final video:** owner-verified public YouTube/Vimeo URL pending
- **Deployed source commit:** recorded after the final public verification

The public three-cue workflow uses explicitly labeled **CACHED DEMO**
candidates, persists complete projects to private Backblaze B2, and keeps live
ElevenLabs generation disabled so anonymous traffic cannot spend provider
credit. **LIVE EVIDENCE REPLAY** contains real recorded Genblaze/ElevenLabs
outputs stored and re-verified from B2; opening it makes no new provider call.
Custom upload is available in a self-hosted LIVE build, not falsely promised by
the public zero-spend deployment.

Submission blockers and prudent non-blocking controls are separated in
`product/docs/OWNER_VERIFICATION_PHASE_2.md`. Never infer an account-console
setting from source code.
