# Failure and recovery evidence

- Readiness retries use bounded exponential backoff for at most 90 seconds.
- A timed-out readiness gate offers retry plus public video/repository fallbacks.
- SSE reconnects once with `Last-Event-ID`, then polls authoritative B2-backed state.
- Generation submission retains its idempotency key and duplicate requests reuse state.
- LIVE proof verification fails closed on missing bytes, checksum mismatch, canonical
  manifest failure, lineage mismatch, non-LIVE relabeling, or deterministic QC mismatch.
- The public browser receives sanitized errors and never receives provider or B2 secrets.
