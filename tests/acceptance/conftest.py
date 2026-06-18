"""Shared fixtures for acceptance criteria tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


@pytest.fixture
def state_manager() -> TaskStateManager:
    return TaskStateManager()


@pytest.fixture
def expected_dir(project_root: Path) -> Path:
    return project_root / "tests" / "data" / "expected"


@pytest.fixture
def scenario_runner(standards_reader):
    from tests.e2e.scenario_runner import ScenarioRunner

    return ScenarioRunner(standards_reader)
