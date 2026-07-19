# FRAMEFOLEY Phase 0 technical spike report

VERDICT: GO

This is a strict gate verdict, not a product-readiness claim. Phase 1 was not
started.

## Verified

- Python requirement: `3.12.13`; 3.11+ check = `True`.
- FFmpeg: `ffmpeg version 8.1.1 Copyright (c) 2000-2026 the FFmpeg developers`.
- Official zero-cost Genblaze fixture run completed with asset SHA-256
  `d2dd9e2312ef0a51692aa04047dcf938d72e8767479f3ab2b77fc6c02f03b354`.
- Canonical manifest hash: `d40d9204d9e4fc3710a837c1df9afe816eedb32889e0fd30130b9620c9390452`.
- `Manifest.verify()` returned `True` and canonical
  JSON serialization round-tripped with result `True`.
- Deterministic fixture QC was `REPAIRABLE` before repair and
  `PASS` after fixed-array FFmpeg repair.
- Formatting/lint/type/unit/no-secret aggregate: `Pass`.
- Fresh-directory `make install` + `make check`: `Pass`.

## External chain — verified

- B2 write/HEAD/list/backend-download/re-hash: `PASS`.
- Real ElevenLabs SFX through Genblaze into B2: `PASS`.
- Live asset SHA-256 equals the B2-downloaded SHA-256: `true`.
- B2 canonical manifest verification: `PASS`.
- Required live-prefix object count: `7`.

## Unverified / unavailable

- Exact provider USD cost is unavailable because the installed
  `genblaze-elevenlabs` connector did not report it. This does not weaken the
  verified generation, storage, hash, manifest, or QC evidence.


## Exact package versions

- `genblaze-core`: `0.3.4`
- `genblaze-s3`: `0.3.4`
- `genblaze-elevenlabs`: `0.3.1`

## Current-interface findings

- `ElevenLabsSFXProvider(api_key=None, output_dir=None, retry_policy=...)` is the
  installed official SFX adapter.
- `Pipeline.step(...)` accepts `model`, `prompt`, `modality`, and provider
  parameters such as `duration_seconds`; `Pipeline.run(...)` accepts `sink`,
  timeout controls, and returns a `PipelineResult`.
- `S3StorageBackend.for_backblaze(...)` reads or accepts B2 bucket, region,
  key ID, and application key; `ObjectStorageSink` persists assets and canonical
  manifests.
- In core 0.3.4, `Manifest.verify()` is stricter than a hash-only check: every
  output asset must declare a valid lowercase SHA-256.
- The ElevenLabs SFX connector no longer ships a pricing table, so cost must be
  recorded as unavailable if the live step does not expose one.

## Live provider/model

- Provider: `ElevenLabsSFXProvider` / `elevenlabs-sfx`
- Model: `eleven_text_to_sound_v2`
- Target: `0.8 seconds`
- Status: `PASS`

## B2 layout

- Required prefix: `framefoley/spike/{timestamp}/`
- Genblaze canonical objects: hierarchical `runs/.../manifest.json` plus the
  generated asset.
- App derivatives: `application/qc-before.json`, `repaired-sfx.wav`,
  `qc-after.json`, `derivative.json`, and `waveform.png`.
- Observed status: `PASS`; observed object count:
  `7`.

## Manifest verification

- Local canonical manifest: `PASS`.
- B2 canonical manifest: `PASS`.
- Live canonical manifest: `PASS`.

## Audio QC result

- Before: `REPAIRABLE` — reasons `['trim_leading_silence']`.
- After: `PASS` — 48 kHz mono PCM WAV, SHA-256
  `d397e46964f7cf30801e459895edff2d8f9800fcdd3615a2f4c6d0fd70a02575`.
- Thresholds are embedded in both QC JSON files and implemented without an LLM.

## Latency

- Live latency: `3.855`.

## Cost

- Recorded USD: `None`.
- Availability: `unavailable`.

## Failure cases

Covered locally with sanitized typed state/tests:

- missing provider key;
- invalid B2 credentials / B2 preflight failure;
- provider timeout;
- provider/model failure;
- B2 upload failure after provider success remains incomplete;
- local provider bytes remain available for bounded storage-only retry;
- corrupt and silent audio;
- false manifest verification cannot become verified;
- one-regeneration retry budget is bounded;
- cached-demo behavior is labeled and never reported as live.

No deliberate paid failure was called.

## Risks for Phase 1

- Genblaze packages are alpha releases; keep exact pins and rerun the entire
  Phase 0 spike before upgrading.
- Provider USD cost is unavailable from the current connector and would require
  a separate provider-account observation.
- A Phase 0 `GO` closes only this spike; it does not authorize Phase 1.

## Owner actions

1. No additional live call or credential action is required to close Phase 0.
2. Keep the scoped credentials secure, or revoke them if further work is deferred.
3. Do not start Phase 1 without a new explicit owner instruction.

## Commands run / reproducible commands

```text
make install
make preflight
make test
make local-manifest
make qc
make evidence
make check
```

Clean reproduction was additionally executed from a temporary directory copied
without `.venv` or prior Phase 0 evidence; locked install and all
`27` recorded tests passed.

The bounded live commands were executed once with
owner-supplied credentials:

```text
make b2-smoke
FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx
make check
```

No additional paid/credited generation is required for this Phase 0 evidence.

## Files changed

- Packaging/scope: `AGENTS.md`, `README.md`, `pyproject.toml`,
  `requirements.lock`, `.env.example`, `.gitignore`, `Makefile`.
- Owner/spike docs: `docs/OWNER_SETUP.md`, `docs/SPIKE_PLAN.md`,
  `docs/PROVIDER_MATRIX.md`, `docs/B2_OBJECTS.md`, `docs/SPIKE_REPORT.md`.
- Spike implementation: `src/framefoley_spike/`,
  `scripts/generate_fixture_wav.py`, and `scripts/run_phase0_live_securely.sh`.
- Failure/QC/manifest tests: `tests/`.
- Sanitized evidence: `artifacts/phase0/`.

## Stop line

Phase 0 stops here. No frontend or full product was built. Phase 1 requires
explicit owner approval after a `GO` verdict.
