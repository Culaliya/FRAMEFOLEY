# Owner checklist

This is the submission-facing mirror of
`product/docs/OWNER_VERIFICATION_PHASE_2.md`. Items remain unchecked until
current source, public, or owner-console evidence exists. Likelihood is not
evidence.

## True submission blockers

- [ ] Public app opens without login.
- [ ] Public repository opens without judge access setup.
- [ ] Final YouTube/Vimeo video plays without login.
- [ ] B2 bucket is confirmed private.
- [ ] B2 application key is confirmed bucket-scoped and least-privilege.
- [ ] Final source, build output, screenshots, and video pass the secret scan.
- [ ] Immutable LIVE proof bundle is available and verifies from B2.
- [ ] Dependency and asset licenses are accepted by the owner.
- [ ] Exact deployed source commit is recorded.
- [ ] Public desktop, tablet, and phone paths complete without runtime errors.
- [ ] App is expected to remain available throughout judging.

## Product truth seal

- [ ] Public capabilities report `generationMode=demo`.
- [ ] Public capabilities report `customUploadCanComplete=false`.
- [ ] Public capabilities report `anonymousProviderSpendEnabled=false`.
- [ ] Landing page contains no active custom-upload dead end.
- [ ] CACHED DEMO completes cueing, six candidates, approval, render, export,
      download, and provenance in private B2.
- [ ] LIVE EVIDENCE REPLAY opens, exposes two LIVE candidates, and records zero
      provider calls during replay.
- [ ] Both canonical proof manifests return true from `Manifest.verify()`.
- [ ] Both proof assets match their B2 re-download SHA-256 records.
- [ ] One replay candidate completes approval, render, export, and provenance.

## Required gates

- [ ] `make install` passes in a clean temporary clone with locked dependencies.
- [ ] `make check` passes.
- [ ] `make browser-test` passes.
- [ ] `make phase2-proof-test` passes.
- [ ] `make secret-scan` passes after final evidence and video assembly.
- [ ] Final master is 2:45–2:58, 1920×1080, narrated in English, and contains an
      embedded English subtitle track plus sidecar WebVTT.

## Prudent but non-blocking in public zero-provider-spend mode

- [ ] ElevenLabs account spend cap.
- [ ] Edge/IP rate limit.
- [ ] B2 lifecycle expiration.
- [ ] External uptime monitor.

These controls remain worthwhile defense in depth. They do not block submission
while public provider calls and custom upload are both disabled. Do not claim
them active without owner evidence.

## Final owner actions

1. Run `./scripts/run_phase2_proof_publish_securely.sh`; it asks for B2 values
   only and makes zero provider calls.
2. Run `make verify-public` after the final commit is deployed.
3. Review and update `evidence/phase2/OWNER_CHECKS.md`.
4. Upload the final master to YouTube/Vimeo and verify signed-out playback.
5. Run `make phase2-evidence`, then `make secret-scan` last.

Completion of this checklist does not authorize another product phase.
