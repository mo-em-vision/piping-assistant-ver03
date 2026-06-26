"""Tests for environment configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings, load_env_files


def test_load_env_files_reads_openai_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-test-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    load_env_files(project_root=tmp_path)

    settings = Settings.from_env()
    assert settings.openai_api_key == "sk-test-from-dotenv"


def test_load_env_files_does_not_override_existing_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-already-set")

    load_env_files(project_root=tmp_path)

    settings = Settings.from_env()
    assert settings.openai_api_key == "sk-already-set"
