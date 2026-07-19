from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote, unquote, urlsplit

from genblaze_core import (
    Asset,
    AudioMetadata,
    KeyStrategy,
    Manifest,
    Modality,
    ObjectStorageSink,
    Pipeline,
)
from genblaze_core.storage import StorageBackend
from genblaze_core.testing import MockProvider


class MemoryBackend(StorageBackend):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        extra_args: dict[str, Any] | None = None,
    ) -> str:
        del content_type, metadata, extra_args
        self.objects[key] = data if isinstance(data, bytes) else data.read()
        return key

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def exists(self, key: str) -> bool:
        return key in self.objects

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def get_url(self, key: str, *, expires_in: int = 3600) -> str:
        del expires_in
        return self.get_durable_url(key)

    def get_durable_url(self, key: str) -> str:
        return f"memory://framefoley/{quote(key)}"

    def key_from_url(self, url: str) -> str | None:
        parsed = urlsplit(url)
        if parsed.scheme != "memory" or parsed.netloc != "framefoley":
            return None
        return unquote(parsed.path.lstrip("/"))


def test_fake_provider_genblaze_manifest_storage_contract(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[3] / "demo" / "cache" / "raw" / "bubble-pop-clean.wav"
    staged = tmp_path / "candidate.wav"
    staged.write_bytes(source.read_bytes())
    asset = Asset(
        url=staged.resolve().as_uri(),
        media_type="audio/wav",
        size_bytes=staged.stat().st_size,
    )
    asset.duration = 0.62
    asset.audio = AudioMetadata(sample_rate=48_000, channels=1, codec="pcm_s16le")
    provider = MockProvider(name="framefoley-fake-provider", assets=[asset])
    backend = MemoryBackend()
    sink = ObjectStorageSink(
        backend,
        prefix="framefoley/v1/projects/prj_123456789abc/genblaze",
        key_strategy=KeyStrategy.HIERARCHICAL,
        max_upload_workers=1,
    )
    try:
        result = (
            Pipeline("framefoley-test-live-contract", project_id="prj_123456789abc")
            .step(
                provider,
                model="fixture-v1",
                prompt="Bounded deterministic gameplay pop fixture.",
                modality=Modality.AUDIO,
                duration_seconds=0.62,
            )
            .run(
                sink=sink,
                timeout=10,
                pipeline_timeout=15,
                max_retries=0,
                raise_on_failure=True,
                _owns_sink=False,
            )
        )
        assert result.manifest.verify() is True
        stored_asset = result.run.steps[0].assets[0]
        key = backend.key_from_url(stored_asset.url)
        assert key is not None
        assert key.startswith("framefoley/v1/projects/prj_123456789abc/")
        downloaded = backend.get(key)
        assert hashlib.sha256(downloaded).hexdigest() == stored_asset.sha256
        manifest_key = sink.manifest_key_for(result.run)
        stored_manifest = Manifest.model_validate_json(backend.get(manifest_key))
        assert stored_manifest.verify() is True
        assert stored_manifest.canonical_hash == result.manifest.canonical_hash
    finally:
        sink.close()
