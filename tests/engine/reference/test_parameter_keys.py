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


def test_param_id_and_key_derive_from_name() -> None:
    from engine.reference.parameter_keys import (
        param_id_from_name,
        param_key_from_param_id,
        validate_parameter_identity_fields,
    )

    name = "Basic Quality Factors for Longitudinal Weld Joints in Pipes and Tubes"
    param_id = param_id_from_name(name)
    assert param_id == (
        "PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes"
    )
    assert param_key_from_param_id(param_id) == (
        "basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes"
    )
    assert validate_parameter_identity_fields(
        {
            "id": param_id,
            "key": param_key_from_param_id(param_id),
            "name": name,
        }
    ) == []


def test_weld_joint_efficiency_legacy_alias_canonicalizes() -> None:
    from engine.reference.parameter_keys import (
        LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
        canonical_parameter_key,
    )

    assert (
        canonical_parameter_key("weld_joint_efficiency")
        == LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY
    )


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
