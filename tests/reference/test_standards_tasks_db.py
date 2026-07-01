"""Tests for global workflow tasks database build."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_paths import resolve_global_tasks_db
from engine.reference.standards_tasks_db import StandardsTasksDatabase
from scripts.build_standards_tasks_db import build_all


def test_build_workflows_db_includes_pipe_wall_thickness(project_root: Path) -> None:
    import pytest

    standards_root = project_root / "knowledge" / "standards"
    workflow = (
        standards_root
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "workflows"
        / "pipe-wall-thickness.yaml"
    )
    if not workflow.is_file():
        pytest.skip("workflow YAML not present in this workspace")
    db_path = build_all(standards_root=standards_root)
    assert db_path is not None
    assert db_path == resolve_global_tasks_db(standards_root)

    database = StandardsTasksDatabase(db_path)
    record = database.get_node("WF-PIPE-WALL-THICKNESS")
    assert record is not None
    assert record["source_rel_path"] == "asme_b31.3/nodes/workflows/pipe-wall-thickness.yaml"
    assert database.resolve_node_id("pipe_wall_thickness_design") == "WF-PIPE-WALL-THICKNESS"
