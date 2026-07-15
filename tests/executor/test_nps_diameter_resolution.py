"""NPS-based outside diameter resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
from engine.executor.node_runner import NodeRunner
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.fact import fact_scalar_value, fact_unit
from models.input import EngineeringInput, InputSource, InputStatus


def test_nps_submit_lookup_stores_outside_diameter() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    state = TaskStateManager()
    task_id = "nps-lookup-store-od"
    state.create_task(task_id)
    state.store_input(
        task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="nominal_pipe_size",
                value="2",
                unit="dimensionless",
                source=InputSource.USER,
            ),
            task_id=task_id,
        ),
    )

    task = state.get_task(task_id)
    apply_nominal_pipe_size_lookup(task, reader.standards_root)
    state.replace_task(task_id, task)

    updated = state.get_task(task_id)
    od_fact = updated.fact_store.active_fact("outside_diameter")
    assert od_fact is not None
    assert fact_scalar_value(od_fact) == pytest.approx(60.33, rel=1e-3)
    assert fact_unit(od_fact) == "mm"
    assert isinstance(updated.outputs.get("outside_diameter_lookup"), dict)


def test_nps_lookup_resolves_outside_diameter_for_calculation() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    state = TaskStateManager()
    task_id = "nps-lookup-wall-thickness"
    state.create_task(task_id)

    state.store_input(
        task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="outside_diameter__resolution_branch",
                value="nps_lookup",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task_id,
        ),
    )
    state.store_input(
        task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="nominal_pipe_size",
                value="2",
                unit="dimensionless",
                source=InputSource.USER,
            ),
            task_id=task_id,
        ),
    )

    task = state.get_task(task_id)
    apply_nominal_pipe_size_lookup(task, reader.standards_root)
    state.replace_task(task_id, task)

    task_inputs = dict(state.get_task(task_id).fact_store.active_facts())
    runner = NodeRunner(reader)
    record = reader.load("304.1.2-a")
    resolved, missing = runner._resolve_calculation_inputs(
        record,
        task_inputs=task_inputs,
        dependency_outputs={},
    )

    assert "outside_diameter" not in missing
    assert "nominal_pipe_size" not in missing
    assert resolved["D"] == pytest.approx(60.33, rel=1e-3)
    assert resolved.get("D_unit") == "mm"
