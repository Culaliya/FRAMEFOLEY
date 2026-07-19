"""Backblaze B2 object-key policy and Genblaze storage smoke."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, cast

from genblaze_core import (
    Asset,
    AudioMetadata,
    KeyStrategy,
    Manifest,
    Modality,
    ObjectStorageSink,
    Pipeline,
)
from genblaze_core.testing import MockProvider
from genblaze_s3 import S3StorageBackend

from framefoley_spike.config import SpikeConfig
from framefoley_spike.provenance import redact_url, sanitize_text, sha256_bytes, sha256_file

SPIKE_ROOT = "framefoley/spike"


class StorageSpikeError(RuntimeError):
    def __init__(self, stage: str, code: str, message: str) -> None:
        self.stage = stage
        self.code = code
        self.safe_message = sanitize_text(message)
        super().__init__(f"{stage}/{code}: {self.safe_message}")


def utc_prefix_token(now: datetime | None = None) -> str:
    instant = now or datetime.now(UTC)
    return instant.strftime("%Y%m%dT%H%M%SZ")


def safe_object_key(*parts: str) -> str:
    """Build a normalized key that cannot escape `framefoley/`."""

    if not parts:
        raise ValueError("at least one object-key part is required")
    for part in parts:
        candidate = PurePosixPath(part)
        if not part or "\\" in part or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("unsafe object-key part")
    key = PurePosixPath(*parts).as_posix().lstrip("/")
    if not key.startswith("framefoley/"):
        raise ValueError("object key must remain under framefoley/")
    return key


def spike_prefix(token: str | None = None) -> str:
    return safe_object_key(SPIKE_ROOT, token or utc_prefix_token())


def create_backend(config: SpikeConfig) -> S3StorageBackend:
    config.require_b2()
    try:
        return S3StorageBackend.for_backblaze(
            bucket=cast(str, config.b2_bucket),
            region=cast(str, config.b2_region),
            key_id=cast(str, config.b2_key_id),
            app_key=cast(str, config.b2_app_key),
            auto_lifecycle=False,
            preflight=True,
        )
    except Exception as exc:
        raise StorageSpikeError("storage_preflight", "b2_preflight_failed", str(exc)) from exc


@contextmanager
def staged_transfer_file(source: Path) -> Iterator[Path]:
    """Copy a local asset below Genblaze's allowlisted system temp root."""

    with TemporaryDirectory(prefix="framefoley-phase0-") as staging_dir:
        staged = Path(staging_dir) / source.name
        staged.write_bytes(source.read_bytes())
        yield staged


def run_b2_smoke(config: SpikeConfig, fixture: Path) -> tuple[dict[str, Any], str]:
    """Upload a fixture through ObjectStorageSink and read/re-hash it."""

    prefix = spike_prefix()
    backend = create_backend(config)
    sink = ObjectStorageSink(
        backend,
        prefix=prefix,
        key_strategy=KeyStrategy.HIERARCHICAL,
        max_upload_workers=1,
    )
    try:
        source_hash = sha256_file(fixture)
        with staged_transfer_file(fixture) as staged_fixture:
            asset = Asset(
                url=staged_fixture.resolve().as_uri(),
                media_type="audio/wav",
                size_bytes=staged_fixture.stat().st_size,
            )
            asset.duration = 0.6
            asset.audio = AudioMetadata(sample_rate=48_000, channels=1, codec="pcm_s16le")
            provider = MockProvider(name="framefoley-fixture", assets=[asset])
            result = (
                Pipeline("framefoley-phase0-b2-fixture")
                .step(
                    provider,
                    model="fixture-v1",
                    prompt="Original deterministic decaying sine and filtered-noise fixture.",
                    modality=Modality.AUDIO,
                    duration_seconds=0.6,
                )
                .run(
                    sink=sink,
                    timeout=20,
                    pipeline_timeout=30,
                    max_retries=0,
                    raise_on_failure=True,
                    _owns_sink=False,
                )
            )
        if not result.manifest.verify():
            raise StorageSpikeError(
                "manifest", "verification_failed", "stored fixture manifest did not verify"
            )

        stored_asset = result.run.steps[0].assets[0]
        asset_key = backend.key_from_url(stored_asset.url)
        if asset_key is None:
            raise StorageSpikeError(
                "storage", "durable_key_missing", "stored fixture URL could not map to a B2 key"
            )
        manifest_key = sink.manifest_key_for(result.run)
        asset_head = backend.head(asset_key)
        manifest_head = backend.head(manifest_key)
        if asset_head is None or manifest_head is None:
            raise StorageSpikeError(
                "storage", "head_missing", "B2 HEAD did not find the expected asset and manifest"
            )

        downloaded = backend.get(asset_key)
        downloaded_hash = sha256_bytes(downloaded)
        if downloaded_hash != stored_asset.sha256 or downloaded_hash != source_hash:
            raise StorageSpikeError(
                "storage", "download_hash_mismatch", "B2-downloaded fixture SHA-256 mismatch"
            )

        stored_manifest_bytes = backend.get(manifest_key)
        stored_manifest = Manifest.model_validate_json(stored_manifest_bytes)
        if not stored_manifest.verify():
            raise StorageSpikeError(
                "manifest",
                "stored_verification_failed",
                "B2-downloaded canonical manifest did not verify",
            )

        page = backend.list(prefix)
        presigned = backend.presigned_get_url(asset_key, expires_in=300)
        inventory = {
            "schema_version": 1,
            "status": "PASS",
            "operation": "fixture_write_head_list_backend_read_rehash",
            "prefix": f"{prefix}/",
            "run_id": result.run.run_id,
            "manifest_verified": True,
            "manifest_canonical_hash": stored_manifest.canonical_hash,
            "source_sha256": source_hash,
            "downloaded_sha256": downloaded_hash,
            "hash_match": True,
            "presigned_get": {
                "created": True,
                "expires_in_seconds": 300,
                "sanitized_url": redact_url(presigned),
            },
            "objects": [
                {
                    "key": entry.key,
                    "size_bytes": entry.size,
                    "last_modified": entry.last_modified.astimezone(UTC).isoformat(),
                    "etag": entry.etag.strip('"'),
                }
                for entry in page.entries
            ],
            "required_objects": {
                "asset": {
                    "key": asset_key,
                    "size_bytes": asset_head.size,
                    "mime_type": asset_head.content_type,
                    "sha256": downloaded_hash,
                    "last_modified": asset_head.last_modified.astimezone(UTC).isoformat(),
                },
                "manifest": {
                    "key": manifest_key,
                    "size_bytes": manifest_head.size,
                    "mime_type": manifest_head.content_type,
                    "canonical_hash": stored_manifest.canonical_hash,
                    "last_modified": manifest_head.last_modified.astimezone(UTC).isoformat(),
                },
            },
        }
        return inventory, stored_manifest.to_canonical_json()
    finally:
        sink.close()
