# Phase 2 owner checks

Recorded: 2026-07-19 (Asia/Taipei)

This file records only secret-safe outcomes. Account identity, application-key
values, bucket identifiers, payment details, cookies, and dashboard screenshots
are intentionally excluded.

## True pre-submission blockers

| Requirement | Status | Secret-safe evidence |
| --- | --- | --- |
| Public app accessible without login | **OWNER-VERIFIED** | Anonymous HTTP request returned `200`; the final public browser verifier also passed. |
| Public repository accessible to judges | **OWNER-VERIFIED** | Anonymous HTTP request to the GitHub repository returned `200`. |
| Final public video accessible without login | **OWNER-VERIFIED** | Anonymous watch and embed requests returned `200`; oEmbed returned the correct title/channel; the public player reported `OK`, 1080p, audio, manual English captions, and embeddability. |
| B2 bucket confirmed private | **OWNER-VERIFIED** | The current Backblaze console setting was inspected while signed in; no private dashboard capture was retained. |
| B2 application key is bucket-scoped and least-privilege | **OWNER-VERIFIED** | The current key is limited to the FRAMEFOLEY bucket and `framefoley/` prefix with `readFiles`, `writeFiles`, and `listFiles`; no key value or key ID was recorded. |
| No credential in source, build output, screenshots, or video | **OWNER-VERIFIED** | Final `make secret-scan` passed; public screenshots and the 2:56 master were visually reviewed and contain no account console or credential screen. |
| LIVE proof bundle available and verifiable | **OWNER-VERIFIED** | Two B2-re-downloaded hashes matched and both canonical manifests returned true; replay opening made zero provider calls. |
| Dependency and asset licenses accepted | **UNVERIFIED** | Owner review/acceptance of lockfile dependencies and `docs/ASSET_PROVENANCE.md` remains required. |
| Deployed commit recorded | **OWNER-VERIFIED** | Render Web and API both displayed `2d91488`; public API reported the full runtime commit `2d9148851b6f288b0c4f2cef6dd5739e156fd73f`. |
| Desktop, phone, and tablet public paths complete | **OWNER-VERIFIED** | Final public verifier passed all three viewports with zero browser console/runtime errors. |
| App remains available during judging | **UNVERIFIED** | Owner must keep both Render services available for the full judging window. |

## Prudent non-blocking controls

- **OWNER-VERIFIED:** Backblaze daily storage cap is `$0.01` and daily download
  bandwidth cap is `$0.01`; the combined configured maximum is `$0.02/day`.
- **UNVERIFIED:** ElevenLabs account spend cap. The public deployment cannot make
  provider calls, so this remains defense in depth rather than a submission blocker.
- **UNVERIFIED:** Edge/IP rate limit.
- **UNVERIFIED:** B2 lifecycle expiration.
- **UNVERIFIED:** External uptime monitor.

Phase 3 is not authorized by any owner check in this file.
