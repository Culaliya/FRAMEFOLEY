# Provenance model

## Purpose and limit

FRAMEFOLEY records a reproducible history of how each sound moved through the
system. Provenance is not a copyright/license warranty, a creativity score, or
a replacement for provider-plan and jurisdiction review.

## Candidate record

Every candidate records, when applicable:

- event ID/title/timestamp and candidate variant;
- source label: `LIVE`, `CACHED DEMO`, or `MOCKED`, plus the project-level
  `LIVE EVIDENCE REPLAY` label when recorded LIVE bytes are opened again;
- full deterministic prompt and bounded parameters;
- provider and model;
- Genblaze run ID and retry parent run ID;
- start/end timestamps and measured application latency;
- provider-reported cost, or an explicit unavailable value;
- canonical manifest object key/hash and `Manifest.verify()` result;
- B2 raw object key and original SHA-256;
- QC before/after metrics, reasons, repairs, and derivative SHA-256;
- approval status.

The project-level provenance index embeds the schema-v1 project snapshot and all
candidate records. The human-readable HTML is derived from the same JSON.

## Truth rules

- `manifestVerified=true` is possible only for a live candidate after both the
  in-memory and B2-reloaded canonical manifests return true from
  `Manifest.verify()`.
- A cached demo has an application cache record, never a canonical Genblaze
  manifest, and therefore remains `manifestVerified=false`.
- A LIVE evidence replay preserves the original candidate `sourceLabel=LIVE`,
  canonical hash, asset hash, run lineage, QC, and repairs. Its project record
  separately states two recorded calls and zero calls to open the replay.
- Technical QC is deterministic code. Creative approval is a separate human
  action and never inferred from a pass verdict.
- A repaired derivative retains the original run/hash lineage; repair does not
  alter the canonical manifest or pretend the derivative was provider output.
- Assumptions and external owner settings are labeled `UNVERIFIED` until
  independently captured.

## Copy-safe inspector

The browser provenance download uses the API document rather than signed asset
URLs. Its final serialization removes query/fragment data from HTTP URLs and
redacts fields shaped like tokens, secrets, cookies, or authorization. The UI
exposes project-relative object keys, which are useful for auditing but do not
grant B2 access.

## Hash relationships

```text
provider asset bytes downloaded from B2
  -> asset SHA-256 (must match Genblaze asset record)
  -> canonical manifest hash (Manifest.verify true)

deterministically repaired WAV
  -> QC-after SHA-256
  -> approved WAV/OGG + derivative.json

authoritative render
  -> render SHA-256 + mix-map.json

deterministic ZIP
  -> export SHA-256 + inventory
```
