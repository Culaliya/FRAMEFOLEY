# Phase 0 spike plan

## Scope contract

| Item | Decision |
| --- | --- |
| User goal | Prove or reject the Genblaze → ElevenLabs SFX → B2 → manifest → QC chain |
| Existing system to preserve | The product blueprint and Phase 0 acceptance gate |
| Allowed change area | Python spike CLI, deterministic fixtures/QC, tests, owner docs, sanitized evidence |
| Explicit non-goals | Frontend, public API, database, full product, second provider, Phase 1 |
| Files touched | Root packaging files, `docs/`, `src/framefoley_spike/`, `scripts/`, `tests/`, `artifacts/phase0/` |
| Verification required | Format/lint/type/unit tests, local canonical manifest, B2 smoke, one authorized live SFX, evidence secret scan |

## Execution order

1. Resolve and inspect current official packages and FFmpeg.
2. Generate a deterministic 0.6-second 48 kHz mono WAV fixture.
3. Create and round-trip a canonical Genblaze manifest; require
   `Manifest.verify()` to return true.
4. Exercise deterministic QC and repair locally, including waveform output.
5. Exercise sanitized failure/recovery behavior with mocks.
6. With owner credentials, upload fixture and canonical manifest through
   `ObjectStorageSink`, then HEAD/list/download/re-hash from B2.
7. Only with explicit live-call acknowledgement, call
   `ElevenLabsSFXProvider` once and persist the resulting asset and manifest to
   B2 before accepting success.
8. Generate the sanitized evidence pack and gate report. Stop at Phase 0.

## Live-call budget

- One successful ElevenLabs SFX call.
- Zero deliberate paid failure calls.
- All requested failure cases use local mocks.
- B2 preflight must pass before ElevenLabs is invoked.
