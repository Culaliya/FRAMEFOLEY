# Public deployment evidence

Evidence label: **LIVE PUBLIC DEPLOYMENT / CACHED DEMO PRODUCT FLOW**  
Verified: 2026-07-19 (Asia/Taipei)

## Public surfaces

- App: <https://framefoley-culaliya.onrender.com>
- API readiness: <https://framefoley-api-culaliya.onrender.com/readyz>
- Repository: <https://github.com/Culaliya/FRAMEFOLEY>
- Demo video:
  <https://raw.githubusercontent.com/Culaliya/FRAMEFOLEY/main/evidence/final/video/framefoley-demo.mp4>
- Deployed source commit:
  `4a4d994eeaa07507d4da8189b92ac2f14c4ba586`
- Host: Render Docker Free, Oregon (US West)

The API and web Docker builds both reached Render's live state at the deployed
commit. No dashboard credential, service secret, environment value, project
token, signed asset URL, or account identity is copied into this record.

## Public probes

```text
GET web /       200 text/html; charset=utf-8  (5 of 5 probes)
GET API /healthz  200 {status: ok, service: framefoley-api, version: 1.0.0}
GET API /readyz   200 {status: ready, generationMode: demo, storage: BACKBLAZE B2}
POST /v1/projects/demo  201 (token presence checked, value never printed)
```

The temporary response used to confirm token presence was deleted immediately.

## Public browser flow

Anonymous project: `prj_5675acd34fbcebc5`

1. JELLY RELAY source project created and source objects stored.
2. Three default cues locked and recovered from B2 on subsequent page loads.
3. Six explicitly labeled **CACHED DEMO** candidates completed deterministic
   QC/repair and reached `READY`.
4. Three first-variant candidates received explicit human approval.
5. Server-side fixed-array FFmpeg render completed with `B2 STORED`.
6. Deterministic export completed with `B2 OBJECT READY`.
7. Provenance loaded six candidate records and reported
   `STORAGE RECORD — BACKBLAZE B2`.
8. No browser page or console error was observed.

Sanitized result identity:

```text
mix SHA-256: 1607371c75def8581f5bbbd49663c077064b9e01e6f9ddeab1bc478484402f2b
ZIP SHA-256: aee6610066b5f2db709b546b19fa09b88bb3d6c6dbde3f3d6587cfcafd291b6d
ZIP inventory: 23 files / 473.3 KB
provenance records: 6
human approvals: 3 / 3
cached candidates ready: 6 / 6
```

## Truth boundary

- This browser flow proves the production API, Docker images, CORS path,
  private B2 persistence, deterministic cached-demo QC, approvals, render,
  export, and provenance surfaces work together.
- It made **zero** ElevenLabs calls. Public live generation is intentionally
  disabled and the provider key is intentionally absent from the public host.
- It does not relabel cached assets as LIVE or cached manifests as canonical.
- The separate `LIVE_CALLS_SANITIZED.json`, `B2_OBJECT_MAP.json`, and
  `MANIFEST_VERIFICATION.json` prove the explicitly authorized final-version
  Genblaze/ElevenLabs live gate.
- Render Free can cold-start after inactivity. Full judging-window availability
  remains a future-state owner check.
- B2 lifecycle and ElevenLabs spend/plan controls remain owner-console
  **UNVERIFIED** settings.
