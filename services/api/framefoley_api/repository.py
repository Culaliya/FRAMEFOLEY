"""B2/local object-backed project persistence and recovery."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from genblaze_core.exceptions import StorageError
from genblaze_core.storage.errors import StorageErrorCode
from pydantic import ValidationError

from framefoley_api.contracts import validate_project_document
from framefoley_api.errors import PublicError
from framefoley_api.models import FrameFoleyProject
from framefoley_api.storage import ObjectStore, validate_object_key

logger = logging.getLogger("framefoley.repository")


def project_prefix(project_id: str) -> str:
    return f"framefoley/v1/projects/{project_id}/"


def project_key(project_id: str) -> str:
    return f"{project_prefix(project_id)}project.json"


class ProjectRepository:
    def __init__(self, store: ObjectStore) -> None:
        self.store = store

    def save(self, project: FrameFoleyProject) -> None:
        project.updated_at = datetime.now(UTC)
        payload = project.model_dump(mode="json", by_alias=True, exclude_none=True)
        validate_project_document(payload)
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.store.put(project_key(project.id), encoded, content_type="application/json")

    def load(self, project_id: str) -> FrameFoleyProject:
        key = project_key(project_id)
        try:
            encoded = self.store.get(key)
        except FileNotFoundError as exc:
            raise PublicError(
                "PROJECT_NOT_FOUND",
                "Project was not found or has expired.",
                status_code=404,
            ) from exc
        except StorageError as exc:
            logger.warning(
                "project storage read failed code=%s status=%s retriable=%s operation=%s",
                exc.error_code,
                exc.status_code,
                exc.is_retriable,
                exc.operation,
            )
            if exc.error_code == StorageErrorCode.NOT_FOUND:
                raise PublicError(
                    "PROJECT_NOT_FOUND",
                    "Project was not found or has expired.",
                    status_code=404,
                ) from exc
            raise PublicError(
                "PROJECT_STORAGE_UNAVAILABLE",
                "Private project storage is temporarily unavailable.",
                retryable=bool(exc.is_retriable),
                status_code=503,
            ) from exc
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
                raise ValueError("unsupported project schema version")
            validate_project_document(payload)
            return FrameFoleyProject.model_validate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, ValueError) as exc:
            raise PublicError(
                "PROJECT_RECOVERY_FAILED",
                "Stored project state is invalid and cannot be guessed or upgraded automatically.",
                status_code=500,
            ) from exc

    def put_object(self, project_id: str, suffix: str, data: bytes, *, content_type: str) -> str:
        key = validate_object_key(f"{project_prefix(project_id)}{suffix}", project_id=project_id)
        self.store.put(key, data, content_type=content_type)
        return key

    def get_object(self, project_id: str, key: str) -> bytes:
        return self.store.get(validate_object_key(key, project_id=project_id))

    def claim_generation_request(self, project: FrameFoleyProject, idempotency_key: str) -> bool:
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        if digest in project.generation_request_keys:
            return False
        if len(project.generation_request_keys) >= 16:
            project.generation_request_keys.pop(0)
        project.generation_request_keys.append(digest)
        self.save(project)
        return True
