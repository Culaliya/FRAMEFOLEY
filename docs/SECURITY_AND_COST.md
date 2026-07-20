# Security, privacy, abuse, and cost

## Credentials

`B2_KEY_ID`, `B2_APP_KEY`, `B2_BUCKET`, `B2_REGION`, and
`ELEVENLABS_API_KEY` are server environment values. They are never serialized
into project documents, sent to the browser, accepted as request input, logged,
or stored in evidence. Production additionally requires a non-default
`FRAMEFOLEY_HMAC_SECRET`.

## Anonymous access

- HMAC-SHA256 project tokens contain project ID, token kind, and expiry.
- Constant-time signature comparison and canonical base64url decoding are used.
- Object tokens carry one already validated key inside one project prefix.
- Cross-project token use is rejected.
- Asset responses are private, short-lived, range-capable, and `nosniff`.

No accounts means possession of the anonymous project token grants project
access until expiry. Users must not share it.

## Input and process safety

- MP4/WebM only, <=30 MB, 8–15 seconds, 480p–1080p, validated by ffprobe.
- 1–3 events; unique IDs/slugs; type-specific durations; marker before clip end.
- Custom style/material text is Unicode-normalized, control-character rejected,
  and length-bounded.
- Gains are -12 to +6 dB; object keys cannot be absolute, traverse, or escape.
- FFmpeg receives argument arrays. No user text enters shell strings.
- Public errors are typed and sanitized; raw tracebacks and full tokens are not
  returned. API access logging is disabled to avoid token-bearing URL logs.

## Live controls

- `GENERATION_MODE` is `live`, `demo`, or `disabled`.
- `LIVE_GENERATION_ENABLED=false` is the default global kill switch.
- Live also requires `FRAMEFOLEY_STORAGE_MODE=b2` and complete credentials.
- Each project has a hard 12-call ceiling, six initial candidates maximum, one
  retry maximum per candidate, and a lower configurable shared retry budget
  (default 2).
- Generation uses an idempotency-key digest and a bounded concurrent-project
  semaphore (default 1).
- Provider call timeout is 45 s; pipeline timeout is 60 s; no hidden retries.
- Demo cache remains available when live is closed.

The public competition deployment is `GENERATION_MODE=demo` and exposes a
server-owned capability contract. It reports both
`anonymousProviderSpendEnabled=false` and `customUploadCanComplete=false`.
The browser cannot override these facts, and the upload-ticket endpoint also
fails closed when the live contract is incomplete.

## Immutable proof controls

- Publication requires `FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1` plus private B2
  credentials; it imports no ElevenLabs key.
- `proof/live/v2/` is the current immutable replay: existing different bytes
  stop publication. Historical `proof/live/v1/` remains accepted only as a
  versioned legacy record and is never overwritten by the v2 command.
- A complete checksum inventory covers every allowed proof object and rejects
  missing or unexpected paths.
- Both canonical manifests must return true from the official
  `Manifest.verify()` implementation after B2 download.
- Provider, model, run, asset hash, QC, and repair lineage must match the strict
  LIVE-only index.
- Opening a replay invokes no generation service and records zero replay calls.
- The proof prefix never reaches the browser. Media is cloned into an isolated
  expiring project protected by the existing HMAC/object-token boundary.

Per-IP/edge rate limiting depends on the selected host and is therefore an
**OWNER-VERIFIED** deployment control, not a source-code claim.

## Cost truth

The evidence records exact calls and provider-reported USD cost when available.
The current connector may report no cost. An absent value means **UNAVAILABLE**,
not zero. The owner must configure and capture an ElevenLabs account spend/usage
cap separately. No cap is claimed active without account evidence.

For the zero-provider-spend public build, an ElevenLabs account spend cap and edge/IP
rate limit remain prudent defense in depth but are not submission blockers:
there is no public provider-call path. B2 lifecycle expiration and an external
uptime monitor are likewise recommended and owner-controlled, not silently
claimed active.

Live commands require an explicit command opt-in and are absent from normal CI:

```text
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make live-smoke
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make full-demo-generation
```

Proof publication is a separate, no-provider-call command:

```text
FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1 make publish-live-proof
```

## Scanning

`scripts/secret_scan.py` scans source and the entire evidence tree without
printing matched values. It detects common provider/token/private-key shapes,
credential assignments, signed AWS query fields, and home paths in evidence.
