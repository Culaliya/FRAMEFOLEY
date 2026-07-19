# Owner checklist

Items remain unchecked until the owner verifies the external state. Source code
and local browser tests cannot prove them.

## Credentials and account controls

- [ ] B2 bucket is private.
- [ ] B2 application key is restricted to the intended bucket/capabilities.
- [ ] B2 anonymous lifecycle rule is active and captured without account email.
- [ ] ElevenLabs key is scoped/revocable and stored only in the API host.
- [ ] ElevenLabs spend/usage cap is active and captured.
- [ ] Current ElevenLabs plan/terms permit the intended public competition use.
- [ ] Production HMAC secret is high-entropy and different from development.

## Final live gate

- [ ] Run `FRAMEFOLEY_ALLOW_LIVE_CALLS=1 make live-smoke` against the final code.
- [ ] At least one final-version candidate is `LIVE`, stored in B2, re-hashed,
      and `manifestVerified=true`.
- [ ] Exact call count and provider-reported cost/unavailable status are in the
      sanitized evidence.
- [ ] No live candidate is actually a cached or mocked asset.

## Deployment

- [ ] Public web URL: `[UNVERIFIED]`
- [ ] Public API `/readyz` reports ready and B2: `[UNVERIFIED]`
- [ ] TLS, exact CORS origin, no-buffer SSE, and edge/IP rate limit are active.
- [ ] Cached demo completes from a signed-out desktop browser.
- [ ] Phone and tablet layouts were checked at the public URL.
- [ ] Live kill switch was tested and can be activated without a deploy.
- [ ] Deployment remains available for the full judging window.

## Repository and judge access

- [ ] Public or judge-accessible repository URL: `[UNVERIFIED]`
- [ ] Exact source commit recorded: `[UNVERIFIED - no git repository yet]`
- [ ] Designated judge account has access if the repository is private.
- [ ] Fresh clone follows README setup with no local-only file dependency.
- [ ] No `.env`, token, cookie, account email, or signed URL is committed.

## Submission media

- [ ] Public demo video URL: `[UNVERIFIED]`
- [ ] Video is around three minutes and has captions/transcript.
- [ ] Narration uses the exact Genblaze/B2/QC/human-decision disclosure.
- [ ] Video visibly distinguishes `CACHED DEMO` from separate `LIVE` evidence.
- [ ] Screenshots contain no credentials, account identity, or signed URL.

## Copy and rights

- [ ] Devpost copy matches the deployed behavior.
- [ ] Providers/models and exact B2/Genblaze roles are listed.
- [ ] JELLY RELAY generator and checksums are included.
- [ ] Lucide upstream license and dependency license obligations are acceptable.
- [ ] No rights warranty or active spend/lifecycle claim lacks evidence.

## Final seal

- [ ] `make check`
- [ ] `make browser-test`
- [ ] clean install in a fresh directory
- [ ] production API container build
- [ ] production web container build
- [ ] final secret scan after evidence/video generation
- [ ] evidence `checksums.sha256` regenerated last

Do not submit while a required external item is still `[UNVERIFIED]`.
