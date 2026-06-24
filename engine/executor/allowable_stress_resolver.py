"""Resolve material and design temperature to allowable stress S from B31.3 tables."""

from __future__ import annotations

from pathlib import Path

from engine.executor.lookup_engine import LookupEngine
from engine.reference.standards_paths import resolve_standard_pack
from models.input import (
    EngineeringInput,
    InputSource,
    InputStatus,
    ResolutionMethod,
    ResolutionRef,
)
from models.task import Task

B31_3_SLUG = "asme_b31.3"
B31_3_MATERIAL_STRESS_TABLE = "material_allowable_stress"
B31_3_TABLE_REF = "asme_b31.3/material_allowable_stress"
LOOKUP_CONFIG = {
    "table_id": B31_3_MATERIAL_STRESS_TABLE,
    "interpolation": True,
}


def _clear_allowable_stress(task: Task) -> None:
    for key in ("allowable_stress", "S", "allowable_stress_lookup", "allowable_stress_unit", "S_unit"):
        task.outputs.pop(key, None)
    task.inputs.pop("allowable_stress", None)


def _material_and_temperature_ready(task: Task) -> tuple[str, float, str] | None:
    material_input = task.inputs.get("material")
    temp_input = task.inputs.get("design_temperature")
    if material_input is None or material_input.value is None:
        return None
    if temp_input is None or temp_input.value is None:
        return None

    material = str(material_input.value).strip()
    if not material:
        return None

    return material, float(temp_input.value), str(temp_input.unit or "F")


def apply_allowable_stress_lookup(task: Task, standards_root: Path) -> None:
    """Look up S in ASME B31.3 tables when material and design temperature are confirmed."""
    ready = _material_and_temperature_ready(task)
    if ready is None:
        _clear_allowable_stress(task)
        return

    material, design_temperature, design_temperature_unit = ready
    pack_root = resolve_standard_pack(standards_root, B31_3_SLUG)
    engine = LookupEngine(pack_root)

    try:
        result = engine.execute_lookup(
            node_id="B313-material-stress",
            lookup_config=LOOKUP_CONFIG,
            inputs={
                "material": material,
                "design_temperature": design_temperature,
                "design_temperature_unit": design_temperature_unit,
            },
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "ASME B31.3 standards tables database is not available. "
            "Run scripts/build_standards_tables_db.py and retry."
        ) from exc
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    stress_pa = result.trace.allowable_stress_pa
    task.outputs["allowable_stress"] = stress_pa
    task.outputs["S"] = stress_pa
    task.outputs["allowable_stress_unit"] = "Pa"
    task.outputs["allowable_stress_lookup"] = {
        "standard": B31_3_SLUG,
        "table_id": result.trace.table_id,
        "material": material,
        "design_temperature_f": result.trace.design_temperature_f,
        "interpolated": result.trace.interpolated,
    }

    task.inputs["allowable_stress"] = EngineeringInput(
        input_id="allowable_stress",
        value=stress_pa,
        unit="Pa",
        source=InputSource.TABLE,
        status=InputStatus.CONFIRMED,
        symbol="S",
        description="Allowable stress from ASME B31.3 Table A-1 (sample)",
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=B31_3_TABLE_REF),
    )

    planning = task.outputs.get("planning_summary")
    if isinstance(planning, dict):
        for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
            items = planning.get(key)
            if isinstance(items, list):
                planning[key] = [item for item in items if item != "allowable_stress"]
        phase_missing = planning.get("phase_missing")
        if isinstance(phase_missing, dict):
            for phase, fields in list(phase_missing.items()):
                if isinstance(fields, list):
                    planning["phase_missing"][phase] = [
                        item for item in fields if item != "allowable_stress"
                    ]
