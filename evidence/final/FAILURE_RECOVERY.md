# Failure and recovery evidence

All rows are **MOCKED deterministic failure tests** unless explicitly labeled.
No paid failure was deliberately called.

| Scenario | Expected safe result | Evidence |
| --- | --- | --- |
| Missing live opt-in | No provider call | Make/Python gate rejects |
| Generation disabled | Typed 503; demo source remains viewable | API integration test |
| Live kill switch closed | Typed configuration failure; no provider call | API integration test |
| Invalid B2 credentials | Sanitized storage preflight failure | Phase 0 failure test |
| Provider timeout/model error | Candidate never verified | Phase 0 failure test |
| One candidate fails | `generation_partial`; five successes preserved | Phase 1 integration test |
| Storage fails after provider success | Bytes retained; storage-only retry; provider count unchanged | Phase 0 failure test |
| Silent/corrupt audio | Regenerate/failed; never approved automatically | QC tests |
| Repairable audio | 48 kHz mono PCM WAV; after verdict PASS | QC + full demo test |
| Tampered manifest | `Manifest.verify()` false; cannot mark verified | Manifest policy test |
| Duplicate generate | Same candidate IDs; no repeated generation | Full API flow |
| API process restart | Project/source hash recovered from object store | Restart integration test |
| Cross-project token | Typed 403 | API token isolation test |

Production B2 restart recovery uses the same repository path but remains tied to
the final LIVE/B2 gate in this pack. Phase 0 separately proves real B2
write/read/re-hash.
