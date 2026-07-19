"""Hashing, derivative lineage, URL redaction, and evidence leak checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(authorization|xi-api-key|b2_app_key|elevenlabs_api_key)\b\s*[:=]\s*[^\s,;]+"
)
_TOKEN_PATTERN = re.compile(r"\b(?:sk|xi)_[A-Za-z0-9_-]{16,}\b")

_EVIDENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("presigned_query", re.compile(r"(?i)X-Amz-(?:Signature|Credential|Security-Token)=")),
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(?:authorization|xi-api-key|b2_app_key|elevenlabs_api_key)\b"
            r"\s*[:=]\s*(?!\[?redacted\]?)[^\s,;]{8,}"
        ),
    ),
    ("provider_token", _TOKEN_PATTERN),
    ("local_home_path", re.compile(r"/Users/[^/\s]+/")),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_url(url: str) -> str:
    """Strip credentials, query, and fragment from a URL."""

    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if parsed.port is not None:
        hostname = f"{hostname}:{parsed.port}"
    return urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))


def sanitize_text(text: str) -> str:
    """Remove common credential and signed-URL shapes from an error string."""

    redacted = _URL_PATTERN.sub(lambda match: redact_url(match.group(0)), text)
    redacted = _ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return _TOKEN_PATTERN.sub("[REDACTED]", redacted)


@dataclass(frozen=True)
class DerivativeRecord:
    schema_version: int
    original_run_id: str
    original_asset_id: str
    original_asset_sha256: str
    canonical_manifest_hash: str
    derivative_sha256: str
    repairs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_text_for_secrets(text: str) -> list[str]:
    return [name for name, pattern in _EVIDENCE_PATTERNS if pattern.search(text)]


def scan_evidence_tree(root: Path) -> dict[str, list[str]]:
    """Return relative evidence paths with secret-like findings."""

    findings: dict[str, list[str]] = {}
    if not root.exists():
        return findings
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path.suffix.lower() in {".wav", ".mp3", ".ogg", ".png"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = scan_text_for_secrets(text)
        if matches:
            findings[path.relative_to(root).as_posix()] = matches
    return findings
