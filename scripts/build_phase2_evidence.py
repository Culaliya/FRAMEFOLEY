"""Build and seal the secret-safe FRAMEFOLEY Phase 2 evidence pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framefoley_spike.provenance import sanitize_text

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "phase2"
STARTING_COMMIT = "e5ed7653c1c9076d99e0460677bb042fa45140b0"
WEB_URL = "https://framefoley-culaliya.onrender.com"
API_URL = "https://framefoley-api-culaliya.onrender.com"
REPOSITORY_URL = "https://github.com/Culaliya/FRAMEFOLEY"
SENSITIVE_ENV_NAMES = {
    "B2_KEY_ID",
    "B2_APP_KEY",
    "B2_BUCKET",
    "B2_REGION",
    "ELEVENLABS_API_KEY",
    "FRAMEFOLEY_HMAC_SECRET",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, indent=2, sort_keys=True))


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip()


def _safe_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in SENSITIVE_ENV_NAMES}


def _safe_output(output: str) -> list[str]:
    interesting = re.compile(
        r"(?:passed|failed|skipped|success|checks? passed|secret scan|error|built|compiled|routes)",
        re.IGNORECASE,
    )
    lines: list[str] = []
    for raw in output.splitlines():
        line = sanitize_text(raw.replace(str(ROOT), "<repo>"))
        if interesting.search(line) and len(line) <= 300:
            lines.append(line)
    return lines[-24:]


def _run_gate(command: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    output = completed.stdout + "\n" + completed.stderr
    return {
        "command": " ".join(command),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exitCode": completed.returncode,
        "durationSeconds": round(time.monotonic() - started, 3),
        "safeOutput": _safe_output(output),
    }


def record_gates() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    commands = [
        ["make", "check"],
        ["make", "browser-test"],
        ["make", "phase2-proof-test"],
        ["make", "secret-scan"],
    ]
    results = [_run_gate(command) for command in commands]
    payload = {
        "schemaVersion": 1,
        "evidenceLabel": "OWNER-VERIFIED",
        "recordedAt": datetime.now(UTC).isoformat(),
        "sourceCommit": _commit(),
        "results": results,
        "allPassed": all(result["status"] == "PASS" for result in results),
    }
    _write_json(EVIDENCE / "GATE_RESULTS_SANITIZED.json", payload)
    lines = [
        "FRAMEFOLEY Phase 2 required gate results",
        f"Recorded: {payload['recordedAt']}",
        f"Source commit: {payload['sourceCommit']}",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"$ {result['command']}",
                f"{result['status']} (exit {result['exitCode']}, {result['durationSeconds']}s)",
                *[str(item) for item in result["safeOutput"]],
                "",
            ]
        )
    _write(EVIDENCE / "TEST_RESULTS.txt", "\n".join(lines))
    return 0 if payload["allPassed"] else 1


def record_clean_install() -> int:
    completed_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    if completed_status.stdout.strip():
        raise RuntimeError("clean-install evidence requires a clean committed source tree")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="framefoley-phase2-clean-") as temporary:
        clone = Path(temporary) / "FRAMEFOLEY"
        cloned = subprocess.run(
            ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(clone)],
            cwd=ROOT,
            env=_safe_environment(),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if cloned.returncode == 0:
            installed = subprocess.run(
                ["make", "install"],
                cwd=clone,
                env=_safe_environment(),
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
        else:
            installed = cloned
        safe_lines = _safe_output(installed.stdout + "\n" + installed.stderr)
    passed = installed.returncode == 0
    payload = {
        "schemaVersion": 1,
        "evidenceLabel": "OWNER-VERIFIED",
        "recordedAt": datetime.now(UTC).isoformat(),
        "sourceCommit": _commit(),
        "command": "git clone --no-hardlinks <repo> <temporary>/FRAMEFOLEY && make install",
        "status": "PASS" if passed else "FAIL",
        "exitCode": installed.returncode,
        "durationSeconds": round(time.monotonic() - started, 3),
        "lockedPythonDependencies": "requirements.lock --require-hashes",
        "lockedWebDependencies": "pnpm install --frozen-lockfile",
        "safeOutput": safe_lines,
    }
    _write_json(EVIDENCE / "CLEAN_BUILD_RESULT_SANITIZED.json", payload)
    _write(
        EVIDENCE / "CLEAN_BUILD.md",
        "\n".join(
            [
                "# Clean-clone install",
                "",
                f"Evidence label: **{payload['evidenceLabel']}**",
                f"Status: **{payload['status']}**",
                f"Source commit: `{payload['sourceCommit']}`",
                "",
                "A temporary no-hardlinks clone ran `make install`. Python used",
                "`requirements.lock --require-hashes`; pnpm used `--frozen-lockfile`.",
                "The temporary checkout and its dependency cache were not added to evidence.",
            ]
        ),
    )
    return 0 if passed else 1


def _video_metadata() -> dict[str, Any]:
    video = EVIDENCE / "video" / "framefoley-phase2-demo.mp4"
    captions = EVIDENCE / "video" / "framefoley-phase2-demo-captions.vtt"
    if not video.is_file() or not captions.is_file():
        return {"status": "UNVERIFIED", "reason": "Phase 2 master or WebVTT is missing"}
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    probe = json.loads(completed.stdout)
    streams = probe.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    subtitle_streams = [stream for stream in streams if stream.get("codec_type") == "subtitle"]
    duration = round(float(probe["format"]["duration"]), 3)
    passed = (
        isinstance(video_stream, dict)
        and video_stream.get("width") == 1920
        and video_stream.get("height") == 1080
        and 165 <= duration <= 178
        and bool(subtitle_streams)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "filename": video.name,
        "durationSeconds": duration,
        "width": video_stream.get("width") if isinstance(video_stream, dict) else None,
        "height": video_stream.get("height") if isinstance(video_stream, dict) else None,
        "subtitleTrackCount": len(subtitle_streams),
        "sidecarWebVtt": captions.name,
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
    }


def _ensure_placeholders() -> None:
    placeholders: dict[str, object] = {
        "CAPABILITIES_SANITIZED.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "reason": "public capability verification has not completed",
        },
        "LIVE_PROOF_INDEX_SANITIZED.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "reason": "immutable B2 proof publication has not completed",
        },
        "LIVE_PROOF_VERIFICATION.json": {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "reason": "immutable B2 proof verification has not completed",
            "providerCallsDuringReplay": 0,
        },
    }
    for name, payload in placeholders.items():
        path = EVIDENCE / name
        if not path.exists():
            _write_json(path, payload)


def _checksums() -> None:
    output = EVIDENCE / "checksums.sha256"
    records: list[str] = []
    for path in sorted(EVIDENCE.rglob("*")):
        if not path.is_file() or path == output:
            continue
        relative = path.relative_to(EVIDENCE).as_posix()
        records.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    _write(output, "\n".join(records))


def assemble() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "screenshots").mkdir(exist_ok=True)
    (EVIDENCE / "video").mkdir(exist_ok=True)
    _ensure_placeholders()
    commit = _commit()
    public = _load_json(EVIDENCE / "PUBLIC_VERIFICATION_SANITIZED.json")
    proof = _load_json(EVIDENCE / "LIVE_PROOF_VERIFICATION.json")
    gates = _load_json(EVIDENCE / "GATE_RESULTS_SANITIZED.json")
    clean = _load_json(EVIDENCE / "CLEAN_BUILD_RESULT_SANITIZED.json")
    video = _video_metadata()
    deployed_commit = "UNVERIFIED"
    if public:
        public_api = public.get("publicApi")
        if isinstance(public_api, dict):
            deployed_commit = str(public_api.get("deployedCommit", "UNVERIFIED"))
    _write(
        EVIDENCE / "STARTING_AND_FINAL_COMMITS.md",
        "\n".join(
            [
                "# Starting and final commits",
                "",
                f"- Phase 2 starting commit: `{STARTING_COMMIT}`",
                f"- Current sealed source commit: `{commit}`",
                f"- Public API reported deployed commit: `{deployed_commit}`",
                "",
                "The final and deployed values match only when public verification reports the",
                "same 40-character commit. An unreported host value remains `UNVERIFIED`.",
            ]
        ),
    )
    proof_status = proof.get("evidenceLabel", "UNVERIFIED") if proof else "UNVERIFIED"
    public_status = public.get("evidenceLabel", "UNVERIFIED") if public else "UNVERIFIED"
    gate_status = "PASS" if gates and gates.get("allPassed") is True else "UNVERIFIED"
    clean_status = clean.get("status", "UNVERIFIED") if clean else "UNVERIFIED"
    _write(
        EVIDENCE / "SUMMARY.md",
        "\n".join(
            [
                "# FRAMEFOLEY Phase 2 evidence summary",
                "",
                "Evidence labels are literal: `LIVE`, `LIVE EVIDENCE REPLAY`,",
                "`CACHED DEMO`, `MOCKED`, `OWNER-VERIFIED`, and `UNVERIFIED`.",
                "",
                f"- Required automated gates: **{gate_status}**",
                f"- Clean-clone install: **{clean_status}**",
                f"- Immutable B2 proof: **{proof_status}**",
                f"- Public verification: **{public_status}**",
                f"- Competition video: **{video['status']}**",
                f"- Source commit: `{commit}`",
                "",
                "The public CACHED DEMO makes no provider call. LIVE EVIDENCE REPLAY",
                "contains two outputs from the authorized recorded LIVE gate; opening it",
                "makes zero provider calls. Human approval remains the creative authority.",
            ]
        ),
    )
    _write(
        EVIDENCE / "PUBLIC_DEPLOYMENT.md",
        "\n".join(
            [
                "# Public deployment",
                "",
                f"- App: <{WEB_URL}>",
                f"- API: <{API_URL}>",
                f"- Repository: <{REPOSITORY_URL}>",
                f"- Public verification: **{public_status}**",
                f"- Deployed commit reported by API: `{deployed_commit}`",
                "",
                "The verification record contains no project token, authorization header,",
                "cookie, signed query string, B2 identifier, provider credential, or account",
                "identity. The final video host remains an owner-only check until logged-out",
                "playback has been confirmed.",
            ]
        ),
    )
    if not (EVIDENCE / "OWNER_CHECKS.md").exists():
        _write(
            EVIDENCE / "OWNER_CHECKS.md",
            """# Owner checks

