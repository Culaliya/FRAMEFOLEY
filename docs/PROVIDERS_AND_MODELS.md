# Providers and models

## Competition production path

| Role | Package / class | Exact version or model | Status |
| --- | --- | --- | --- |
| Orchestration | `genblaze-core` / `Pipeline` | 0.3.4 | Phase 0 LIVE verified; used by Phase 1 |
| Durable sink | `genblaze-core` / `ObjectStorageSink` | 0.3.4 | Phase 0 LIVE verified; used by Phase 1 |
| B2 backend | `genblaze-s3` / `S3StorageBackend.for_backblaze` | 0.3.4 | Phase 0 LIVE verified; used by Phase 1 |
| SFX provider | `genblaze-elevenlabs` / `ElevenLabsSFXProvider` | 0.3.1 | Only live provider |
| SFX model | ElevenLabs | `eleven_text_to_sound_v2` | Only live model |
| Test provider | `genblaze_core.testing.MockProvider` | bundled with core 0.3.4 | MOCKED tests only |
| Demo source | FRAMEFOLEY deterministic cache | `deterministic-original-v1` | CACHED DEMO only |

There is no second provider, automatic failover, TTS, dialogue, or music model.

## Provider values retained

The app retains provider/model, parameters, full prompt, run ID, parent run ID,
timestamps, asset SHA-256, canonical manifest hash, and provider-reported cost.
The current connector can return no USD cost; `null`/unavailable is honest and
must not be converted into `$0.00` or a spend-cap claim.

## Upgrade policy

These are alpha Genblaze packages. Any upgrade requires a new interface
inspection, exact re-pin, B2 write/read/re-hash, live manifest verification,
failure-path tests, and a clean evidence pack before deployment. Semver range
upgrades are intentionally not used.

## Rights note

Provider/model disclosure does not itself grant rights. The owner must confirm
the active ElevenLabs plan and terms for the intended submission/use. See
`ASSET_PROVENANCE.md` and `OWNER_CHECKLIST.md`.
