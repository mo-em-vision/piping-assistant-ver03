"""Regression tests for NPS entry unit resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.nps_input_resolver import _nps_entry_unit
from models.fact import FactClass, ValidationStatus, build_categorical_fact, fact_from_user_submission
from models.fact import FactProvenance, FactSource, SourceType


def test_nps_entry_unit_defaults_dimensionless_to_nps() -> None:
    fact = build_categorical_fact(
        key="nominal_pipe_size",
        parameter="nominal_pipe_size",
        label="4",
        normalized_key="4",
        fact_class=FactClass.USER_SUPPLIED,
        source=FactSource(source_type=SourceType.USER_INPUT, source_id="USER"),
        provenance=FactProvenance(task_id="t1"),
        validation_status=ValidationStatus.CONFIRMED,
    )
    assert _nps_entry_unit(fact) == "NPS"


def test_nps_entry_unit_uses_original_unit() -> None:
    fact = fact_from_user_submission(
        key="nominal_pipe_size",
        value="100",
        unit="DN",
        task_id="t1",
        original_unit="DN",
    )
    assert _nps_entry_unit(fact) == "DN"


def test_apply_nominal_pipe_size_lookup_with_dimensionless_fact() -> None:
    from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
    from engine.state.state_manager import TaskStateManager
    from models.task import TaskStatus

    standards_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("nps-legacy-unit", status=TaskStatus.AWAITING_INPUT)
    fact = fact_from_user_submission(
        key="nominal_pipe_size",
        value="4",
        unit="dimensionless",
        task_id=task.task_id,
    )
    manager.store_input(task.task_id, fact)
    task = manager.get_task(task.task_id)

    apply_nominal_pipe_size_lookup(task, standards_root)

    od = task.fact_store.active_fact("outside_diameter")
    assert od is not None
    from models.fact import fact_scalar_value

    assert fact_scalar_value(od) == pytest.approx(114.3)
