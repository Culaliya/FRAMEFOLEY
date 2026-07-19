from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from framefoley_api.contracts import validate_project_document
from framefoley_api.errors import PublicError
from framefoley_api.models import (
    FrameFoleyProject,
    ProjectPhase,
    ProjectState,
    SoundEvent,
    StyleProfile,
)
from framefoley_api.prompting import build_prompt, normalize_custom_text
from framefoley_api.security import TokenSigner


def test_hmac_tokens_are_scoped_expiring_and_tamper_evident() -> None:
    signer = TokenSigner.from_secret("unit-test-hmac-secret")
    expires = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = signer.project_token("prj_123456789abc", expires)
    signer.verify_project_token(token, "prj_123456789abc")
    with pytest.raises(PublicError, match="cannot access"):
        signer.verify_project_token(token, "prj_abcdef123456")
    with pytest.raises(PublicError, match="invalid or expired"):
        signer.verify_project_token(
            token[:-1] + ("a" if token[-1] != "a" else "b"), "prj_123456789abc"
        )


def test_prompt_builder_is_bounded_and_rejects_control_text() -> None:
    event = SoundEvent(
        id="evt_12345678",
        slug="small-hit",
        title="Small hit",
        type="impact",
        timestamp_seconds=1.2,
        target_duration_seconds=0.5,
        intensity="soft",
        material_note="felt on glass",
    )
    style = StyleProfile(
        id="lunar_arcade",
        title="LUNAR ARCADE",
        prompt_prefix="Luminous, tactile, playful, slightly glassy.",
    )
    prompt = build_prompt(event, style, "clean")
    assert "Sound effect only. No speech. No music." in prompt
    assert "Clean, compact, readable, minimal tail." in prompt
    assert build_prompt(event, style, "clean") == prompt
    with pytest.raises(PublicError, match="control"):
        normalize_custom_text("hidden\u0000text")


def test_project_contract_rejects_unversioned_or_extra_data() -> None:
    now = datetime.now(UTC)
    project = FrameFoleyProject(
        id="prj_123456789abc",
        slug="contract-check",
        title="Contract check",
        state=ProjectState.CREATED,
        phase=ProjectPhase.SOURCE,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        style=StyleProfile(
            id="lunar_arcade",
            title="LUNAR ARCADE",
            prompt_prefix="Luminous and tactile.",
        ),
        generation_mode="demo",
        retry_budget_remaining=2,
    )
    document = project.model_dump(mode="json", by_alias=True, exclude_none=True)
    validate_project_document(document)
    document["unexpected"] = True
    with pytest.raises(PublicError, match="schema validation"):
        validate_project_document(document)
