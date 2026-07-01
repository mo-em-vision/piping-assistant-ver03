"""Shared fixtures for MVP verification tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


@pytest.fixture
def state_manager() -> TaskStateManager:
    return TaskStateManager()


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    return project_root / "tests" / "data"


@pytest.fixture
def scenarios_dir(project_root: Path) -> Path:
    return project_root / "tests" / "data" / "scenarios"


@pytest.fixture
def expected_dir(project_root: Path) -> Path:
    return project_root / "tests" / "data" / "expected"


@pytest.fixture
def scenario_runner(standards_reader: StandardsReader):
    from tests.e2e.scenario_runner import ScenarioRunner

    return ScenarioRunner(standards_reader)


@pytest.fixture
def mvp_service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    sessions_dir = tmp_path / "sessions"
    standards_root = project_root / "knowledge" / "standards"
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")
