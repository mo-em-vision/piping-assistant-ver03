"""Resolve pipe geometry inputs from NPS/schedule or direct entry."""

from __future__ import annotations

from pathlib import Path

from engine.graph.assumption_checker import field_value
from engine.graph.lookup_resolution_service import (
    B36_10_TABLE_REF,
    resolve_wall_thickness_from_nps_schedule,
)
from engine.graph.resolution_branches import (
    active_resolution_branch_id,
    resolution_branch_fact_key,
)
from engine.state.task_facts import (
    active_facts,
    fact_scalar_value,
    store_lookup_categorical_fact,
    store_system_categorical_fact,
)
from models.fact import SourceType
from models.task import Task


def _geometry_branch(task: Task) -> str | None:
    inputs = active_facts(task)
    branch = active_resolution_branch_id("outside_diameter", inputs)
    if branch in {"nps_lookup", "direct_od"}:
        return str(branch)
    if field_value("pipe_schedule", inputs) is not None:
        return "nps_lookup"
    if field_value("actual_wall_thickness", inputs) is not None:
        return "direct_od"
    return None


def apply_wall_thickness_basis_from_geometry(task: Task) -> None:
    """Infer wall thickness basis when geometry branch implies a known source."""
    if task.fact_store.active_fact("wall_thickness_basis") is not None:
        return
    branch = _geometry_branch(task)
    if branch == "nps_lookup":
        store_system_categorical_fact(
            task,
            key="wall_thickness_basis",
            label="nominal_schedule",
        )
    elif branch == "direct_od":
        store_system_categorical_fact(
            task,
            key="wall_thickness_basis",
            label="measured_actual",
        )


def store_outside_diameter_resolution_branch(task: Task, branch_id: str) -> None:
    store_system_categorical_fact(
        task,
        key=resolution_branch_fact_key("outside_diameter"),
        label=str(branch_id),
    )


def _od_already_table_derived(task: Task) -> bool:
    od = task.fact_store.active_fact("outside_diameter")
    if od is None or fact_scalar_value(od) is None:
        return False
    return od.source.source_type == SourceType.TABLE_LOOKUP


def apply_pipe_schedule_lookup(task: Task, standards_root: Path) -> None:
    """Look up wall thickness from NPS and schedule; do not re-derive OD when already stored."""
    if _geometry_branch(task) != "nps_lookup":
        return

    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    schedule_input = task.fact_store.active_fact("pipe_schedule")
    if nps_input is None or fact_scalar_value(nps_input) is None:
        raise ValueError("Nominal pipe size is required before pipe schedule lookup.")
    if schedule_input is None or fact_scalar_value(schedule_input) is None:
        raise ValueError("Pipe schedule is required.")

    raw_schedule = str(fact_scalar_value(schedule_input)).strip()
    if not raw_schedule:
        raise ValueError("Pipe schedule is required.")

    try:
        result = resolve_wall_thickness_from_nps_schedule(task, standards_root)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    meta = result.meta
    wall_thickness_mm = result.outputs.get("actual_wall_thickness")
    if wall_thickness_mm is None:
        raise ValueError(
            f"Wall thickness for NPS {meta.get('nps')!r} schedule {raw_schedule!r} "
            "was not found in ASME B36.10."
        )

    store_lookup_categorical_fact(
        task,
        key="pipe_schedule",
        label=str(meta.get("schedule") or raw_schedule),
        table_ref=B36_10_TABLE_REF,
        original_value=schedule_input.original_value or raw_schedule,
        lookup_node=result.lookup_node_id,
        lookup_rule=result.rule,
    )
    store_system_categorical_fact(
        task,
        key="wall_thickness_basis",
        label="nominal_schedule",
    )

    od_fact = task.fact_store.active_fact("outside_diameter")
    od_mm = fact_scalar_value(od_fact) if od_fact is not None else None
    if od_mm is not None and not _od_already_table_derived(task):
        od_mm = None

    task.outputs["outside_diameter_lookup"] = {
        "standard": meta.get("standard"),
        "table_id": meta.get("table_id"),
        "lookup_node_id": result.lookup_node_id,
        "rule": result.rule,
        "nps": meta.get("nps"),
        "schedule": meta.get("schedule"),
        "outside_diameter_in": meta.get("outside_diameter_in"),
        "outside_diameter_mm": float(od_mm) if od_mm is not None else None,
        "wall_thickness_in": meta.get("wall_thickness_in"),
        "wall_thickness_mm": float(wall_thickness_mm),
        "row_identity": meta.get("nps", "") + "|" + str(meta.get("schedule") or raw_schedule),
    }

    _clear_geometry_from_planning(
        task,
        {"nominal_pipe_size", "pipe_schedule", "outside_diameter", "actual_wall_thickness"},
    )


def _clear_geometry_from_planning(task: Task, field_ids: set[str]) -> None:
    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)
