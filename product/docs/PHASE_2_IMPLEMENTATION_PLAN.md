# FRAMEFOLEY Phase 2 implementation plan

Starting source commit:
`e5ed7653c1c9076d99e0460677bb042fa45140b0`

Authorization: **Phase 2 is explicitly authorized. Phase 3 is not authorized.**

## Scope contract

| Item | Decision |
| --- | --- |
| User goal | Make the existing public competition build judge-readable, replay its verified LIVE evidence without a provider call, remove the impossible public upload promise, and lock submission proof. |
| Existing system to preserve | Next.js App Router, FastAPI state machine, shared schema v1, Genblaze-only LIVE path, ElevenLabs SFX, private Backblaze B2, fixed-array FFmpeg, HMAC project tokens, no database. |
| Allowed change area | Capability/readiness contracts; landing comparison; immutable LIVE proof publication and replay; public copy labels; bounded network recovery; owner/public verification scripts; Phase 2 evidence, screenshots, and video. |
| Explicit non-goals | Accounts, billing, database, chat, music/TTS, automatic cue detection, second provider, public LIVE spend, engine plugins, native apps, analytics, visual rebrand, Phase 3. |
| Files likely touched | `services/api/framefoley_api/`, `packages/contracts/`, `apps/web/`, `scripts/`, `Makefile`, `README.md`, `docs/`, `product/docs/`, `evidence/phase2/`. |
| Verification required | Locked install, formatting, lint, mypy/TypeScript, unit/integration tests, production builds, Phase 2 proof tests, desktop/tablet/phone Playwright, public probes, media inspection, checksums, and secret scan. |

## Implementation sequence

1. Add a strict server-owned `/v1/capabilities` response and make both landing
   and source selection capability-driven. Public demo mode must not advertise
   an upload path that cannot complete; self-hosted LIVE mode retains it.
2. Reuse JELLY RELAY media in an accessible landing comparison that starts
   silent, keeps one video timeline, requires a user gesture for sound, stops
   on silence/unmount/hidden tab, and exposes three cue ticks.
3. Add a fail-closed LIVE proof module, immutable `proof/live/v1/` contract,
   explicit no-provider-call publication command, B2 validation, replay project
   creation, and the existing audition/render/export/provenance spine.
4. Add the reusable readiness gate and one-reconnect SSE client with
   authoritative project polling fallback and existing idempotency protection.
5. Collapse public truth language to `CACHED DEMO`, `LIVE EVIDENCE REPLAY`, and
   `LIVE`; update the UI, docs, Devpost copy, transcript, and consistency tests.
6. Add owner verification and sanitized public/evidence builders. Classify true
   submission blockers separately from prudent zero-spend controls.
7. Run every local gate, publish the proof with B2-only credentials and explicit
   owner opt-in, deploy the exact commit, exercise public desktop/tablet/phone
   flows, capture fresh evidence, and produce the 2:45–2:58 master.

## LIVE truth boundary

The source Phase 1 evidence identifies two final-version LIVE candidates and
their B2 objects. The repository deliberately contains no B2 credentials and
does not persist the raw private objects. Implementation and tamper tests use a
local proof fixture; production publication will re-download the recorded B2
bytes, run `Manifest.verify()` on both canonical manifests, re-hash every audio
object, and write the immutable proof prefix. The publication command accepts
no ElevenLabs key and makes zero provider calls.

## Completion boundary

Phase 2 is complete only when the required local and public evidence exists,
the deployed commit is recorded, owner-only facts remain honestly classified,
and no Phase 3 implementation or planning has begun.
