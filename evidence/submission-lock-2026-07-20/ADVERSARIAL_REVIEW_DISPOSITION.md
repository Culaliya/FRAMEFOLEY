# Adversarial review disposition

Recorded: 2026-07-20 (Asia/Taipei)

Source review:
`FRAMEFOLEY_ADVERSARIAL_REVIEW_2026-07-20.md` supplied by the owner.

## Bounded pre-submission actions

| Finding | Disposition | Evidence |
| --- | --- | --- |
| `OPEN A VERIFIED LIVE RUN` blurs the current action | FIXED IN SOURCE | Landing CTA now says `OPEN VERIFIED LIVE EVIDENCE REPLAY`. |
| Broad `ZERO-SPEND` wording | FIXED IN SOURCE/DOCS | Current UI and submission docs say `ZERO-PROVIDER-SPEND`. |
| Broad `WITHOUT NEW SPEND` wording | FIXED IN SOURCE | Replay banner says `WITHOUT NEW PROVIDER CALLS`. |
| First-touch proof line missing | FIXED IN SOURCE | Landing now states `2 REAL PROVIDER OUTPUTS · RE-VERIFIED FROM B2 · 0 CALLS TO REPLAY`. |
| Copy regression coverage | FIXED IN TEST | `tests/test_phase2_copy.py` asserts the exact replacement text and rejects the three old phrases. |
| Dependency / asset evidence | PAID LIVE V2 RIGHTS REMEDIATED; DEPENDENCY NOTICES RETAINED | Starter, owner terms confirmation, disabled SFX Explore sharing, fresh calls, B2 hashes, and immutable proof v2 are recorded in `RIGHTS_AND_LICENSE_AUDIT.md`. |
| Public YouTube video | READY AFTER V2 REBUILD AND FINAL QA | The older master remains historical; upload only the rebuilt proof-v2 master after its gates pass. |
| Render availability during judging | OWNER OPERATIONAL COMMITMENT REQUIRED | This is a future availability fact and cannot be converted into current proof. |

## Explicitly not implemented

Phase 3 remains **NOT AUTHORIZED**. No Offline Proof Verifier, Expiry
Reconciler, Whole-Kit Consistency Audition, account system, database, provider,
generation modality, or architecture redesign was added.
