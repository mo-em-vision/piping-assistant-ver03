"""Tests for opportunistic goal resolution during replan."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.resolution.goal_resolver import resolve_ready_goals
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.helpers.facts import legacy_input, set_fact_from_input


def _standards_db_available(project_root: Path) -> bool:
    from engine.reference.pack_tables_db import resolve_pack_tables_db

    return resolve_pack_tables_db(project_root / "knowledge" / "standards" / "asme" / "asme_b31.3").exists()


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_resolve_ready_goals_applies_allowable_stress_when_prerequisites_exist(
    project_root: Path,
) -> None:
    if not _standards_db_available(project_root):
        pytest.skip("standards tables db must be built")

    manager = TaskStateManager()
    task = manager.create_task("goal-resolver-test01", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(
        task,
        legacy_input(
            input_id="material",
            value="SA-106B",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    set_fact_from_input(
        task,
        legacy_input(
            input_id="design_temperature",
            value=100.0,
            unit="F",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    changed = resolve_ready_goals(task, project_root / "knowledge" / "standards")
    assert changed is True
    assert task.fact_store.active_fact("allowable_stress") is not None
