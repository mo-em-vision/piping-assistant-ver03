"""Fixtures for integrity tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")
