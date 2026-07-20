# FRAMEFOLEY Phase 2 owner verification

This checklist separates submission blockers from prudent account hardening. A
box may be marked `OWNER-VERIFIED` only after the owner has current evidence.
Source code, a local mock, or a successful screenshot cannot prove an account
console setting.

## True pre-submission blockers

| Requirement | Current evidence needed | Status |
| --- | --- | --- |
| Public app opens without login | Signed-out desktop and mobile load | OWNER-VERIFIED |
| Public repository opens for judges | Signed-out repository load | OWNER-VERIFIED |
| Final video opens without login | Anonymous YouTube watch/embed/player checks | OWNER-VERIFIED |
| B2 bucket is private | Current bucket access setting, with account identity cropped | OWNER-VERIFIED |
| B2 key is bucket-scoped and least-privilege | Current application-key scope/capabilities, with key values hidden | OWNER-VERIFIED |
| Source/build/media contain no credential | Final `make secret-scan` plus media review | OWNER-VERIFIED |
| LIVE proof bundle is available and verifies | Publication and public verification JSON | OWNER-VERIFIED |
| Dependency and asset licenses are accepted | Owner review of lockfiles and `docs/ASSET_PROVENANCE.md` | UNVERIFIED |
| Deployed commit is recorded | Public `/healthz` commit or Render deploy evidence | OWNER-VERIFIED |
| Desktop, phone, and tablet complete | Public Playwright result and screenshots | OWNER-VERIFIED |
| App remains available during judging | Owner availability decision and judging-window check | UNVERIFIED |

Do not convert an `UNVERIFIED` row to `PASS` because it is likely true. Record
the smallest sufficient, secret-safe evidence in
`evidence/phase2/OWNER_CHECKS.md`.

## Publish the immutable paid LIVE proof v2

The paid remediation command makes one bounded two-candidate LIVE run, stores
fresh objects in B2, verifies both canonical manifests, and publishes the
versioned private v2 replay bundle. The publication step makes zero additional
provider calls and never modifies historical v1.

```bash
./scripts/run_paid_live_v2_securely.sh
```

The prompt asks for the four B2 values and ElevenLabs API key in the local
Terminal. Secret values are neither echoed nor written to `.env`. Type
`RUN PAID LIVE V2` only after the displayed scope is correct. The underlying
fail-closed command is:

```bash
FRAMEFOLEY_ALLOW_LIVE_CALLS=1 \
FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1 \
FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED=1 \
make paid-live-v2
```

Expected safe result:

```text
LIVE proof publication PASS: status=created|already-present candidates=2 manifests=2 assetHashes=2 providerCalls=0
```

## Public verification

After the implementation commit is deployed and the proof bundle exists:

```bash
make verify-public
```

This checks the web root; API health, readiness, strict capabilities, exact
CORS, and SSE headers; full CACHED DEMO and LIVE EVIDENCE REPLAY completion;
zero replay provider calls; and desktop, tablet, and phone browser flows. It
stores sanitized results only. Project tokens and signed URLs remain in memory
and are never written to the evidence pack.

Independently confirm these two signed-out surfaces:

```text
https://framefoley-culaliya.onrender.com
https://github.com/Culaliya/FRAMEFOLEY
```

The creator-voiceover final video is public at <https://youtu.be/Q8F8djVgkgA>. Anonymous watch,
embed, oEmbed, player, 1080p, audio, and manual English-caption checks passed.
The earlier proof-v2 upload remains public and is not relabeled or deleted.

## Prudent, non-blocking controls

These remain recommended, but they are not submission blockers while the
public capability contract reports both
`anonymousProviderSpendEnabled=false` and `customUploadCanComplete=false`:

- ElevenLabs account spend cap — useful defense in depth for a later LIVE host,
  but the public judge flow has no provider-call path.
- Edge/IP rate limit — useful against API and B2 traffic spikes, though it
  cannot create ElevenLabs spend in the zero-provider-spend public mode.
- B2 lifecycle expiration — useful for storage hygiene; anonymous projects
  already carry application-level expiry metadata.
- External uptime monitor — useful for Render Free cold starts and availability,
  but the product also has a bounded readiness gate and fallback evidence.

Do not claim any of these controls active without current owner-console
evidence.

## Final owner seal

- [ ] Review every blocker above and update `OWNER_CHECKS.md` truthfully.
- [x] Upload the 2:45–2:58 master and verify anonymous playback.
- [x] Paste the final public video URL into the submission and evidence docs.
- [ ] Confirm the app should stay deployed for the full judging window.
- [ ] Run `make phase2-evidence`, then `make secret-scan` one final time.

Phase 2 verification does not authorize Phase 3.
