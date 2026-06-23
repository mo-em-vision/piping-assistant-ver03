"""Release readiness checks for MVP sign-off (Phase 15)."""

from __future__ import annotations

import json
from pathlib import Path


def test_desktop_package_has_release_scripts(project_root: Path) -> None:
    package = json.loads((project_root / "desktopApp" / "package.json").read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})
    assert "verify:mvp" in scripts
    assert "verify:release" in scripts
    assert "package:win" in scripts


def test_electron_builder_config_present(project_root: Path) -> None:
    package = json.loads((project_root / "desktopApp" / "package.json").read_text(encoding="utf-8"))
    build = package.get("build", {})
    assert build.get("productName") == "Engineering Workspace"
    assert any(target.get("target") == "nsis" for target in build.get("win", {}).get("target", []))


def test_app_logger_and_diagnostics_support(project_root: Path) -> None:
    logger = project_root / "desktopApp" / "electron" / "services" / "appLogger.ts"
    menu = project_root / "desktopApp" / "electron" / "menu.ts"
    assert logger.is_file()
    menu_text = menu.read_text(encoding="utf-8")
    assert "Open Logs Folder" in menu_text
    assert "Copy Diagnostics" in menu_text


def test_health_endpoint_available(project_root: Path) -> None:
    server = (project_root / "api" / "server.py").read_text(encoding="utf-8")
    assert 'path == "/health"' in server


def test_mvp_completion_documented(project_root: Path) -> None:
    roadmap = (project_root / "docs" / "desktopApp" / "14_desktop_app_implementation_roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "Phase 13 — MVP Verification" in roadmap
    assert "generate report" in roadmap.lower()
