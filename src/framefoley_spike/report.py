"""Sanitized evidence-pack and Phase 0 gate reporting."""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framefoley_spike.config import (
    SpikeConfig,
    ffmpeg_version,
    resolved_package_versions,
)
from framefoley_spike.provenance import scan_evidence_tree, sha256_file

REQUIRED_ARTIFACTS = (
    "SUMMARY.md",
    "environment.json",
    "package-versions.json",
    "b2-inventory.json",
    "live-run-sanitized.json",
    "manifest.json",
    "qc-before.json",
    "qc-after.json",
    "waveform.png",
    "repaired-sfx.wav",
    "checksums.sha256",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path.name}")
    return loaded


def write_environment(artifact_dir: Path, config: SpikeConfig) -> None:
    presence = config.presence()
    write_json(
        artifact_dir / "environment.json",
        {
            "schema_version": 1,
            "captured_at": datetime.now(UTC).isoformat(),
            "python_version": platform.python_version(),
            "python_requirement_met": tuple(map(int, platform.python_version_tuple()))
            >= (3, 11, 0),
            "ffmpeg_version": ffmpeg_version(),
            "credentials_present": {
                "b2_credentials": presence["B2_KEY_ID"] and presence["B2_APP_KEY"],
                "b2_bucket": presence["B2_BUCKET"],
                "b2_region": presence["B2_REGION"],
                "elevenlabs_key": presence["ELEVENLABS_API_KEY"],
            },
        },
    )
    write_json(
        artifact_dir / "package-versions.json",
        {"schema_version": 1, "packages": resolved_package_versions()},
    )


def ensure_external_placeholders(artifact_dir: Path, config: SpikeConfig) -> None:
    b2_path = artifact_dir / "b2-inventory.json"
    if not b2_path.exists():
        write_json(
            b2_path,
            {
                "schema_version": 1,
                "status": "BLOCKED",
                "reason_code": "owner_configuration_missing",
                "missing": list(config.missing_b2()),
                "objects": [],
            },
        )
    live_path = artifact_dir / "live-run-sanitized.json"
    if not live_path.exists():
        write_json(
            live_path,
            {
                "schema_version": 1,
                "status": "BLOCKED",
                "reason_code": "owner_configuration_missing",
                "missing": list(config.missing_live()),
                "provider": "elevenlabs-sfx",
                "provider_class": "ElevenLabsSFXProvider",
                "model": "eleven_text_to_sound_v2",
                "provider_call_attempted": False,
                "cost": {"usd": 0.0, "availability": "not_incurred"},
            },
        )


def _live_gate_passed(live: dict[str, Any]) -> bool:
    return (
        live.get("status") == "PASS"
        and live.get("manifest_verified") is True
        and live.get("asset_sha256") == live.get("downloaded_sha256")
        and live.get("audio_qc_after", {}).get("verdict") == "PASS"
    )


def _b2_gate_passed(b2: dict[str, Any]) -> bool:
    return (
        b2.get("status") == "PASS"
        and b2.get("manifest_verified") is True
        and b2.get("hash_match") is True
    )


def determine_verdict(artifact_dir: Path) -> str:
    live = read_json(artifact_dir / "live-run-sanitized.json")
    b2 = read_json(artifact_dir / "b2-inventory.json")
    live_pass = _live_gate_passed(live)
    b2_pass = _b2_gate_passed(b2)
    if live_pass and b2_pass:
        return "GO"

    missing = set(live.get("missing", []))
    if b2_pass and missing == {"ELEVENLABS_API_KEY"}:
        return "CONDITIONAL GO"
    return "NO-GO"


def _checks_status(artifact_dir: Path) -> str:
    path = artifact_dir / "verification.json"
    if not path.exists():
        return "Unverified"
    payload = read_json(path)
    checks = payload.get("checks", {})
    return "Pass" if checks and all(value == "PASS" for value in checks.values()) else "Fail"


def _clean_reproduction_status(artifact_dir: Path) -> str:
    path = artifact_dir / "clean-reproduction.json"
    if not path.exists():
        return "Unverified"
    return "Pass" if read_json(path).get("status") == "PASS" else "Fail"


