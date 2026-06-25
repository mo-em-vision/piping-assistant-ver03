"""Shared fixtures for API tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
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


def api_session_id(service: DesktopApiService, name: str = "API Test Project") -> str:
    return service.create_project(name)["id"]
