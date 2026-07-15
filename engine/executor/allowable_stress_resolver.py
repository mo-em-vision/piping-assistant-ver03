"""Resolve material and design temperature to allowable stress S from B31.3 tables."""

from __future__ import annotations

from pathlib import Path

from engine.executor.lookup_engine import LookupEngine
from engine.reference.asme_b31_3_table_ids import TABLE_A_1
from engine.reference.standards_paths import resolve_standard_pack
from engine.reference.parameter_keys import active_material_grade_fact
from engine.state.task_facts import (
    deactivate_fact,
    fact_scalar_value,
    fact_unit,
    store_lookup_numeric_fact,
)
from models.task import Task

B31_3_SLUG = "asme_b31.3"
B31_3_TABLE_A_1 = TABLE_A_1
B31_3_TABLE_REF = f"{B31_3_SLUG}/{TABLE_A_1}"
LOOKUP_TABLE_REF = "asme-b313-table-A-1"
LOOKUP_RULE = "by_material_temperature"


def _clear_allowable_stress(task: Task) -> None:
    for key in ("allowable_stress", "S", "allowable_stress_lookup", "allowable_stress_unit", "S_unit"):
        task.outputs.pop(key, None)
    deactivate_fact(task, "allowable_stress")


def _material_and_temperature_ready(task: Task) -> tuple[str, float, str] | None:
    material_input = active_material_grade_fact(task)
    temp_input = task.fact_store.active_fact("design_temperature")
    if material_input is None or fact_scalar_value(material_input) is None:
        return None
    if temp_input is None or fact_scalar_value(temp_input) is None:
        return None

    material = str(fact_scalar_value(material_input)).strip()
    if not material:
        return None

    return material, float(fact_scalar_value(temp_input)), str(fact_unit(temp_input) or "F")


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
        rule_result = engine.execute_rule_lookup(
            table_ref=LOOKUP_TABLE_REF,
            rule=LOOKUP_RULE,
            inputs={
                "material_grade": material,
                "design_temperature": design_temperature,
                "design_temperature_unit": design_temperature_unit,
            },
        )
        stress_pa = float(rule_result.outputs["allowable_stress"])
        interpolated = bool(rule_result.meta.get("interpolated"))
        table_id = str(rule_result.meta.get("table_id") or B31_3_TABLE_A_1)
        temp_f = float(rule_result.meta.get("design_temperature_f", design_temperature))
    except FileNotFoundError as exc:
        raise ValueError(
            "ASME B31.3 standards tables database is not available. "
            "Run scripts/build_standards_tables_db.py and retry."
        ) from exc
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    task.outputs["allowable_stress"] = stress_pa
    task.outputs["S"] = stress_pa
    task.outputs["allowable_stress_unit"] = "Pa"
    task.outputs["allowable_stress_lookup"] = {
        "standard": B31_3_SLUG,
        "table_id": table_id,
        "material": material,
        "design_temperature_f": temp_f,
        "interpolated": interpolated,
    }

    store_lookup_numeric_fact(
        task,
        key="allowable_stress",
        amount=stress_pa,
        unit="Pa",
        table_ref=B31_3_TABLE_REF,
        symbol="S",
        description="Allowable stress from ASME B31.3 Table A-1 (sample)",
    )

    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)
