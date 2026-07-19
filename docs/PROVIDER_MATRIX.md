# Provider matrix — Phase 0

| Role | Package/class | Version/model | Phase 0 status |
| --- | --- | --- | --- |
| Orchestration | `genblaze-core` / `Pipeline` | 0.3.4 | Installed and locally exercised |
| Storage | `genblaze-s3` / `S3StorageBackend.for_backblaze` | 0.3.4 | Implementation ready; live credentials required |
| Object sink | `genblaze-core` / `ObjectStorageSink` | 0.3.4 | Local contract inspected; B2 run requires credentials |
| Primary live SFX | `genblaze-elevenlabs` / `ElevenLabsSFXProvider` | 0.3.1 / `eleven_text_to_sound_v2` | Implementation ready; owner API key required |
| Local fixture | `genblaze_core.testing.MockProvider` | bundled with core 0.3.4 | Zero-cost canonical manifest path |
| Secondary provider | None | N/A | Explicitly out of scope |

Current interface notes:

- `Pipeline.run()` returns a `PipelineResult` containing `.run` and `.manifest`.
- `ElevenLabsSFXProvider(output_dir=...)` returns local MP3 bytes through its
  official SDK adapter; `duration_seconds` is passed to `Pipeline.step(...)`.
- `ObjectStorageSink` rejects presigned asset URLs in manifests. Durable,
  credential-free B2 URIs remain in provenance; presigned URLs are generated
  only for short-lived reads.
- In core 0.3.4, `Manifest.verify()` checks both the canonical manifest hash and
  valid SHA-256 coverage for every output asset.
