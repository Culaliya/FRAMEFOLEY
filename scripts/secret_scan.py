"""Fail-closed, value-silent source and evidence secret scan."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from framefoley_spike.provenance import scan_evidence_tree

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "playwright-report",
    "test-results",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".env",
    ".example",
    ".html",
    ".js",
    ".json",
    ".lock",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("provider_token", re.compile(r"\b(?:sk|xi)_[A-Za-z0-9_-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    (
        "secret_assignment",
        re.compile(
            r"(?m)^[ \t]*(?:B2_APP_KEY|ELEVENLABS_API_KEY|FRAMEFOLEY_HMAC_SECRET)"
            r"[ \t]*=[ \t]*(?![<\[])[^\s#][^\r\n]{7,}$"
        ),
    ),
)


def _source_findings() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if "evidence" in path.parts or path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for rule, pattern in RULES:
            if pattern.search(text):
                findings.append((path.relative_to(ROOT).as_posix(), rule))
    return findings


def main() -> int:
    source = _source_findings()
    evidence = scan_evidence_tree(ROOT / "evidence")
    if source or evidence:
        print("Secret scan: FAIL", file=sys.stderr)
        for path, rule in source:
            print(f"source finding: {path} ({rule})", file=sys.stderr)
        for path, rules in evidence.items():
            print(f"evidence finding: {path} ({', '.join(rules)})", file=sys.stderr)
        return 1
    print("Secret scan: PASS (source + evidence; values never printed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
