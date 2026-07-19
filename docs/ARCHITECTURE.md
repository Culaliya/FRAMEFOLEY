# Architecture

## Scope boundary

FRAMEFOLEY has one flow: silent clip -> 1–3 cues -> two SFX candidates each ->
audition -> approve -> render -> export/provenance. There are no accounts,
database, teams, billing, chat, TTS, music, automatic video understanding,
analytics, or second provider.

## Components

| Component | Responsibility | Authority |
| --- | --- | --- |
| `apps/web` | Next.js UI, timeline, Web Audio audition | Human interaction only |
| `services/api` | HMAC access, state machine, generation coordination, media and export | Server-side product authority |
| `packages/contracts` | JSON Schema v1 and generated TypeScript | Wire-format source of truth |
| Genblaze | Provider orchestration, canonical run/manifest | Live generation path |
| ElevenLabs SFX | One live audio provider | Provider output only |
| Backblaze B2 | Private durable production objects | System of record |
| FFmpeg/ffprobe | Inspection, repair, waveform, render, conversion | Deterministic technical processing |

## Request and data flow

1. The API creates an anonymous project and returns an expiring HMAC token.
2. The browser selects the deterministic demo or uploads a validated source.
3. The API strips source audio, stores preview/thumbnail/metadata, and advances
   only through validated state transitions.
4. Cue edits are bounded to three events and stored as independent event JSON.
5. In `live` mode, each candidate is a Genblaze pipeline run persisted through
   `ObjectStorageSink` into the project's B2 prefix.
6. The API downloads the B2 object, re-hashes it, verifies both in-memory and
   B2-reloaded canonical manifests, then runs deterministic QC.
7. The browser auditions; only a person can approve a candidate.
8. Fixed-array FFmpeg commands produce the authoritative preview. A deterministic
   ZIP and provenance index are stored under the same project prefix.

## State machine

```text
created -> source_uploading -> source_ready -> cueing
        -> generation_queued -> generating -> audition_ready
        -> approvals_complete -> rendering -> render_ready
        -> exporting -> complete
```

Explicit failures are `source_failed`, `generation_partial`,
`generation_failed`, `render_failed`, and `export_failed`. The transition table
in `services/api/framefoley_api/state.py` rejects invalid jumps. Partial
generation preserves successful candidates.

## Progress and concurrency

Generation is bounded and synchronous at the API worker but publishes factual
SSE events from the state/event log. Deployment must permit long requests and
SSE; an unverified short-timeout function is unsuitable. A process-level
bounded semaphore defaults to one concurrent project generation. Production
edge/IP rate limiting is a deployment-layer owner action.

## Recovery

There is no hidden in-memory database. Project documents are schema-validated on
every save/load and reject unknown future versions. Browser progress events are
ephemeral, but authoritative project state and every material object are in B2.
See `B2_STORAGE_AND_RECOVERY.md`.

## Trust boundaries

- Browser input is untrusted and receives no provider/storage credential.
- Provider output is untrusted technical input until stored, hashed, decoded,
  inspected, and (for live candidates) manifest-verified.
- Canonical Genblaze manifests are never rewritten.
- Human creative approval and deterministic technical QC are separate facts.
