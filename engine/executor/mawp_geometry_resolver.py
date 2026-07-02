"""Resolve MAWP workflow geometry inputs from NPS/schedule or direct entry."""

from __future__ import annotations

from pathlib import Path

from engine.executor.nps_input_resolver import (
    B36_10_TABLE_REF,
    _normalize_entry_unit,
    _to_nps_lookup_key,
)
from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.assumption_checker import field_value
from engine.state.task_facts import (
    active_facts,
    fact_scalar_value,
    fact_unit,
    store_lookup_categorical_fact,
    store_lookup_numeric_fact,
    store_system_categorical_fact,
    store_user_fact,
)
from models.task import Task


def _geometry_mode(task: Task) -> str:
    inputs = active_facts(task)
    mode = field_value("geometry_input_mode", inputs)
    if mode in {"nps_and_schedule", "direct_od_and_thickness"}:
        return str(mode)
    if field_value("pipe_schedule", inputs) is not None:
        return "nps_and_schedule"
    if field_value("actual_wall_thickness", inputs) is not None:
        return "direct_od_and_thickness"
    return "nps_and_schedule"


def apply_geometry_input_mode_default(task: Task) -> None:
    if task.fact_store.active_fact("geometry_input_mode") is not None:
        return
    store_system_categorical_fact(
        task,
        key="geometry_input_mode",
        label="nps_and_schedule",
    )


def apply_nominal_pipe_size_for_mawp(task: Task, standards_root: Path) -> None:
    """Look up outside diameter from NPS (schedule applied separately)."""
    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    if nps_input is None or fact_scalar_value(nps_input) is None:
        return

    raw_nps = str(fact_scalar_value(nps_input)).strip()
    if not raw_nps:
        raise ValueError("Nominal pipe size is required.")

    entry_unit = _normalize_entry_unit(fact_unit(nps_input))
    lookup_nps = _to_nps_lookup_key(raw_nps, entry_unit)

    lookup = PipeDimensionLookup(standards_root)
    try:
        result = lookup.lookup(lookup_nps)
    except FileNotFoundError as exc:
        raise ValueError(
            "Pipe dimension database is not available. "
            "Run scripts/build_pipe_dimensions_db.py and retry."
        ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Nominal pipe size {raw_nps!r} was not found in {lookup.standard_slug}. "
            "Enter a standard NPS (for example 2, 4, or 6)."
        ) from exc

    store_lookup_categorical_fact(
        task,
        key="nominal_pipe_size",
        label=str(result.nps),
        table_ref=B36_10_TABLE_REF,
        original_value=nps_input.original_value or raw_nps,
    )
    store_system_categorical_fact(
        task,
        key="geometry_input_mode",
        label="nps_and_schedule",
    )


def apply_pipe_schedule_lookup(task: Task, standards_root: Path) -> None:
    """Look up outside diameter and wall thickness from NPS and schedule."""
    if _geometry_mode(task) != "nps_and_schedule":
        return

    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    schedule_input = task.fact_store.active_fact("pipe_schedule")
    if nps_input is None or fact_scalar_value(nps_input) is None:
        raise ValueError("Nominal pipe size is required before pipe schedule lookup.")
    if schedule_input is None or fact_scalar_value(schedule_input) is None:
        raise ValueError("Pipe schedule is required.")

    raw_nps = str(fact_scalar_value(nps_input)).strip()
    raw_schedule = str(fact_scalar_value(schedule_input)).strip()
    if not raw_schedule:
        raise ValueError("Pipe schedule is required.")

    entry_unit = _normalize_entry_unit(fact_unit(nps_input))
    lookup_nps = _to_nps_lookup_key(raw_nps, entry_unit)

    lookup = PipeDimensionLookup(standards_root)
    try:
        result = lookup.lookup(lookup_nps, schedule=raw_schedule)
    except FileNotFoundError as exc:
        raise ValueError(
            "Pipe dimension database is not available. "
            "Run scripts/build_pipe_dimensions_db.py and retry."
        ) from exc
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if result.wall_thickness_mm is None:
        raise ValueError(
            f"Wall thickness for NPS {result.nps!r} schedule {raw_schedule!r} "
            "was not found in ASME B36.10."
        )

    store_lookup_categorical_fact(
        task,
        key="pipe_schedule",
        label=str(result.schedule or raw_schedule),
        table_ref=B36_10_TABLE_REF,
        original_value=schedule_input.original_value or raw_schedule,
    )
    store_lookup_numeric_fact(
        task,
        key="outside_diameter",
        amount=result.outside_diameter_mm,
        unit="mm",
        table_ref=B36_10_TABLE_REF,
        symbol="D",
        description="Outside diameter from ASME B36.10M",
    )
    store_lookup_numeric_fact(
        task,
        key="actual_wall_thickness",
        amount=result.wall_thickness_mm,
        unit="mm",
        table_ref=B36_10_TABLE_REF,
        symbol="t_actual",
        description="Wall thickness from ASME B36.10M",
    )

    task.outputs["outside_diameter_lookup"] = {
        "standard": result.standard_slug or lookup.standard_slug,
        "table_id": result.table_id,
        "nps": result.nps,
        "schedule": result.schedule,
        "outside_diameter_in": result.outside_diameter_in,
        "outside_diameter_mm": result.outside_diameter_mm,
        "wall_thickness_in": result.wall_thickness_in,
        "wall_thickness_mm": result.wall_thickness_mm,
    }

    _clear_geometry_from_planning(
        task,
        {"nominal_pipe_size", "pipe_schedule", "outside_diameter", "actual_wall_thickness"},
    )


def apply_direct_geometry_mode(task: Task) -> None:
    if _geometry_mode(task) != "direct_od_and_thickness":
        return
    store_system_categorical_fact(
        task,
        key="geometry_input_mode",
        label="direct_od_and_thickness",
    )


def _clear_geometry_from_planning(task: Task, field_ids: set[str]) -> None:
    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)
