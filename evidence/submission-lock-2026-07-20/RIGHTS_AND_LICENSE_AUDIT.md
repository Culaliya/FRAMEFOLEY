# Rights and license audit

Recorded: 2026-07-20 (Asia/Taipei)

This is a technical evidence record, not legal advice and not an owner signature.
Legal acceptance remains an owner action.

## Asset inventory

| Asset group | Source / proof | Risk status | Submission action |
| --- | --- | --- | --- |
| JELLY RELAY video, thumbnail, and event metadata | Original deterministic local generator; reproduction command and checksums are recorded in `docs/ASSET_PROVENANCE.md` and `demo/jelly-relay-assets.json` | SAFE | Retain source and checksums. |
| Procedural CACHED DEMO WAV files | Original oscillator/noise/envelope synthesis from the same local generator | SAFE | Keep labeled `CACHED DEMO`; do not relabel as provider output. |
| Landing approved mix | Deterministic derivative of original JELLY RELAY plus original procedural cues | SAFE | Retain lineage. |
| FRAMEFOLEY mark and UI visual system | Original SVG and CSS | SAFE | No external asset notice needed. |
| System font stacks | No font file is downloaded or redistributed | SAFE | Continue using system fallbacks. |
| Lucide UI icons | `lucide-react@1.25.0`; installed package contains ISC and Feather-derived MIT notices | ATTRIBUTE / NOTICE RETAINED | See `docs/THIRD_PARTY_NOTICES.md`. |
| Historical LIVE proof v1 sound effects | ElevenLabs Sound Effects generated while the inspected account was Free | **DO NOT USE FOR CASH-PRIZE SUBMISSION** | Retain immutable historical evidence; the current replay service does not select v1. |
| Paid LIVE proof v2 sound effects | Fresh ElevenLabs Sound Effects generated after Starter and the disabled Explore-sharing state were owner-verified; Genblaze manifests and B2 hashes verified | **OWNER-VERIFIED / RIGHTS REMEDIATED** | Use only the v2 replay bytes and a master rebuilt from v2. |

## Dependency metadata review

- `pnpm-lock.yaml` plus the installed production-license inventory reported 62
  Node package/version entries: 44 MIT, 8 Apache-2.0, 7 ISC versions, and one
  each BSD-3-Clause, 0BSD, CC-BY-4.0, and LGPL-3.0-or-later.
- `requirements.lock` plus installed Python metadata reported 67 non-project
  distributions. Every distribution reported a license expression, license
  field, or license classifier. The set is permissive or weak-copyleft; no GPL
  or AGPL dependency was reported.
- Direct packages and notable transitive notice obligations are retained in
  `docs/THIRD_PARTY_NOTICES.md`. Lockfiles remain the exact version identity
  source of truth.

Technical dependency verdict: **PASS WITH NOTICES**. This does not replace the
owner's acceptance of the applicable licenses.

## Current provider-rights facts

The following facts were checked on 2026-07-20 without retaining account,
payment, cookie, key, or identity data:

1. The earlier signed-in inspection displayed **Free**; those historical v1
   outputs were not treated as retroactively commercial.
2. ElevenLabs' current publishing guidance says its Free plan does not include
   a commercial license. It also requires `elevenlabs.io` or `11.ai` in the
   title when Free-plan output is published non-commercially.
3. The same guidance says outputs generated during a paid subscription may be
   used commercially, subject to the applicable agreement, input rights,
   laws, Terms, and Prohibited Use Policy; it does not make pre-subscription
   output retroactively commercial.
4. The Sound Effects Terms, last updated 2026-02-12, state that SFX outputs may
   be sublicensed to third parties unless the account uses the product's
   `Disable` opt-out. Existing sublicenses or uses are not revoked by a later
   opt-out.
5. The Backblaze hackathon offers cash prizes and requires third-party
   integrations to be authorized under their terms. Its public demo video must
   not include copyrighted third-party material without permission, and its
   submission ownership and IP representations are broader than a casual
   non-commercial upload.
6. At 2026-07-20 17:15 CST, after the owner personally completed payment and
   final terms confirmation, the signed-in workspace displayed **Starter**.
7. Before the new calls, the Sound Effects UI was changed to state that
   generated results would not be shared to Explore for other users to download.
8. At 2026-07-20 17:21 CST, the bounded remediation gate made exactly two new
   provider calls, produced two ready LIVE candidates, stored 24 project objects
   in B2, and recorded two `Manifest.verify() == true` results.
9. Immutable `framefoley/proof/live/v2/` publication returned `created`; two
   downloaded asset hashes matched, two manifests re-verified, and publication
   itself made zero provider calls. The v2 index records the owner-verified
   Starter and disabled Explore-sharing basis.

Official references reviewed:

- <https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform>
- <https://elevenlabs.io/terms-of-use>
- <https://elevenlabs.io/sound-effects-terms>
- <https://elevenlabs.io/pricing>
- <https://backblaze-generative-media.devpost.com/rules>

## Fail-closed verdict

**PROVIDER RIGHTS FOR LIVE V2: REMEDIATED — FINAL MEDIA REBUILD AND QA PASSED.**

The historical v1 bytes remain excluded. The fresh v2 bytes were generated only
after the owner completed the paid-plan/terms action and disabled SFX Explore
sharing. They are covered by fresh canonical manifests, B2 object hashes, and an
immutable v2 checksum inventory.

Completed media gates:

1. Source selecting proof v2 was deployed to both public Render services.
2. The public replay was exercised and a new 1920x1080 master was captured from
   v2.
3. The 2:56 master contains H.264 video, AAC audio, an embedded English subtitle
   track, and a sidecar WebVTT file.
4. Six key frames and the contact sheet were visually reviewed; no account
   console, credential, signed URL, or private identifier was exposed.

Remaining publication gate: upload this rebuilt master publicly and verify
signed-out playback, 1080p processing, captions, and embeddability.

These steps are submission-rights remediation only. They do not authorize any
Phase 3 candidate or product feature.
