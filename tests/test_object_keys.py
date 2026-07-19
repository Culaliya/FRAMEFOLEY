from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from framefoley_spike.b2 import safe_object_key, spike_prefix, staged_transfer_file
from framefoley_spike.genblaze_sfx import provider_transfer_dir
from framefoley_spike.provenance import redact_url, sanitize_text


@pytest.mark.parametrize(
    "parts",
    [
        ("framefoley", "../escape"),
        ("framefoley", "/absolute"),
        ("framefoley", "bad\\path"),
        ("other-root", "file.wav"),
    ],
)
def test_object_keys_cannot_escape_framefoley(parts: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        safe_object_key(*parts)


def test_spike_prefix_is_bounded() -> None:
    prefix = spike_prefix("20260718T120000Z")
    assert prefix == "framefoley/spike/20260718T120000Z"


def test_signed_urls_are_redacted() -> None:
    original = "https://s3.example.test/bucket/key.wav?X-Amz-Credential=abc&X-Amz-Signature=secret"
    redacted = redact_url(original)
    assert redacted == "https://s3.example.test/bucket/key.wav"
    assert "Signature" not in sanitize_text(f"download={original}")
    assert "secret" not in sanitize_text(f"download={original}")


def test_local_assets_are_staged_under_genblaze_allowed_temp_root(tmp_path: Path) -> None:
    source = tmp_path / "fixture.wav"
    source.write_bytes(b"deterministic fixture")

    with staged_transfer_file(source) as staged:
        assert staged.read_bytes() == source.read_bytes()
        assert staged.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())


def test_provider_output_uses_genblaze_allowed_temp_root() -> None:
    assert provider_transfer_dir().is_relative_to(Path(tempfile.gettempdir()).resolve())
