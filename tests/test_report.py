from __future__ import annotations

from pathlib import Path

from framefoley_spike.report import write_json, write_spike_report, write_summary


def _write_go_artifacts(artifact_dir: Path) -> None:
    write_json(
        artifact_dir / "package-versions.json",
        {
            "packages": {
                "genblaze-core": "0.3.4",
                "genblaze-s3": "0.3.4",
                "genblaze-elevenlabs": "0.3.1",
            }
        },
    )
    write_json(
        artifact_dir / "environment.json",
        {
            "python_version": "3.12.13",
            "python_requirement_met": True,
            "ffmpeg_version": "ffmpeg test version",
        },
    )
    write_json(
        artifact_dir / "b2-inventory.json",
        {
            "status": "PASS",
            "manifest_verified": True,
            "hash_match": True,
            "objects": [{"key": "asset"}, {"key": "manifest"}],
        },
    )
    write_json(
        artifact_dir / "live-run-sanitized.json",
        {
            "status": "PASS",
            "manifest_verified": True,
            "asset_sha256": "a" * 64,
            "downloaded_sha256": "a" * 64,
            "audio_qc_after": {"verdict": "PASS"},
            "provider_call_attempted": True,
            "latency_seconds": 1.25,
            "cost": {"usd": None, "availability": "unavailable"},
        },
    )
    write_json(
        artifact_dir / "local-manifest-result.json",
        {
            "asset_sha256": "b" * 64,
            "manifest_canonical_hash": "c" * 64,
            "manifest_verified": True,
            "roundtrip_verified": True,
        },
    )
    write_json(
        artifact_dir / "qc-before.json",
        {"verdict": "REPAIRABLE", "reasons": ["trim_leading_silence"]},
    )
    write_json(
        artifact_dir / "qc-after.json",
        {"verdict": "PASS", "metrics": {"sha256": "d" * 64}},
    )
    write_json(
        artifact_dir / "verification.json",
        {"checks": {"format": "PASS", "lint": "PASS", "tests": "PASS"}},
    )
    write_json(
        artifact_dir / "clean-reproduction.json",
        {"status": "PASS", "tests": {"count": 27, "status": "PASS"}},
    )


def test_go_report_records_live_chain_as_completed(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    report_path = tmp_path / "SPIKE_REPORT.md"
    _write_go_artifacts(artifact_dir)

    assert write_spike_report(artifact_dir, report_path) == "GO"
    report = report_path.read_text(encoding="utf-8")

    assert "VERDICT: GO" in report
    assert "## External chain — verified" in report
    assert "bounded live commands were executed once" in report
    assert "Live commands were not run" not in report
    assert "not proven until owner credentials" not in report


def test_go_summary_does_not_request_another_live_call(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    _write_go_artifacts(artifact_dir)

    write_summary(artifact_dir)
    summary = (artifact_dir / "SUMMARY.md").read_text(encoding="utf-8")

    assert "VERDICT: GO" in summary
    assert "owner-supplied live path was executed once" in summary
    assert "After the owner supplies" not in summary
