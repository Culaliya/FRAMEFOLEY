# Genblaze usage

## Exact pinned interface

Phase 1 reuses the Phase 0 verified package interface without guessing names:

```text
genblaze-core==0.3.4
genblaze-s3==0.3.4
genblaze-elevenlabs==0.3.1
```

The live service constructs:

```text
ElevenLabsSFXProvider(
  api_key=server_secret,
  output_dir=temporary_directory,
  retry_policy=RetryPolicy(max_attempts=1, jitter="none")
)

Pipeline("framefoley-phase1-sfx", project_id=...)
  .step(
    provider,
    model="eleven_text_to_sound_v2",
    prompt=deterministic_prompt,
    modality=Modality.AUDIO,
    duration_seconds=bounded_target
  )
  .run(
    sink=ObjectStorageSink(...),
    timeout=45,
    pipeline_timeout=60,
    max_retries=0,
    raise_on_failure=True
  )
```

Genblaze is the only live generative-audio path. The application does not call
the ElevenLabs SDK directly around it and does not synthesize a replacement
manifest.

## Verification sequence

For every live candidate, the application:

1. increments the project call counter before the external request;
2. runs Genblaze with no hidden provider/pipeline retry;
3. waits for `ObjectStorageSink` to finish B2 persistence;
4. requires `result.manifest.verify()` to return `true`;
5. resolves the asset and manifest to the private project prefix;
6. downloads the B2 asset and compares SHA-256 with the Genblaze asset record;
7. reloads the canonical manifest from B2 and requires `Manifest.verify()` again;
8. records run ID, parent run, provider/model, parameters, timestamps, latency,
   cost when reported, hashes, and object keys;
9. runs deterministic QC and derivative generation.

Only after both manifest checks and B2 re-hash can `manifestVerified` be true.

## Retry lineage

There are two initial independent candidates per event. A candidate receives at
most one visible retry, and only for deterministic regenerate verdicts such as
silent, corrupt, or grossly wrong duration. The retry stores `parentRunId`,
changes the deterministic retry instruction, and consumes the configurable
project retry budget. The hard project ceiling is 12 live calls.

## Modes and labels

- `live`: Genblaze + ElevenLabs + B2; candidate label `LIVE`.
- `demo`: original bundled assets copied through the same app QC/export path;
  candidate label `CACHED DEMO`, `manifestVerified=false`.
- `disabled`: generation refuses safely; the app can still explain/view a demo.

Mock providers exist only in integration tests and are labeled `MOCKED` in
evidence. They cannot satisfy the final live gate.
