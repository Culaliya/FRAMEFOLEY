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
| LIVE EVIDENCE REPLAY sound effects | ElevenLabs Sound Effects generated through Genblaze and stored in B2 | **BLOCKED FOR CASH-PRIZE SUBMISSION** | Do not publish the current master as the hackathon video until provider-plan rights are remediated. |

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

1. The signed-in ElevenLabs subscription page displayed the current plan as
   **Free**.
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

Official references reviewed:

- <https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform>
- <https://elevenlabs.io/terms-of-use>
- <https://elevenlabs.io/sound-effects-terms>
- <https://elevenlabs.io/pricing>
- <https://backblaze-generative-media.devpost.com/rules>

## Fail-closed verdict

**PROVIDER RIGHTS: BLOCKED — OWNER ACTION REQUIRED.**

The current LIVE proof bytes and the current final video must not be represented
as cleared for this cash-prize submission. Attribution alone would support the
provider's stated non-commercial Free-plan sharing condition, but it does not
close the hackathon's rights representations.

Smallest defensible remediation:

1. Owner explicitly authorizes or performs a paid-plan change and accepts the
   current Terms, Sound Effects Terms, Prohibited Use Policy, and the residual
   non-exclusivity/sublicensing implications.
2. Before new SFX calls, owner decides whether to enable the Sound Effects
   sublicensing opt-out.
3. Generate fresh final-version LIVE candidates under the paid plan through the
   existing explicit live gate. Preserve immutable `proof/live/v1/`; publish a
   new versioned proof rather than mutating canonical or immutable records.
4. Rebuild the final video from the remediated proof, rerun the existing gates,
   then upload publicly and verify signed-out playback.

These steps are submission-rights remediation only. They do not authorize any
Phase 3 candidate or product feature.
