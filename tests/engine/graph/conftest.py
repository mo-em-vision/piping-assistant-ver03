"""Shared fixtures for engine graph tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
