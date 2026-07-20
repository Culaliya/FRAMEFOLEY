# Owner checklist

This is the submission-facing mirror of
`product/docs/OWNER_VERIFICATION_PHASE_2.md`. Items remain unchecked until
current source, public, or owner-console evidence exists. Likelihood is not
evidence.

## True submission blockers

- [x] Public app opens without login.
- [x] Public repository opens without judge access setup.
- [x] Final YouTube video plays without login.
- [x] B2 bucket is confirmed private.
- [x] B2 application key is confirmed bucket-scoped and least-privilege.
- [x] Final source, build output, screenshots, and video pass the secret scan.
- [x] Immutable LIVE proof bundle is available and verifies from B2.
- [ ] Dependency and asset licenses are accepted by the owner.
- [x] Exact deployed runtime commit is recorded.
- [x] Public desktop, tablet, and phone paths complete without runtime errors.
- [ ] App is expected to remain available throughout judging.

## Product truth seal

- [x] Public capabilities report `generationMode=demo`.
- [x] Public capabilities report `customUploadCanComplete=false`.
- [x] Public capabilities report `anonymousProviderSpendEnabled=false`.
- [x] Landing page contains no active custom-upload dead end.
- [x] CACHED DEMO completes cueing, six candidates, approval, render, export,
      download, and provenance in private B2.
- [x] LIVE EVIDENCE REPLAY opens, exposes two LIVE candidates, and records zero
      provider calls during replay.
- [x] Both canonical proof manifests return true from `Manifest.verify()`.
- [x] Both proof assets match their B2 re-download SHA-256 records.
- [x] One replay candidate completes approval, render, export, and provenance.

## Required gates

- [x] `make install` passes in a clean temporary clone with locked dependencies.
- [x] `make check` passes.
- [x] `make browser-test` passes.
- [x] `make phase2-proof-test` passes.
- [x] `make secret-scan` passes after final evidence and video assembly.
- [x] Final master is 2:45–2:58, 1920×1080, narrated in English, and contains an
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
4. Creator-voiceover final master published and anonymously verified at
   `https://youtu.be/Q8F8djVgkgA`; the earlier public proof-v2 upload remains
   available as historical evidence.
5. Run `make phase2-evidence`, then `make secret-scan` last.

Completion of this checklist does not authorize another product phase.
