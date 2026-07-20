# Architecture

## Scope boundary

FRAMEFOLEY has one flow: silent clip -> 1–3 cues -> two SFX candidates each ->
audition -> approve -> render -> export/provenance. There are no accounts,
database, teams, billing, chat, TTS, music, automatic video understanding,
analytics, or second provider.

## Components

| Component | Responsibility | Authority |
| --- | --- | --- |
| `apps/web` | Next.js UI, instant comparison, timeline, Web Audio audition, readiness gate | Human interaction only |
| `services/api` | Capability truth, HMAC access, state machine, generation/replay coordination, media and export | Server-side product authority |
| `packages/contracts` | JSON Schema v1 and generated TypeScript | Wire-format source of truth |
| Genblaze | Provider orchestration, canonical run/manifest | Self-hosted LIVE path and recorded proof lineage |
| ElevenLabs SFX | The one live audio provider | Provider output only |
| Backblaze B2 | Private durable production objects and immutable proof | System of record |
| FFmpeg/ffprobe | Inspection, repair, waveform, render, conversion | Deterministic technical processing |

## Request and data flow

1. The web reads `GET /v1/capabilities`; only the server decides whether custom
   upload can complete and whether the immutable LIVE proof is available.
2. Before project creation, a bounded readiness gate checks the API, media tools,
   and B2 readiness for up to 90 seconds without showing raw infrastructure
   errors.
3. The API creates an anonymous project and returns an expiring HMAC token.
4. The public browser selects the deterministic demo. Custom upload appears only
   when a self-hosted LIVE deployment reports that it can finish.
5. The API strips source audio, stores preview/thumbnail/metadata, and advances
   only through validated state transitions.
6. Cue edits are bounded to three events and stored as independent event JSON.
7. In `live` mode, each candidate is a Genblaze pipeline run persisted through
   `ObjectStorageSink` into the project's B2 prefix.
8. The API downloads the B2 object, re-hashes it, verifies both in-memory and
   B2-reloaded canonical manifests, then runs deterministic QC.
9. The browser auditions; only a person can approve a candidate.
10. Fixed-array FFmpeg commands produce the authoritative preview. A
    deterministic ZIP and provenance index are stored under the project prefix.

The landing comparison reuses one synchronized video element. It starts muted;
an explicit gesture only toggles approved preview audio. It is a CACHED DEMO
creative preview, not evidence of a provider request made now.

## LIVE evidence replay

The current immutable private bundle lives under `framefoley/proof/live/v2/`.
Its strict index records two outputs from the owner-verified paid-plan LIVE
remediation gate and the disabled Sound Effects Explore-sharing state. Every
source, event, candidate record, canonical manifest, QC report, waveform, and
derivative is covered by `checksums.sha256`. Historical
`framefoley/proof/live/v1/` bytes stay immutable and are not selected by the
public replay service.

`POST /v1/projects/live-proof` downloads and re-hashes the bundle, validates the
index, requires both official Genblaze `Manifest.verify()` calls to return true,
and compares provider/model/run/asset/QC lineage. Any missing, modified, or
relabeled object fails closed. A passing request clones the bytes into a new
private expiring project and starts at A/B audition. It does not invoke the
generation service and records `replayProviderCallCount=0`.

## State machine

```text
created -> source_uploading -> source_ready -> cueing
        -> generation_queued -> generating -> audition_ready
        -> approvals_complete -> rendering -> render_ready
        -> exporting -> complete
```

The proof replay enters honestly at `audition_ready`; provider generation
happened during the recorded LIVE gate, not in the replay request. Explicit
failures are `source_failed`, `generation_partial`, `generation_failed`,
`render_failed`, and `export_failed`. The transition table rejects invalid
jumps. Partial generation preserves successful candidates.

## Progress and concurrency

Generation is bounded and synchronous at the API worker but publishes factual
SSE events from the state/event log. Deployment must permit long requests and
SSE; an unverified short-timeout function is unsuitable. A process-level
bounded semaphore defaults to one concurrent project generation. Production
edge/IP rate limiting is a prudent owner deployment control.

The browser reconnects SSE once with `Last-Event-ID`. If that second stream
fails, it polls the authoritative project document; it never invents missing
pipeline events. The same idempotency key remains attached to a generation
submission, so recovery does not duplicate provider requests.

## Recovery

There is no hidden in-memory database. Project documents are schema-validated on
every save/load and reject unknown future versions. Browser progress events are
ephemeral, but authoritative project state and every material object are in B2.
See `B2_STORAGE_AND_RECOVERY.md`.

## Trust boundaries

- Browser input is untrusted and receives no provider/storage credential.
- Provider output is untrusted technical input until stored, hashed, decoded,
  inspected, and (for LIVE candidates) manifest-verified.
- Canonical Genblaze manifests are never rewritten.
- The immutable proof prefix is never exposed directly to the browser; replay
  media inherits the project-token and expiring object-token model.
- Public capability responses are strict, short-cached, and contain no bucket,
  key, credential, signed URL, or internal path.
- Human creative approval and deterministic technical QC are separate facts.
