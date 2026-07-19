# FRAMEFOLEY Phase 1 final evidence summary

Current recommendation: **SUBMIT AFTER FIXES — owner console controls only**

## Proven locally

- **CACHED DEMO:** Original JELLY RELAY completes source -> cue -> six cached
  candidates -> deterministic QC/repair -> A/B audition -> approvals -> FFmpeg
  render -> deterministic ZIP -> provenance.
- **MOCKED:** Local object storage, fake-provider Genblaze integration, failure
  injection, restart recovery, and security controls are tested and never
  represented as production B2 evidence.
- Desktop/tablet/phone browser checks pass without console/runtime errors.
- The product recording is 2:56 and shows actual browser interaction.
- Source and evidence secret scans pass when `SECURITY_SCAN.md` is marked PASS.
- **LIVE:** The Phase 1 final-version gate made two bounded ElevenLabs SFX
  requests for one event. Both candidates reached `ready`, required zero
  retries, passed deterministic QC after local format repair, reached B2, and
  returned `true` from `Manifest.verify()`.
- The LIVE evidence inventory contains 24 non-empty B2 objects with recorded
  SHA-256 hashes, including source material, candidate audio, and canonical
  manifests.

## Proven in the public deployment

- Public repository: <https://github.com/Culaliya/FRAMEFOLEY>
- Public app: <https://framefoley-culaliya.onrender.com>
- Public API readiness:
  <https://framefoley-api-culaliya.onrender.com/readyz>
- Public demo video:
  <https://raw.githubusercontent.com/Culaliya/FRAMEFOLEY/main/evidence/final/video/framefoley-demo.mp4>
- API and web Docker services deployed source commit
  `4a4d994eeaa07507d4da8189b92ac2f14c4ba586` on Render Free.
- Five independent root probes returned HTTP 200; `/healthz` returned `ok` and
  `/readyz` returned `ready`, `generationMode=demo`, and
  `storage=BACKBLAZE B2`.
- A public browser completed JELLY RELAY end to end: three cues, six
  **CACHED DEMO** candidates ready, three human approvals, authoritative mix
  `B2 STORED`, 23-file deterministic ZIP `B2 OBJECT READY`, and six provenance
  records with `STORAGE RECORD — BACKBLAZE B2`.
- Public live generation is intentionally disabled and no ElevenLabs key is on
  the public host, so anonymous traffic cannot spend provider credit.

See `PUBLIC_DEPLOYMENT.md` for the sanitized public-flow proof.

## External truth boundary

- Phase 0 contains a separate **LIVE** ElevenLabs -> Genblaze -> B2 -> verified
  manifest proof and returned GO.
- `LIVE_CALLS_SANITIZED.json`, `B2_OBJECT_MAP.json`, and
  `MANIFEST_VERIFICATION.json` contain the successful, explicitly authorized
  Phase 1 final-version live run.
- Public app, repository, video, Docker builds, and anonymous B2-backed demo are
  verified.
- The B2 lifecycle rule, ElevenLabs account plan/terms, provider spend/usage
  cap, public phone/tablet pass, full judging-window uptime, and the combined
  edge/SSE deployment-control checklist remain **UNVERIFIED**.

## Why this is still “submit after fixes”

The scoped product, final-version live gate, and public competition deployment
are complete. The remaining blockers are owner-controlled account-console and
judging-window checks. In particular, the 72-hour app expiry does not prove the
matching B2 lifecycle rule is active. The evidence pack does not infer or claim
those settings.