Evidence label: **UNVERIFIED**

- [ ] B2 bucket confirmed private.
- [ ] B2 key confirmed bucket-scoped and least-privilege.
- [ ] Dependency and asset licenses accepted.
- [ ] Final YouTube/Vimeo video plays logged out.
- [ ] App will remain available through judging.

Prudent but non-blocking in zero-spend public mode: ElevenLabs spend cap,
edge/IP rate limit, B2 lifecycle, and an external uptime monitor. Do not mark
them active without evidence.
""",
        )
    _write(
        EVIDENCE / "FAILURE_RECOVERY.md",
        """# Failure and recovery evidence

- Readiness retries use bounded exponential backoff for at most 90 seconds.
- A timed-out readiness gate offers retry plus public video/repository fallbacks.
- SSE reconnects once with `Last-Event-ID`, then polls authoritative B2-backed state.
- Generation submission retains its idempotency key and duplicate requests reuse state.
- LIVE proof verification fails closed on missing bytes, checksum mismatch, canonical
  manifest failure, lineage mismatch, non-LIVE relabeling, or deterministic QC mismatch.
- The public browser receives sanitized errors and never receives provider or B2 secrets.
""",
    )
    _write(
        EVIDENCE / "COPY_CONSISTENCY.md",
        """# Copy consistency

Automated tests scan public UI and submission copy for contradictory labels.
The public vocabulary is `CACHED DEMO`, `LIVE EVIDENCE REPLAY`, and `LIVE`.
`MOCKED` is limited to tests/local development. Public copy does not call a
replay current live generation, call LIVE bytes cached, show PHASE 1, or expose
an active upload path when the capability contract says it cannot complete.
""",
    )
    _write(
        EVIDENCE / "SECURITY_SCAN.md",
        "\n".join(
            [
                "# Security scan",
                "",
                f"Required gate record: **{gate_status}**",
                "",
                "`make secret-scan` fails closed across source and evidence while keeping",
                "matched values silent. Final status is authoritative only when the gate",
                "record and post-assembly secret scan both pass.",
            ]
        ),
    )
    _write_json(EVIDENCE / "VIDEO_METADATA_SANITIZED.json", video)
    _checksums()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("assemble", "record-gates", "record-clean-install"),
        nargs="?",
        default="assemble",
    )
    args = parser.parse_args()
    if args.command == "record-gates":
        return record_gates()
    if args.command == "record-clean-install":
        return record_clean_install()
    return assemble()


if __name__ == "__main__":
    raise SystemExit(main())
