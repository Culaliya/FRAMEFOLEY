# B2 object layout — Phase 0

Every live run uses this required root:

```text
framefoley/spike/{UTC_TIMESTAMP}/
```

Genblaze hierarchical storage owns the canonical run subtree:

```text
framefoley/spike/{UTC_TIMESTAMP}/runs/{DATE}/{RUN_ID}/
  manifest.json
  ... generated asset object(s) ...
```

Application-level deterministic derivatives are separate and never rewrite the
canonical Genblaze manifest:

```text
framefoley/spike/{UTC_TIMESTAMP}/application/
  qc-before.json
  repaired-sfx.wav
  qc-after.json
  derivative.json
  waveform.png
```

The evidence command records the exact observed keys, sizes, MIME types,
timestamps, and hashes in `artifacts/phase0/b2-inventory.json`. Presigned query
parameters are never persisted.
