from __future__ import annotations

from pathlib import Path

import pytest

from framefoley_spike.fixture import generate_fixture


@pytest.fixture
def fixture_wav(tmp_path: Path) -> Path:
    return generate_fixture(tmp_path / "fixture.wav")
