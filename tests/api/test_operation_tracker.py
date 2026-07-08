"""Tests for developer operation tracking."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from engine.inspection.operation_tracker import operations_snapshot, track_operation


@pytest.fixture
def inspection_env():
    from engine.inspection.operation_tracker import _tracker

    previous = os.environ.get("DEV_INSPECTION_ENABLED")
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    with _tracker._lock:
        _tracker._running.clear()
        _tracker._recent.clear()
    yield
    if previous is None:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)
    else:
        os.environ["DEV_INSPECTION_ENABLED"] = previous


def test_track_operation_records_running_and_recent(inspection_env) -> None:
    assert operations_snapshot() == {"running": [], "recent": []}

    with track_operation("slow_step", category="planning", task_id="task-1"):
        running = operations_snapshot()["running"]
        assert len(running) == 1
        assert running[0]["name"] == "slow_step"
        assert running[0]["category"] == "planning"
        assert running[0]["metadata"]["task_id"] == "task-1"
        assert running[0]["elapsed_ms"] >= 0

    recent = operations_snapshot()["recent"]
    assert len(recent) == 1
    assert recent[0]["name"] == "slow_step"
    assert recent[0]["status"] == "completed"
    assert recent[0]["duration_ms"] is not None
    assert recent[0]["duration_ms"] >= 0


def test_track_operation_records_failure(inspection_env) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with track_operation("failing_step", category="execution"):
            raise RuntimeError("boom")

    recent = operations_snapshot()["recent"]
    assert recent[0]["status"] == "failed"
    assert recent[0]["error"] == "boom"


def test_track_operation_nested_parent(inspection_env) -> None:
    with track_operation("outer", category="http"):
        with track_operation("inner", category="planning"):
            running = operations_snapshot()["running"]
            assert len(running) == 2
            inner = next(item for item in running if item["name"] == "inner")
            outer = next(item for item in running if item["name"] == "outer")
            assert inner["parent_id"] == outer["id"]


def test_operations_api_disabled_without_env(project_root: Path) -> None:
    os.environ.pop("DEV_INSPECTION_ENABLED", None)
    service = DesktopApiService.from_project_root(project_root)
    with pytest.raises(ApiError) as exc:
        service.get_operations()
    assert exc.value.status == 404


def test_operations_api_enabled(project_root: Path, inspection_env) -> None:
    service = DesktopApiService.from_project_root(project_root)
    with track_operation("api_probe", category="planning"):
        payload = service.get_operations()
    assert any(item["name"] == "api_probe" for item in payload["running"])
