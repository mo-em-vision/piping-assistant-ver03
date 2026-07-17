"""Shared fixtures for navigation ownership baseline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader
from tests.navigation.fixtures.synthetic_nav_pack import (
    WORKFLOW_ROOT,
    build_synthetic_nav_pack,
)


@pytest.fixture
def b313_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


@pytest.fixture
def synthetic_nav_reader(tmp_path: Path) -> StandardsReader:
    reader, _root = build_synthetic_nav_pack(tmp_path)
    return reader


@pytest.fixture
def synthetic_nav_root() -> str:
    return WORKFLOW_ROOT
