from pathlib import Path

from framefoley_api.settings import Settings


def test_repository_root_can_be_explicitly_pinned(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRAMEFOLEY_REPO_ROOT", str(tmp_path))

    settings = Settings.from_env()

    assert settings.repo_root == tmp_path.resolve()
    assert settings.data_dir == (tmp_path / ".data").resolve()
