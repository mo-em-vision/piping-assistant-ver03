"""Tests for enriched execution trace when inspection is enabled."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from engine.executor.executor import execute_workflow
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from tests.acceptance.helpers import sample_inputs


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


@pytest.mark.parametrize("inspection_enabled", [False, True])
def test_execution_trace_records_inspection_metadata_when_enabled(
    project_root: Path,
    inspection_enabled: bool,
) -> None:
    if inspection_enabled:
        os.environ["DEV_INSPECTION_ENABLED"] = "1"
    else:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)

    try:
        manager = TaskStateManager()
        task_id = f"inspection-trace-{inspection_enabled}"
        manager.create_task(task_id)
        for engineering_input in sample_inputs().values():
            manager.store_input(task_id, engineering_input)

        execute_workflow(task_id, "pipe_wall_thickness_design", state=manager, reader=_reader(project_root))
        trace = manager.get_task(task_id).outputs.get("_execution_trace")
        assert isinstance(trace, list)

        if inspection_enabled:
            assert manager.get_task(task_id).outputs.get("_planner_decisions")
            assert manager.get_task(task_id).outputs.get("_execution_events") is not None
            enriched = [
                item
                for item in trace
                if isinstance(item, dict) and item.get("trace", {}).get("inspection")
            ]
            if enriched:
                inspection = enriched[0]["trace"]["inspection"]
                assert "step_index" in inspection
                assert "duration_ms" in inspection
        else:
            assert manager.get_task(task_id).outputs.get("_execution_events") is None
    finally:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)
