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
from models.input import (
    EngineeringInput,
    InputSource,
    InputStatus,
    ResolutionMethod,
    ResolutionRef,
)
from models.task import Task


def _geometry_mode(task: Task) -> str:
    mode = field_value("geometry_input_mode", task.inputs)
    if mode in {"nps_and_schedule", "direct_od_and_thickness"}:
        return str(mode)
    if field_value("pipe_schedule", task.inputs) is not None:
        return "nps_and_schedule"
    if field_value("actual_wall_thickness", task.inputs) is not None:
        return "direct_od_and_thickness"
    return "nps_and_schedule"


def apply_geometry_input_mode_default(task: Task) -> None:
    if task.inputs.get("geometry_input_mode") is not None:
        return
    task.inputs["geometry_input_mode"] = EngineeringInput(
        input_id="geometry_input_mode",
        value="nps_and_schedule",
        unit="dimensionless",
        source=InputSource.SYSTEM,
        status=InputStatus.CONFIRMED,
    )


def apply_nominal_pipe_size_for_mawp(task: Task, standards_root: Path) -> None:
    """Look up outside diameter from NPS (schedule applied separately)."""
    nps_input = task.inputs.get("nominal_pipe_size")
    if nps_input is None or nps_input.value is None:
        return

    raw_nps = str(nps_input.value).strip()
    if not raw_nps:
        raise ValueError("Nominal pipe size is required.")

    entry_unit = _normalize_entry_unit(nps_input.unit)
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

    task.inputs["nominal_pipe_size"] = EngineeringInput(
        input_id="nominal_pipe_size",
        value=result.nps,
        unit="dimensionless",
        source=nps_input.source,
        status=InputStatus.CONFIRMED,
        original_value=nps_input.original_value or raw_nps,
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=B36_10_TABLE_REF),
    )

    task.inputs["geometry_input_mode"] = EngineeringInput(
        input_id="geometry_input_mode",
        value="nps_and_schedule",
        unit="dimensionless",
        source=InputSource.SYSTEM,
        status=InputStatus.CONFIRMED,
    )


def apply_pipe_schedule_lookup(task: Task, standards_root: Path) -> None:
    """Look up outside diameter and wall thickness from NPS and schedule."""
    if _geometry_mode(task) != "nps_and_schedule":
        return

    nps_input = task.inputs.get("nominal_pipe_size")
    schedule_input = task.inputs.get("pipe_schedule")
    if nps_input is None or nps_input.value is None:
        raise ValueError("Nominal pipe size is required before pipe schedule lookup.")
    if schedule_input is None or schedule_input.value is None:
        raise ValueError("Pipe schedule is required.")

    raw_nps = str(nps_input.value).strip()
    raw_schedule = str(schedule_input.value).strip()
    if not raw_schedule:
        raise ValueError("Pipe schedule is required.")

    entry_unit = _normalize_entry_unit(nps_input.unit)
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

    task.inputs["pipe_schedule"] = EngineeringInput(
        input_id="pipe_schedule",
        value=result.schedule or raw_schedule,
        unit="dimensionless",
        source=schedule_input.source,
        status=InputStatus.CONFIRMED,
        original_value=schedule_input.original_value or raw_schedule,
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=B36_10_TABLE_REF),
    )

    task.inputs["outside_diameter"] = EngineeringInput(
        input_id="outside_diameter",
        value=result.outside_diameter_mm,
        unit="mm",
        source=InputSource.TABLE,
        status=InputStatus.CONFIRMED,
        symbol="D",
        description="Outside diameter from ASME B36.10M",
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=B36_10_TABLE_REF),
    )

    task.inputs["actual_wall_thickness"] = EngineeringInput(
        input_id="actual_wall_thickness",
        value=result.wall_thickness_mm,
        unit="mm",
        source=InputSource.TABLE,
        status=InputStatus.CONFIRMED,
        symbol="t_actual",
        description="Wall thickness from ASME B36.10M",
        resolution_method=ResolutionMethod.TABLE_LOOKUP,
        resolution_ref=ResolutionRef(table=B36_10_TABLE_REF),
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

    _clear_geometry_from_planning(task, {"nominal_pipe_size", "pipe_schedule", "outside_diameter", "actual_wall_thickness"})


def apply_direct_geometry_mode(task: Task) -> None:
    if _geometry_mode(task) != "direct_od_and_thickness":
        return
    task.inputs["geometry_input_mode"] = EngineeringInput(
        input_id="geometry_input_mode",
        value="direct_od_and_thickness",
        unit="dimensionless",
        source=InputSource.SYSTEM,
        status=InputStatus.CONFIRMED,
    )


def _clear_geometry_from_planning(task: Task, field_ids: set[str]) -> None:
    planning = task.outputs.get("planning_summary")
    if not isinstance(planning, dict):
        return
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        items = planning.get(key)
        if isinstance(items, list):
            planning[key] = [item for item in items if item not in field_ids]
    phase_missing = planning.get("phase_missing")
    if isinstance(phase_missing, dict):
        for phase, fields in list(phase_missing.items()):
            if isinstance(fields, list):
                planning["phase_missing"][phase] = [item for item in fields if item not in field_ids]