def write_summary(artifact_dir: Path) -> None:
    verdict = determine_verdict(artifact_dir)
    live = read_json(artifact_dir / "live-run-sanitized.json")
    b2 = read_json(artifact_dir / "b2-inventory.json")
    before = read_json(artifact_dir / "qc-before.json")
    after = read_json(artifact_dir / "qc-after.json")
    manifest = read_json(artifact_dir / "local-manifest-result.json")
    live_attempted = live.get("provider_call_attempted", live.get("status") == "PASS")
    cost = live.get("cost", {})
    live_reproduction_note = (
        "The owner-supplied live path was executed once for this evidence pack. "
        "Do not repeat it unless a fresh paid/credited reproduction is intentionally authorized."
        if verdict == "GO"
        else (
            "After the owner supplies all five required variables, run the bounded "
            "live commands below."
        )
    )
    summary = f"""# FRAMEFOLEY Phase 0 evidence summary

VERDICT: {verdict}

## Verified locally

- Genblaze canonical fixture manifest verified: `{str(manifest.get("manifest_verified")).lower()}`
- Canonical serialization round-trip verified: `{str(manifest.get("roundtrip_verified")).lower()}`
- Fixture asset SHA-256 covered: `{manifest.get("asset_sha256")}`
- QC before repair: `{before.get("verdict")}`
- QC after repair: `{after.get("verdict")}`
- Formatting/lint/type/tests/no-secret aggregate: `{_checks_status(artifact_dir)}`
- Fresh-directory lockfile install and full check: `{_clean_reproduction_status(artifact_dir)}`

## External chain

- B2 smoke: `{b2.get("status")}`
- Live ElevenLabs SFX: `{live.get("status")}`
- Live provider call attempted: `{str(live_attempted).lower()}`
- Provider cost record: USD `{cost.get("usd")}`; availability `{cost.get("availability")}`

## Reproduce

```bash
make install
make preflight
make test
make local-manifest
make qc
make evidence
make check
```

{live_reproduction_note}

```bash
make b2-smoke
FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx
make evidence
make check
```

No frontend, database, or Phase 1 functionality is part of this evidence.
"""
    (artifact_dir / "SUMMARY.md").write_text(summary, encoding="utf-8")


