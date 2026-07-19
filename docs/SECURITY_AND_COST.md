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

Per-IP/edge rate limiting depends on the selected host and is therefore an
**OWNER-VERIFIED** deployment control, not a source-code claim.

## Cost truth

The evidence records exact calls and provider-reported USD cost when available.
The current connector may report no cost. An absent value means **UNAVAILABLE**,
not zero. The owner must configure and capture an ElevenLabs account spend/usage
cap separately. No cap is claimed active without account evidence.

Live commands require an explicit command opt-in and are absent from normal CI:

```text
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make live-smoke
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make full-demo-generation
```

## Scanning

`scripts/secret_scan.py` scans source and the entire evidence tree without
printing matched values. It detects common provider/token/private-key shapes,
credential assignments, signed AWS query fields, and home paths in evidence.
