"""Tests for desktop user-data configuration."""

from __future__ import annotations

from config.loader import CLIConfig


def test_cli_config_uses_desktop_user_data_for_sessions(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "backend"
    project_root.mkdir()
    (project_root / "config").mkdir()
    (project_root / "config" / "config.yaml").write_text(
        "sessions_dir: sessions\nstandards_root: standards\n",
        encoding="utf-8",
    )
    (project_root / "standards").mkdir()

    user_data = tmp_path / "user-data"
    monkeypatch.setenv("DESKTOP_USER_DATA", str(user_data))

    config = CLIConfig.load(
        project_root=project_root,
        config_path=project_root / "config" / "config.yaml",
    )

    assert config.sessions_dir == user_data / "sessions"
    assert config.standards_root == project_root / "standards"
