# FRAMEFOLEY Phase 1 final evidence summary

Current recommendation: **SUBMIT AFTER OWNER PUBLICATION**

## Proven locally

- **CACHED DEMO:** Original JELLY RELAY completes source -> cue -> six cached
  candidates -> deterministic QC/repair -> A/B audition -> approvals -> FFmpeg
  render -> deterministic ZIP -> provenance.
- **MOCKED:** Local object storage, fake-provider Genblaze integration, failure
  injection, restart recovery, and security controls are tested and never
  represented as production B2 evidence.
- Desktop/tablet/phone browser checks pass without console/runtime errors.
- The product recording is 2:55 and shows actual browser interaction.
- Source and evidence secret scans pass when `SECURITY_SCAN.md` is marked PASS.
- **LIVE:** The Phase 1 final-version gate made two bounded ElevenLabs SFX
  requests for one event. Both candidates reached `ready`, required zero
  retries, passed deterministic QC after local format repair, reached B2, and
  returned `true` from `Manifest.verify()`.
- The LIVE evidence inventory contains 24 non-empty B2 objects with recorded
  SHA-256 hashes, including source material, candidate audio, and canonical
  manifests.

## External truth boundary

- Phase 0 contains a separate **LIVE** ElevenLabs -> Genblaze -> B2 -> verified
  manifest proof and returned GO.
- `LIVE_CALLS_SANITIZED.json`, `B2_OBJECT_MAP.json`, and
  `MANIFEST_VERIFICATION.json` now contain the successful, explicitly
  authorized Phase 1 final-version live run.
- Public app, public/judge repository, public video URL, B2 lifecycle rule,
  provider spend cap, and designated judge access are **UNVERIFIED**.

## Why this is not yet “submit”

The scoped product and final-version live gate are complete. The remaining done
conditions are owner-controlled publication and account-console settings. They
cannot be inferred from local code or provider responses, so the evidence pack
does not claim them.
