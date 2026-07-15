"""Tests for canonical lookup resolution service."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
from engine.graph.lookup_resolution_service import (
    OUTSIDE_DIAMETER_LOOKUP_NODE,
    resolve_and_store_lookup,
)
from engine.state.state_manager import TaskStateManager
from models.fact import SourceType, fact_scalar_value
from models.input import EngineeringInput, InputSource, InputStatus
from engine.state.fact_migration import fact_from_engineering_input


def _standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def _task_with_nps(*, task_id: str, nps: str = "2") -> tuple:
    state = TaskStateManager()
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
                value=nps,
                unit="NPS",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task_id,
        ),
    )
    return state, state.get_task(task_id)


def test_resolve_and_store_lookup_enriches_fact_provenance() -> None:
    _, task = _task_with_nps(task_id="lookup-prov-od")
    result = resolve_and_store_lookup(
        task,
        lookup_node_id=OUTSIDE_DIAMETER_LOOKUP_NODE,
        standards_root=_standards_root(),
        target_parameters=["outside_diameter"],
    )
    od = task.fact_store.active_fact("outside_diameter")
    assert od is not None
    assert od.source.source_type == SourceType.TABLE_LOOKUP
    assert od.source.lookup_node == OUTSIDE_DIAMETER_LOOKUP_NODE
    assert "by_nps" in od.source.source_id
    assert "nominal_pipe_size" in od.source.input_facts
    assert od.metadata.get("lookup_row_identity") == result.meta.get("nps")
    assert od.metadata.get("authority_id") == "AUTH-ASME-B36.10M"


def test_idempotent_resubmit_does_not_duplicate_active_od_fact() -> None:
    _, task = _task_with_nps(task_id="lookup-idempotent")
    resolve_and_store_lookup(
        task,
        lookup_node_id=OUTSIDE_DIAMETER_LOOKUP_NODE,
        standards_root=_standards_root(),
        target_parameters=["outside_diameter"],
    )
    first_id = task.fact_store.active_fact("outside_diameter").id
    resolve_and_store_lookup(
        task,
        lookup_node_id=OUTSIDE_DIAMETER_LOOKUP_NODE,
        standards_root=_standards_root(),
        target_parameters=["outside_diameter"],
    )
    second = task.fact_store.active_fact("outside_diameter")
    assert second.id == first_id


def test_nps_change_supersedes_prior_outside_diameter() -> None:
    state, task = _task_with_nps(task_id="lookup-nps-change", nps="2")
    apply_nominal_pipe_size_lookup(task, _standards_root())
    first_od = fact_scalar_value(task.fact_store.active_fact("outside_diameter"))

    state.store_input(
        task.task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="nominal_pipe_size",
                value="4",
                unit="NPS",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task.task_id,
        ),
    )
    task = state.get_task(task.task_id)
    apply_nominal_pipe_size_lookup(task, _standards_root())
    second_od = fact_scalar_value(task.fact_store.active_fact("outside_diameter"))
    assert first_od != pytest.approx(second_od)
    assert second_od == pytest.approx(114.3, rel=1e-3)
