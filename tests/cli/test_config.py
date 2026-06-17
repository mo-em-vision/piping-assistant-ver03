"""CLI configuration tests."""

from __future__ import annotations

from config.loader import CLIConfig


def test_cli_config_loads_yaml(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "report_format: html\nlanguage: english\ndefault_standard: ASME_B31.3\nsessions_dir: sessions\n",
        encoding="utf-8",
    )
    cfg = CLIConfig.load(config_path=config_file, project_root=tmp_path)
    assert cfg.report_format == "html"
    assert cfg.sessions_dir == tmp_path / "sessions"
