"""Generate secret-safe final metadata and evidence checksums."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "final"
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "evidence",
    "node_modules",
    "playwright-report",
    "test-results",
}
SKIP_FILES = {
    "AGENTS.md",
    "CODEX_FRAMEFOLEY_PHASE_0_TECHNICAL_SPIKE.md",
    "FRAMEFOLEY_PRODUCT_BLUEPRINT.md",
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _command_version(arguments: list[str]) -> str:
    completed = subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=15)
    return completed.stdout.strip().splitlines()[0]


def _source_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "UNVERIFIED - no source commit"
    return completed.stdout.strip()


def _source_paths() -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return sorted(ROOT.rglob("*"))
    return [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def _source_fingerprint() -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in _source_paths():
        if (
            not path.is_file()
            or path.name in SKIP_FILES
            or any(part in SKIP_PARTS for part in path.parts)
        ):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        count += 1
    return digest.hexdigest(), count


def _video_metadata() -> dict[str, Any]:
    path = EVIDENCE / "video" / "framefoley-demo.mp4"
    if not path.is_file():
        path = EVIDENCE / "video" / "framefoley-demo-raw.webm"
    if not path.is_file():
        return {"status": "UNVERIFIED", "reason": "demo video is missing"}
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    payload = json.loads(completed.stdout)["format"]
    return {
        "status": "CACHED DEMO",
        "filename": path.name,
        "durationSeconds": round(float(payload["duration"]), 3),
        "sizeBytes": int(payload["size"]),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def metadata() -> None:
    fingerprint, source_count = _source_fingerprint()
    python_packages = {
        name: importlib.metadata.version(name)
        for name in (
            "fastapi",
            "genblaze-core",
            "genblaze-elevenlabs",
            "genblaze-s3",
            "httpx",
            "jsonschema",
            "mypy",
            "pillow",
            "pytest",
            "ruff",
            "uvicorn",
        )
    }
    web_package = json.loads((ROOT / "apps" / "web" / "package.json").read_text())
    _write_json(
        EVIDENCE / "PACKAGE_VERSIONS.json",
        {
            "schemaVersion": 1,
            "evidenceLabel": "LOCAL BUILD",
            "python": platform.python_version(),
            "node": _command_version(["node", "--version"]),
            "pnpm": _command_version(["pnpm", "--version"]),
            "ffmpeg": _command_version(["ffmpeg", "-version"]),
            "pythonPackages": python_packages,
            "webDependencies": {
                **web_package["dependencies"],
                **web_package["devDependencies"],
            },
            "requirementsLockSha256": hashlib.sha256(
                (ROOT / "requirements.lock").read_bytes()
            ).hexdigest(),
            "pnpmLockSha256": hashlib.sha256((ROOT / "pnpm-lock.yaml").read_bytes()).hexdigest(),
            "sourceCommit": _source_commit(),
            "sourceTreeSha256": fingerprint,
            "sourceTreeFileCount": source_count,
            "video": _video_metadata(),
            "screenshotCount": len(list((EVIDENCE / "screenshots").glob("*.png"))),
        },
    )
    placeholders = {
        "B2_OBJECT_MAP.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "reason": "Phase 1 final-version live gate has not completed in this pack.",
            "phase0Reference": "artifacts/phase0/b2-inventory.json",
        },
        "LIVE_CALLS_SANITIZED.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "providerCallCount": 0,
            "reason": "Phase 1 final-version live gate has not completed in this pack.",
        },
        "MANIFEST_VERIFICATION.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "allReadyLiveCandidatesVerified": False,
            "reason": "Phase 1 final-version live gate has not completed in this pack.",
        },
    }
    for name, payload in placeholders.items():
        path = EVIDENCE / name
        if not path.exists():
            _write_json(path, payload)


def checksums() -> None:
    output = EVIDENCE / "checksums.sha256"
    records: list[str] = []
    for path in sorted(EVIDENCE.rglob("*")):
        if not path.is_file() or path == output:
            continue
        relative = path.relative_to(EVIDENCE).as_posix()
        records.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    output.write_text("\n".join(records) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("metadata", "checksums"))
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.command == "metadata":
        metadata()
    else:
        checksums()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
