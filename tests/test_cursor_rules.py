"""Verify Cursor implementation rule artifacts exist (Phase 14)."""

from __future__ import annotations

from pathlib import Path


def test_agents_md_exists(project_root: Path) -> None:
    agents = project_root / "AGENTS.md"
    assert agents.is_file()
    content = agents.read_text(encoding="utf-8")
    assert "desktopApp" in content
    assert "verify:mvp" in content


def test_cursor_rules_directory(project_root: Path) -> None:
    rules_dir = project_root / ".cursor" / "rules"
    assert rules_dir.is_dir()
    rule_files = sorted(rules_dir.glob("*.mdc"))
    names = {path.stem for path in rule_files}
    assert "desktop-project" in names
    assert "desktop-frontend" in names
    assert "backend-engine" in names


def test_desktop_project_rule_is_always_apply(project_root: Path) -> None:
    rule = project_root / ".cursor" / "rules" / "desktop-project.mdc"
    text = rule.read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
