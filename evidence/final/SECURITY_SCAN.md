# Security scan

Status: **PASS — SOURCE + EVIDENCE**

`make secret-scan` completed in the working tree after the final-version LIVE
gate and in a fresh source-only copy. It scans without printing matched values.

Covered rules include:

- provider/API token shapes;
- private keys and AWS access-key shapes;
- non-placeholder secret assignments;
- signed AWS query fields;
- authorization/cookie/project-token fields in copy-safe provenance;
- local home-directory paths in evidence;
- `.env` and generated/cache directories excluded from publication.

The evidence pack contains no API key, HMAC secret, authorization header,
cookie, signed query string, account email, or home path. Screenshots and videos
were visually inspected and show only anonymous project IDs/hashes/object keys.

The public repository and raw demo-video URL return HTTP 200. Public API
responses expose health/readiness labels but no credential. The public host
runs `GENERATION_MODE=demo` with live generation disabled and without the
ElevenLabs key; B2 credentials remain masked API-host variables.

The post-LIVE and post-publication scans passed. Public URL metadata was added
without a secret finding, and `checksums.sha256` was regenerated last.
