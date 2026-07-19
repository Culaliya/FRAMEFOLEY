from __future__ import annotations

import pytest

from framefoley_spike.config import ConfigError, SpikeConfig, preflight_lines


def test_missing_environment_names_fail_without_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("B2_KEY_ID", "B2_APP_KEY", "B2_BUCKET", "B2_REGION", "ELEVENLABS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    config = SpikeConfig.from_env()
    with pytest.raises(ConfigError) as captured:
        config.require_live()
    message = str(captured.value)
    assert "B2_KEY_ID" in message
    assert "ELEVENLABS_API_KEY" in message
    assert "None" not in message


def test_preflight_prints_presence_not_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    secrets = {
        "B2_KEY_ID": "key-id-do-not-print",
        "B2_APP_KEY": "b2-secret-do-not-print",
        "B2_BUCKET": "bucket-do-not-print",
        "B2_REGION": "region-do-not-print",
        "ELEVENLABS_API_KEY": "eleven-secret-do-not-print",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    output = "\n".join(preflight_lines(SpikeConfig.from_env()))
    assert "B2 credentials present: yes" in output
    assert "ElevenLabs key present: yes" in output
    assert all(value not in output for value in secrets.values())
