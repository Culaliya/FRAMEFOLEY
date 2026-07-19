from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _public_ui_text() -> str:
    paths = sorted((ROOT / "apps" / "web").glob("app/**/*.tsx")) + sorted(
        (ROOT / "apps" / "web" / "components").glob("*.tsx")
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_phase2_public_truth_labels_are_consistent() -> None:
    text = _public_ui_text()
    upper = text.upper()
    assert "PHASE 1" not in upper
    assert "LIVE GENERATION" not in upper
    assert "LIVE GENERATION NOW" not in upper
    assert "CURRENT LIVE RUN" not in upper
    assert "NEWLY GENERATED" not in upper
    assert "CACHED LIVE" not in upper
    assert "CACHED DEMO" in upper
    assert "LIVE EVIDENCE REPLAY" in upper
    assert "HUMAN APPROVAL REMAINS AUTHORITATIVE" in upper


def test_upload_route_is_only_exposed_under_the_server_capability_branch() -> None:
    landing = (ROOT / "apps" / "web" / "components" / "landing-experience.tsx").read_text(
        encoding="utf-8"
    )
    route = 'href="/projects/new?source=upload"'
    assert landing.count(route) == 1
    route_index = landing.index(route)
    capability_index = landing.rfind("capabilities?.customUploadCanComplete", 0, route_index)
    assert capability_index >= 0
    assert route_index - capability_index < 180


def test_replay_copy_always_discloses_zero_new_provider_calls() -> None:
    replay_files = [
        ROOT / "apps" / "web" / "components" / "landing-experience.tsx",
        ROOT / "apps" / "web" / "app" / "projects" / "[id]" / "generate" / "page.tsx",
        ROOT / "apps" / "web" / "app" / "projects" / "[id]" / "audition" / "page.tsx",
        ROOT / "apps" / "web" / "app" / "projects" / "[id]" / "provenance" / "page.tsx",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in replay_files).lower()
    assert "live evidence replay" in text
    assert "zero provider calls" in text or "0 provider calls" in text
    assert "provider calls happened during the recorded live gate" in text


def test_submission_docs_preserve_the_same_public_truth_contract() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "DEVPOST_SUBMISSION.md",
        ROOT / "docs" / "DEMO_SCRIPT.md",
        ROOT / "docs" / "OWNER_CHECKLIST.md",
        ROOT / "docs" / "SECURITY_AND_COST.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    upper = text.upper()
    assert "CACHED DEMO" in upper
    assert "LIVE EVIDENCE REPLAY" in upper
    assert "ZERO NEW PROVIDER CALL" in upper or "ZERO PROVIDER CALL" in upper
    assert "HUMAN APPROVAL REMAINS" in upper
    assert "CUSTOMUPLOADCANCOMPLETE=FALSE" in upper
    assert "ANONYMOUSPROVIDERSPENDENABLED=FALSE" in upper
    assert "CACHED LIVE" not in upper
    assert not re.search(
        r"LIVE EVIDENCE REPLAY.{0,180}(?:FRESH|CURRENT) (?:LIVE )?(?:GENERATION|PROVIDER CALL)",
        upper,
        re.DOTALL,
    )
    devpost = (ROOT / "docs" / "DEVPOST_SUBMISSION.md").read_text(encoding="utf-8").lower()
    assert "multi-provider" not in devpost
    assert "automatic scene understanding" in devpost
