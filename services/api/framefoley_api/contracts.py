"""Validation against the repository's versioned JSON Schema source of truth."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from framefoley_api.errors import PublicError


@lru_cache(maxsize=1)
def _project_validator() -> Draft202012Validator:
    repo_root = Path(__file__).resolve().parents[3]
    schema_path = repo_root / "packages" / "contracts" / "schemas" / "framefoley.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_project_document(payload: dict[str, Any]) -> None:
    try:
        _project_validator().validate(payload)
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise PublicError(
            "PROJECT_SCHEMA_INVALID",
            f"Project schema validation failed at {path}: {exc.message}",
            status_code=422,
        ) from exc
