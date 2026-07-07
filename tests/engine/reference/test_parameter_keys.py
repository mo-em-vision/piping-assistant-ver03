"""Tests for canonical runtime parameter keys."""

from __future__ import annotations

from engine.reference.parameter_keys import (
    MATERIAL_GRADE_KEY,
    active_material_grade_fact,
    api_parameter_id,
    canonical_parameter_key,
    fact_for_task_input,
    is_material_grade_parameter,
    read_parameter_value,
)
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import store_fact
from models.fact import fact_from_user_submission, fact_scalar_value
from models.task import TaskStatus


def test_api_parameter_id_canonicalizes_legacy_aliases() -> None:
    assert api_parameter_id("material") == MATERIAL_GRADE_KEY
    assert api_parameter_id("material_grade") == MATERIAL_GRADE_KEY
    assert api_parameter_id("joint_category") == "pipe_construction_type"
    assert api_parameter_id("design_pressure") == "internal_design_gage_pressure"


def test_material_grade_is_canonical_parameter_key() -> None:
    assert MATERIAL_GRADE_KEY == "material_grade"
    assert canonical_parameter_key("material") == MATERIAL_GRADE_KEY
    assert canonical_parameter_key("material_grade") == MATERIAL_GRADE_KEY
    assert is_material_grade_parameter("material_grade")
    assert is_material_grade_parameter("material")


def test_read_parameter_value_prefers_canonical_key() -> None:
    inputs = {
        "material_grade": "astm_a106_gr_b",
        "material": "legacy",
    }
    assert read_parameter_value(inputs, MATERIAL_GRADE_KEY) == "astm_a106_gr_b"


def test_read_parameter_value_accepts_legacy_material_key() -> None:
    inputs = {"material": "astm_a106_gr_b"}
    assert read_parameter_value(inputs, MATERIAL_GRADE_KEY) == "astm_a106_gr_b"


def test_active_material_grade_fact_reads_legacy_material_fact() -> None:
    manager = TaskStateManager()
    task = manager.create_task("legacy-material", status=TaskStatus.AWAITING_INPUT)
    store_fact(
        task,
        fact_from_user_submission(
            key="material",
            value="astm_a106_gr_b",
            unit="dimensionless",
            task_id=task.task_id,
        ),
    )
    fact = active_material_grade_fact(task)
    assert fact is not None
    assert fact_scalar_value(fact) == "astm_a106_gr_b"


def test_fact_for_task_input_resolves_joint_category_from_pipe_construction_type() -> None:
    from models.fact import fact_from_user_submission

    fact = fact_from_user_submission(
        key="pipe_construction_type",
        value="seamless",
        unit="dimensionless",
        task_id="alias-test",
    )
    inputs = {"pipe_construction_type": fact}
    resolved = fact_for_task_input(inputs, "joint_category")
    assert resolved is fact
