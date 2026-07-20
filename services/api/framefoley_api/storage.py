"""B2 production storage and path-safe local development adapter."""

from __future__ import annotations

import mimetypes
from pathlib import Path, PurePosixPath
from typing import Protocol, cast

from genblaze_s3 import S3StorageBackend

from framefoley_api.settings import Settings


def validate_object_key(key: str, *, project_id: str | None = None) -> str:
    path = PurePosixPath(key)
    if path.is_absolute() or "\\" in key or ".." in path.parts:
        raise ValueError("unsafe object key")
    if project_id:
        required = f"framefoley/v1/projects/{project_id}/"
        if not key.startswith(required):
            raise ValueError("object key is outside the allowed project prefix")
    elif not key.startswith(
        (
            "framefoley/v1/projects/",
            "framefoley/proof/live/v1/",
            "framefoley/proof/live/v2/",
        )
    ):
        raise ValueError("object key is outside the allowed FRAMEFOLEY prefixes")
    return path.as_posix()


class ObjectStore(Protocol):
    label: str

    def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def list_keys(self, prefix: str) -> list[str]: ...


class LocalObjectStore:
    label = "MOCKED LOCAL STORAGE"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = validate_object_key(key)
        path = (self.root / PurePosixPath(safe)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("object path escaped local storage root")
        return path

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list_keys(self, prefix: str) -> list[str]:
        safe_prefix = validate_object_key(prefix)
        directory = self._path(safe_prefix)
        if directory.is_file():
            return [safe_prefix]
        if not directory.exists():
            return []
        return sorted(
            path.relative_to(self.root).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        )


class B2ObjectStore:
    label = "BACKBLAZE B2"

    def __init__(self, settings: Settings) -> None:
        settings.require_b2()
        self.backend = S3StorageBackend.for_backblaze(
            bucket=cast(str, settings.b2_bucket),
            region=cast(str, settings.b2_region),
            key_id=cast(str, settings.b2_key_id),
            app_key=cast(str, settings.b2_app_key),
            auto_lifecycle=False,
            preflight=True,
        )

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self.backend.put(validate_object_key(key), data, content_type=content_type)

    def get(self, key: str) -> bytes:
        return self.backend.get(validate_object_key(key))

    def exists(self, key: str) -> bool:
        return self.backend.exists(validate_object_key(key))

    def list_keys(self, prefix: str) -> list[str]:
        page = self.backend.list(validate_object_key(prefix))
        return sorted(item.key for item in page.entries)


def content_type_for_key(key: str) -> str:
    guessed, _ = mimetypes.guess_type(key)
    return guessed or "application/octet-stream"


def create_object_store(settings: Settings) -> ObjectStore:
    if settings.storage_mode == "b2":
        return B2ObjectStore(settings)
    return LocalObjectStore(settings.data_dir / "objects")