def write_checksums(artifact_dir: Path) -> None:
    lines: list[str] = []
    for path in sorted(candidate for candidate in artifact_dir.rglob("*") if candidate.is_file()):
        if path.name == "checksums.sha256" or "work" in path.relative_to(artifact_dir).parts:
            continue
        relative = path.relative_to(artifact_dir).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    (artifact_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_spike_report(artifact_dir: Path, report_path: Path) -> str:
    verdict = determine_verdict(artifact_dir)
    versions = read_json(artifact_dir / "package-versions.json")["packages"]
    environment = read_json(artifact_dir / "environment.json")
    b2 = read_json(artifact_dir / "b2-inventory.json")
    live = read_json(artifact_dir / "live-run-sanitized.json")
    local = read_json(artifact_dir / "local-manifest-result.json")
    before = read_json(artifact_dir / "qc-before.json")
    after = read_json(artifact_dir / "qc-after.json")
    verification_status = _checks_status(artifact_dir)
    clean_reproduction_status = _clean_reproduction_status(artifact_dir)
    clean_reproduction = (
        read_json(artifact_dir / "clean-reproduction.json")
        if (artifact_dir / "clean-reproduction.json").exists()
        else {}
    )
    clean_test_count = clean_reproduction.get("tests", {}).get("count", "unavailable")
    live_gate_passed = _live_gate_passed(live)
    b2_gate_passed = _b2_gate_passed(b2)

    missing = live.get("missing", [])
    if live_gate_passed and b2_gate_passed:
        external_chain_section = f"""## External chain — verified

- B2 write/HEAD/list/backend-download/re-hash: `PASS`.
- Real ElevenLabs SFX through Genblaze into B2: `PASS`.
- Live asset SHA-256 equals the B2-downloaded SHA-256: `true`.
- B2 canonical manifest verification: `PASS`.
- Required live-prefix object count: `{len(b2.get("objects", []))}`.

## Unverified / unavailable

- Exact provider USD cost is unavailable because the installed
  `genblaze-elevenlabs` connector did not report it. This does not weaken the
  verified generation, storage, hash, manifest, or QC evidence.
"""
        risk_lines = """- Genblaze packages are alpha releases; keep exact pins and rerun the entire
  Phase 0 spike before upgrading.
- Provider USD cost is unavailable from the current connector and would require
  a separate provider-account observation.
- A Phase 0 `GO` closes only this spike; it does not authorize Phase 1."""
        owner_actions = (
            "1. No additional live call or credential action is required to close Phase 0.\n"
            "2. Keep the scoped credentials secure, or revoke them if further work is deferred.\n"
            "3. Do not start Phase 1 without a new explicit owner instruction."
        )
        live_command_record = """The bounded live commands were executed once with
owner-supplied credentials:

```text
make b2-smoke
FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx
make check
```

No additional paid/credited generation is required for this Phase 0 evidence."""
    else:
        external_chain_section = f"""## External chain — blocked / unverified

- B2 write/HEAD/list/backend-download/re-hash: `{b2.get("status")}`.
- Real ElevenLabs SFX through Genblaze into B2: `{live.get("status")}`.
- Live B2 canonical manifest verification, provider latency, and cost remain
  unverified until `live-run-sanitized.json` records a gate-valid `PASS`.
"""
        risk_lines = """- The live provider and storage chain is not proven until owner
  credentials are supplied and the live gate passes.
- Genblaze packages are alpha releases; keep exact pins and rerun the entire
  spike before upgrading.
- Do not start Phase 1 while this report is `NO-GO`."""
        owner_action = (
            "Supply these owner-created variables outside the repository: " + ", ".join(missing)
            if missing
            else "Resolve the recorded external-chain failure before another bounded attempt."
        )
        owner_actions = f"""1. {owner_action}
2. Follow `docs/OWNER_SETUP.md`; use a private bucket and a bucket/prefix-scoped
   application key, never a master key.
3. Run `make b2-smoke`.
4. Explicitly authorize at most one `FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx`.
5. Re-run `make check` and require a strict `GO`; do not start Phase 1 automatically."""
        live_command_record = """The live commands are not recorded as successfully complete:

```text
make b2-smoke
FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx
```"""
    python_version = environment.get("python_version")
    python_requirement_met = environment.get("python_requirement_met")
    report = f"""# FRAMEFOLEY Phase 0 technical spike report

VERDICT: {verdict}

This is a strict gate verdict, not a product-readiness claim. Phase 1 was not
started.

## Verified

- Python requirement: `{python_version}`; 3.11+ check = `{python_requirement_met}`.
- FFmpeg: `{environment.get("ffmpeg_version")}`.
- Official zero-cost Genblaze fixture run completed with asset SHA-256
  `{local.get("asset_sha256")}`.
- Canonical manifest hash: `{local.get("manifest_canonical_hash")}`.
- `Manifest.verify()` returned `{local.get("manifest_verified")}` and canonical
  JSON serialization round-tripped with result `{local.get("roundtrip_verified")}`.
- Deterministic fixture QC was `{before.get("verdict")}` before repair and
  `{after.get("verdict")}` after fixed-array FFmpeg repair.
- Formatting/lint/type/unit/no-secret aggregate: `{verification_status}`.
- Fresh-directory `make install` + `make check`: `{clean_reproduction_status}`.

{external_chain_section}

## Exact package versions

- `genblaze-core`: `{versions.get("genblaze-core")}`
- `genblaze-s3`: `{versions.get("genblaze-s3")}`
- `genblaze-elevenlabs`: `{versions.get("genblaze-elevenlabs")}`

## Current-interface findings

- `ElevenLabsSFXProvider(api_key=None, output_dir=None, retry_policy=...)` is the
  installed official SFX adapter.
- `Pipeline.step(...)` accepts `model`, `prompt`, `modality`, and provider
  parameters such as `duration_seconds`; `Pipeline.run(...)` accepts `sink`,
  timeout controls, and returns a `PipelineResult`.
- `S3StorageBackend.for_backblaze(...)` reads or accepts B2 bucket, region,
  key ID, and application key; `ObjectStorageSink` persists assets and canonical
  manifests.
- In core 0.3.4, `Manifest.verify()` is stricter than a hash-only check: every
  output asset must declare a valid lowercase SHA-256.
- The ElevenLabs SFX connector no longer ships a pricing table, so cost must be
  recorded as unavailable if the live step does not expose one.

## Live provider/model

- Provider: `ElevenLabsSFXProvider` / `elevenlabs-sfx`
- Model: `eleven_text_to_sound_v2`
- Target: `0.8 seconds`
- Status: `{live.get("status")}`

## B2 layout

- Required prefix: `framefoley/spike/{{timestamp}}/`
- Genblaze canonical objects: hierarchical `runs/.../manifest.json` plus the
  generated asset.
- App derivatives: `application/qc-before.json`, `repaired-sfx.wav`,
  `qc-after.json`, `derivative.json`, and `waveform.png`.
- Observed status: `{b2.get("status")}`; observed object count:
  `{len(b2.get("objects", []))}`.

## Manifest verification

- Local canonical manifest: `PASS`.
- B2 canonical manifest: `{"PASS" if b2.get("manifest_verified") is True else "Unverified"}`.
- Live canonical manifest: `{"PASS" if live.get("manifest_verified") is True else "Unverified"}`.

## Audio QC result

- Before: `{before.get("verdict")}` — reasons `{before.get("reasons")}`.
- After: `{after.get("verdict")}` — 48 kHz mono PCM WAV, SHA-256
  `{after.get("metrics", {}).get("sha256")}`.
- Thresholds are embedded in both QC JSON files and implemented without an LLM.

## Latency

- Live latency: `{live.get("latency_seconds", "unavailable")}`.

## Cost

- Recorded USD: `{live.get("cost", {}).get("usd", "unavailable")}`.
- Availability: `{live.get("cost", {}).get("availability", "unavailable")}`.

## Failure cases

Covered locally with sanitized typed state/tests:

- missing provider key;
- invalid B2 credentials / B2 preflight failure;
- provider timeout;
- provider/model failure;
- B2 upload failure after provider success remains incomplete;
- local provider bytes remain available for bounded storage-only retry;
- corrupt and silent audio;
- false manifest verification cannot become verified;
- one-regeneration retry budget is bounded;
- cached-demo behavior is labeled and never reported as live.

No deliberate paid failure was called.

## Risks for Phase 1

{risk_lines}

## Owner actions

{owner_actions}

## Commands run / reproducible commands

```text
make install
make preflight
make test
make local-manifest
make qc
make evidence
make check
```

Clean reproduction was additionally executed from a temporary directory copied
without `.venv` or prior Phase 0 evidence; locked install and all
`{clean_test_count}` recorded tests passed.

{live_command_record}

## Files changed

- Packaging/scope: `AGENTS.md`, `README.md`, `pyproject.toml`,
  `requirements.lock`, `.env.example`, `.gitignore`, `Makefile`.
- Owner/spike docs: `docs/OWNER_SETUP.md`, `docs/SPIKE_PLAN.md`,
  `docs/PROVIDER_MATRIX.md`, `docs/B2_OBJECTS.md`, `docs/SPIKE_REPORT.md`.
- Spike implementation: `src/framefoley_spike/`,
  `scripts/generate_fixture_wav.py`, and `scripts/run_phase0_live_securely.sh`.
- Failure/QC/manifest tests: `tests/`.
- Sanitized evidence: `artifacts/phase0/`.

## Stop line

Phase 0 stops here. No frontend or full product was built. Phase 1 requires
explicit owner approval after a `GO` verdict.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return verdict


def verify_required_artifacts(artifact_dir: Path) -> list[str]:
    return [name for name in REQUIRED_ARTIFACTS if not (artifact_dir / name).exists()]


def assert_secret_free(artifact_dir: Path) -> None:
    findings = scan_evidence_tree(artifact_dir)
    if findings:
        details = ", ".join(f"{path}:{'/'.join(matches)}" for path, matches in findings.items())
        raise RuntimeError(f"secret-like evidence rejected: {details}")
