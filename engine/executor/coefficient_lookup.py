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
from engine.reference.standards_paths import resolve_standard_pack
from models.input import (
    EngineeringInput,
    InputSource,
    InputStatus,
    ResolutionMethod,
    ResolutionRef,
)
from models.task import Task

from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5,
    TABLE_304_1_1,
    TABLE_A_1A,
)

B31_3_SLUG = "asme_b31.3"
A1_TABLE_REF = f"{B31_3_SLUG}/{TABLE_A_1A}"
W_TABLE_REF = f"{B31_3_SLUG}/{TABLE_302_3_5}"
Y_TABLE_REF = f"{B31_3_SLUG}/{TABLE_304_1_1}"

_COEFFICIENT_FIELDS = (
    "weld_joint_efficiency",
    "weld_strength_reduction",
    "temperature_coefficient",
)


def _input_value(existing_inputs: dict[str, Any], input_id: str) -> Any | None:
    raw = existing_inputs.get(input_id)
    if raw is None:
        return None
    if hasattr(raw, "value"):
        return raw.value
    return raw


def _input_ready(existing_inputs: dict[str, Any], input_id: str) -> bool:
    raw = existing_inputs.get(input_id)
    if raw is None:
        return False
    if isinstance(raw, EngineeringInput):
        if raw.value is None or str(raw.value).strip() == "":
            return False
        return raw.status in {InputStatus.CONFIRMED, InputStatus.USER_OVERRIDE}
    return True


def _should_auto_apply(existing: EngineeringInput | None) -> bool:
    if existing is None:
        return True
    if existing.status == InputStatus.USER_OVERRIDE:
        return False
    return existing.status in {InputStatus.PROPOSED_DEFAULT, InputStatus.PENDING}


def _set_table_coefficient(
    task: Task,
    *,
    input_id: str,
    symbol: str,
    value: float,
    description: str,
    table_ref: str,
) -> None:
    task.inputs[input_id] = EngineeringInput(
        input_id=input_id,
        value=value,
        unit="dimensionless",
        source=InputSource.TABLE,
        status=InputStatus.CONFIRMED,
        requires_confirmation=False,
        symbol=symbol,
        description=description,
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=table_ref),
    )
    _remove_from_planning_missing(task, input_id)


def _remove_from_planning_missing(task: Task, input_id: str) -> None:
    planning = task.outputs.get("planning_summary")
    if not isinstance(planning, dict):
        return
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        items = planning.get(key)
        if isinstance(items, list):
            planning[key] = [item for item in items if item != input_id]
    phase_missing = planning.get("phase_missing")
    if isinstance(phase_missing, dict):
        for phase, fields in list(phase_missing.items()):
            if isinstance(fields, list):
                planning["phase_missing"][phase] = [item for item in fields if item != input_id]


def apply_coefficient_lookups(task: Task, standards_root: Path) -> None:
    """Look up E, W, and Y when their prerequisite inputs are confirmed."""
    existing_inputs = dict(task.inputs)
    pack_root = resolve_standard_pack(standards_root, B31_3_SLUG)

    material = _input_value(existing_inputs, "material")
    joint_category = _input_value(existing_inputs, "joint_category")
    design_temperature = _input_value(existing_inputs, "design_temperature")
    temp_input = existing_inputs.get("design_temperature")
    temp_unit = "F"
    if isinstance(temp_input, EngineeringInput):
        temp_unit = str(temp_input.unit or "F")

    material_ready = _input_ready(existing_inputs, "material")
    joint_ready = _input_ready(existing_inputs, "joint_category")
    temperature_ready = _input_ready(existing_inputs, "design_temperature")

    if material_ready and joint_ready:
        existing = task.inputs.get("weld_joint_efficiency")
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
                    input_id="weld_joint_efficiency",
                    symbol="E",
                    value=e_value,
                    description=(
                        f"Quality factor from Tables A-1A/A-1B for {material} ({joint_category})"
                    ),
                    table_ref=A1_TABLE_REF,
                )

    if material_ready and joint_ready and temperature_ready:
        existing = task.inputs.get("weld_strength_reduction")
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
                    input_id="weld_strength_reduction",
                    symbol="W",
                    value=w_value,
                    description="Weld strength reduction factor from Table 302.3.5",
                    table_ref=W_TABLE_REF,
                )

    if temperature_ready and _thin_wall_assumed(existing_inputs):
        existing = task.inputs.get("temperature_coefficient")
        if _should_auto_apply(existing):
            try:
                y_value, _ = lookup_y_coefficient(
                    pack_root,
                    design_temperature=float(design_temperature),
                    design_temperature_unit=temp_unit,
                    material=str(material) if material is not None else None,
                )
            except (ValueError, FileNotFoundError):
                y_value = None
            if y_value is not None:
                _set_table_coefficient(
                    task,
                    input_id="temperature_coefficient",
                    symbol="Y",
                    value=y_value,
                    description="Temperature coefficient from Table 304.1.1",
                    table_ref=Y_TABLE_REF,
                )
