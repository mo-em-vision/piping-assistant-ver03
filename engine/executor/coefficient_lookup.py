"""Resolve weld joint coefficients E, W, and Y from ASME B31.3 tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.coefficient_resolver import (
    _thin_wall_assumed,
    lookup_quality_factor,
    lookup_w_factor,
    lookup_y_coefficient,
)
from engine.executor.lookup_execution_service import store_numeric_lookup_result
from engine.reference.parameter_keys import (
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    MATERIAL_GRADE_KEY,
    parameter_is_ready,
    read_fact_value,
)
from engine.reference.standards_paths import resolve_standard_pack
from engine.state.task_facts import active_facts, fact_unit
from models.fact import Fact, FactClass, ValidationStatus, fact_is_expansion_ready, fact_scalar_value
from models.task import Task

from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5,
    TABLE_304_1_1,
    TABLE_A_3,
)

B31_3_SLUG = "asme_b31.3"
A3_TABLE_REF = f"{B31_3_SLUG}/{TABLE_A_3}"
W_TABLE_REF = f"{B31_3_SLUG}/{TABLE_302_3_5}"
Y_TABLE_REF = f"{B31_3_SLUG}/{TABLE_304_1_1}"

_COEFFICIENT_FIELDS = (
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    "weld_strength_reduction_factor_w",
    "temperature_coefficient_y",
)


def _input_value(existing_inputs: dict[str, Any], input_id: str) -> Any | None:
    raw = existing_inputs.get(input_id)
    if raw is None:
        return None
    if isinstance(raw, Fact):
        return fact_scalar_value(raw)
    if hasattr(raw, "value"):
        return raw.value
    return raw


def _input_ready(existing_inputs: dict[str, Any], input_id: str) -> bool:
    raw = existing_inputs.get(input_id)
    if raw is None:
        return False
    if isinstance(raw, Fact):
        value = fact_scalar_value(raw)
        if value is None or str(value).strip() == "":
            return False
        return fact_is_expansion_ready(raw)
    return True


def _material_input(existing_inputs: dict[str, Any]) -> tuple[Any | None, bool]:
    return (
        read_fact_value(existing_inputs, MATERIAL_GRADE_KEY),
        parameter_is_ready(existing_inputs, MATERIAL_GRADE_KEY),
    )


def _should_auto_apply(existing: Fact | None) -> bool:
    if existing is None:
        return True
    if existing.fact_class == FactClass.USER_SUPPLIED and existing.validation.status == ValidationStatus.CONFIRMED:
        if existing.original_value is not None:
            return False
    return existing.validation.status in {
        ValidationStatus.PENDING,
    } or existing.fact_class == FactClass.DEFAULT_CONFIRMED


def _set_table_coefficient(
    task: Task,
    *,
    input_id: str,
    symbol: str,
    value: float,
    description: str,
    table_ref: str,
) -> None:
    store_numeric_lookup_result(
        task,
        key=input_id,
        amount=value,
        unit="dimensionless",
        table_ref=table_ref,
        symbol=symbol,
        description=description,
        produced_by_node="coefficient_lookup",
    )
    _remove_from_planning_missing(task, input_id)


def _remove_from_planning_missing(task: Task, input_id: str) -> None:
    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)


def _pipe_construction_type_value(existing_inputs: dict[str, Any]) -> Any | None:
    for input_id in ("pipe_construction_type", "joint_category"):
        value = _input_value(existing_inputs, input_id)
        if value is not None:
            return value
    return None


def _pipe_construction_type_ready(existing_inputs: dict[str, Any]) -> bool:
    for input_id in ("pipe_construction_type", "joint_category"):
        if _input_ready(existing_inputs, input_id):
            return True
    return False


def apply_coefficient_lookups(task: Task, standards_root: Path) -> None:
    """Look up E, W, and Y when their prerequisite inputs are confirmed."""
    existing_inputs = active_facts(task)
    pack_root = resolve_standard_pack(standards_root, B31_3_SLUG)

    material, material_ready = _material_input(existing_inputs)
    joint_category = _pipe_construction_type_value(existing_inputs)
    design_temperature = _input_value(existing_inputs, "design_temperature")
    temp_input = existing_inputs.get("design_temperature")
    temp_unit = "F"
    if isinstance(temp_input, Fact):
        temp_unit = str(fact_unit(temp_input) or "F")

    joint_ready = _pipe_construction_type_ready(existing_inputs)
    temperature_ready = _input_ready(existing_inputs, "design_temperature")

    if material_ready and joint_ready:
        existing = task.fact_store.active_fact(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY)
        if _should_auto_apply(existing):
            try:
                e_value = lookup_quality_factor(
                    pack_root,
                    material=str(material),
                    joint_category=str(joint_category),
                )
            except (ValueError, FileNotFoundError):
                e_value = None
            if e_value is not None:
                _set_table_coefficient(
                    task,
                    input_id=LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
                    symbol="E_j",
                    value=e_value,
                    description=(
                        f"Quality factor E_j from Table A-3 for {material} ({joint_category})"
                    ),
                    table_ref=A3_TABLE_REF,
                )

    if material_ready and joint_ready and temperature_ready:
        existing = task.fact_store.active_fact("weld_strength_reduction_factor_w")
        if _should_auto_apply(existing):
            try:
                w_value = lookup_w_factor(
                    pack_root,
                    material=str(material),
                    design_temperature=float(design_temperature),
                    design_temperature_unit=temp_unit,
                    weld_joint_category=str(joint_category),
                )
            except (ValueError, FileNotFoundError):
                w_value = None
            if w_value is not None:
                _set_table_coefficient(
                    task,
                    input_id="weld_strength_reduction_factor_w",
                    symbol="W",
                    value=w_value,
                    description="Weld strength reduction factor from Table 302.3.5-1",
                    table_ref=W_TABLE_REF,
                )

    if temperature_ready and _thin_wall_assumed(existing_inputs):
        existing = task.fact_store.active_fact("temperature_coefficient_y")
        if _should_auto_apply(existing):
            metallurgical_group = _input_value(existing_inputs, "metallurgical_group")
            try:
                y_value, _ = lookup_y_coefficient(
                    pack_root,
                    design_temperature=float(design_temperature),
                    design_temperature_unit=temp_unit,
                    metallurgical_group=(
                        str(metallurgical_group) if metallurgical_group else None
                    ),
                    material=(
                        str(material)
                        if material is not None and not metallurgical_group
                        else None
                    ),
                )
            except (ValueError, FileNotFoundError):
                y_value = None
            if y_value is not None:
                _set_table_coefficient(
                    task,
                    input_id="temperature_coefficient_y",
                    symbol="Y",
                    value=y_value,
                    description="Temperature coefficient from Table 304.1.1-1",
                    table_ref=Y_TABLE_REF,
                )
