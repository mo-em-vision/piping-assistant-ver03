"""Derive metallurgical group from the material catalog when material grade is known."""

from __future__ import annotations

from pathlib import Path

from engine.reference.material_catalog_db import lookup_metallurgical_group
from engine.reference.parameter_keys import active_material_grade_fact
from engine.state.task_facts import deactivate_fact, fact_scalar_value, store_system_categorical_fact
from models.fact import FactClass, ValidationStatus
from models.task import Task


def _clear_metallurgical_group(task: Task) -> None:
    deactivate_fact(task, "metallurgical_group")


def apply_metallurgical_group_lookup(task: Task, standards_root: Path) -> None:
    """Set metallurgical_group from the material catalog when material_grade is confirmed."""
    material_input = active_material_grade_fact(task)
    if material_input is None or fact_scalar_value(material_input) is None:
        _clear_metallurgical_group(task)
        return

    material_id = str(fact_scalar_value(material_input)).strip()
    if not material_id:
        _clear_metallurgical_group(task)
        return

    from engine.reference.material_resolver import canonical_material_id

    canonical_id = canonical_material_id(material_id, standards_root=standards_root) or material_id
    group = lookup_metallurgical_group(standards_root, canonical_id)
    if group is None:
        return

    existing = task.fact_store.active_fact("metallurgical_group")
    if existing is not None:
        if existing.fact_class == FactClass.USER_SUPPLIED:
            if existing.validation.status == ValidationStatus.CONFIRMED:
                return
        current = str(fact_scalar_value(existing) or "").strip()
        if current == group:
            return

    store_system_categorical_fact(
        task,
        key="metallurgical_group",
        label=group,
        description=f"Metallurgical group derived from material catalog ({material_id})",
    )

    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)
