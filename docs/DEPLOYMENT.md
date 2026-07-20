# Deployment

## Supported shape

Deploy the web and API separately or as the supplied two-container stack.

The API host must support:

- Python 3.11+;
- FFmpeg and ffprobe;
- requests lasting at least 120 seconds;
- SSE without response buffering;
- private environment secrets;
- temporary disk for a 30 MB source plus derivatives;
- one or more long-running container/process workers.

Do not move generation into an unverified short-timeout serverless function.
The browser bundle contains no secret and may use any Node/Next-compatible host.

## Local container proof

```bash
cp .env.example .env
docker compose up --build
curl --fail http://localhost:8000/healthz
curl --fail http://localhost:8000/readyz
```

Compose intentionally starts in `demo` + local-storage mode. It is a local
reproduction environment, not evidence of production B2 persistence.

## API production variables

```text
FRAMEFOLEY_ENV=production
FRAMEFOLEY_STORAGE_MODE=b2
FRAMEFOLEY_HMAC_SECRET=<random high-entropy server secret>
GENERATION_MODE=live | demo | disabled
LIVE_GENERATION_ENABLED=true | false
FRAMEFOLEY_PROJECT_TTL_HOURS=72
FRAMEFOLEY_MAX_CONCURRENT_GENERATION=1
FRAMEFOLEY_PROJECT_RETRY_BUDGET=2
FRONTEND_ORIGIN=https://your-web-origin.example
B2_KEY_ID=<server secret>
B2_APP_KEY=<server secret>
B2_BUCKET=<private bucket name>
B2_REGION=<bucket region>
ELEVENLABS_API_KEY=<server secret>
```

Web build variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api-origin.example
```

`NEXT_PUBLIC_*` is intentionally public and must contain only the API origin.

For the public zero-provider-spend competition deployment, use:

```text
FRAMEFOLEY_STORAGE_MODE=b2
GENERATION_MODE=demo
LIVE_GENERATION_ENABLED=false
ELEVENLABS_API_KEY=<absent>
```

The API then reports `customUploadCanComplete=false` and
`anonymousProviderSpendEnabled=false`. Do not override those facts in frontend
copy. The private B2 values remain required for complete project persistence and
LIVE evidence replay.

## Deployment order

1. Create/confirm the private B2 bucket and scoped application key.
2. Configure the anonymous lifecycle rule and retain secret-safe evidence.
3. Treat provider spend/usage cap as prudent but non-blocking while public
   provider calls remain disabled; never claim it active before owner capture.
4. Publish and verify the immutable `proof/live/v2/` bundle from the paid-plan
   remediation evidence. Publication itself must make zero provider calls;
   historical `proof/live/v1/` remains untouched.
5. Deploy the API container with live generation disabled.
6. Confirm `/healthz`, `/readyz`, and `/v1/capabilities`; readiness must name
   `BACKBLAZE B2` and capabilities must show zero anonymous provider spend.
7. Deploy the web with the API origin baked into its build.
8. Set API `FRONTEND_ORIGIN` to the exact public web origin.
9. Preserve SSE no-buffer configuration. Edge/IP rate limiting remains prudent.
10. Run CACHED DEMO and LIVE EVIDENCE REPLAY publicly on desktop, tablet, and
    phone, including approval, render, export, download, and provenance.
11. Keep public LIVE generation disabled throughout judging.

## Security headers and transport

Terminate TLS at the deployment edge. Preserve `X-Content-Type-Options:
nosniff`, do not enable URL/query logging for object tokens, and do not forward
authorization headers to analytics. The app intentionally includes no analytics
SDK. Add CSP/HSTS at the edge after verifying video/audio blob/media behavior.

## Scale and recovery

The current in-process generation semaphore is per API process. For the narrow
competition deployment, run one generation worker/process or add a platform
global concurrency/rate policy. Multiple unconstrained API replicas would not
share that semaphore. Authoritative state still recovers from B2, but SSE event
history is process-local and may reconnect without replay after a restart.

## Rollback

- Set `LIVE_GENERATION_ENABLED=false` or `GENERATION_MODE=disabled` first.
- Keep B2 objects intact; never roll back by deleting canonical run objects.
- Redeploy the prior exact image.
- Validate cached demo, project recovery, and B2 reads.
- Re-enable live only after the manifest/B2 gate passes.

## Judge access

This product has no accounts. Provide the public web URL and a fresh anonymous
project path generated through the normal flow. Repository access must be public
or explicitly granted to the designated judge account by the owner. Record the
actual URLs in `OWNER_CHECKLIST.md` only after they work from a signed-out
browser.
