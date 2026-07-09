"""Recommend standard pipe schedule from calculated minimum wall thickness."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.executor.pipe_dimension_lookup import B36_10_SLUG, PipeDimensionLookup
from engine.executor.unit_manager import prepare_fact
from engine.reference.pipe_dimensions_db import PipeScheduleEntry
from models.fact import fact_scalar_value
from models.task import Task

B36_10_DISPLAY = "ASME B36.10M"
B36_10_TRACE_NODE_ID = "B3610-table-2-1"

_CANONICAL_SCHEDULE_ALIASES: dict[str, str] = {
    "STD": "40",
    "STANDARD": "40",
    "XS": "80",
    "XSTR": "80",
    "XXS": "160",
}


@dataclass(frozen=True)
class PipeScheduleRecommendation:
    """Next standard schedule whose nominal wall thickness is not less than t_m."""

    nps: str
    schedule: str
    wall_thickness_mm: float
    minimum_required_thickness_mm: float
    standard_slug: str
    standard_display: str
    table_id: str


def resolve_task_nps(task: Task, standards_root: Path) -> str | None:
    """Resolve NPS from task inputs or outside-diameter table lookup."""
    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    if nps_input is not None and fact_scalar_value(nps_input) is not None:
        return str(fact_scalar_value(nps_input)).strip()

    lookup_output = task.outputs.get("outside_diameter_lookup")
    if isinstance(lookup_output, dict) and lookup_output.get("nps"):
        return str(lookup_output["nps"]).strip()

    od_input = task.fact_store.active_fact("outside_diameter")
    if od_input is None or fact_scalar_value(od_input) is None:
        return None

    try:
        od_mm = float(fact_scalar_value(prepare_fact(od_input)))
    except (TypeError, ValueError):
        return None

    try:
        lookup = PipeDimensionLookup(standards_root)
    except FileNotFoundError:
        return None
    return lookup.find_nps_by_outside_diameter_mm(od_mm)


def recommend_pipe_schedule(
    *,
    nps: str,
    minimum_required_thickness_mm: float,
    standards_root: Path,
    standard: str = B36_10_SLUG,
) -> PipeScheduleRecommendation | None:
    """Return the lightest standard schedule with nominal wall thickness >= t_m."""
    try:
        lookup = PipeDimensionLookup(standards_root, standard=standard)
        schedules = lookup.list_schedules_for_nps(nps)
    except (FileNotFoundError, ValueError):
        return None

    if not schedules:
        return None

    selected = _select_next_schedule(schedules, float(minimum_required_thickness_mm))
    if selected is None:
        return None

    return PipeScheduleRecommendation(
        nps=nps,
        schedule=selected.schedule,
        wall_thickness_mm=selected.wall_thickness_mm,
        minimum_required_thickness_mm=float(minimum_required_thickness_mm),
        standard_slug=lookup.standard_slug,
        standard_display=B36_10_DISPLAY,
        table_id=lookup.table_id,
    )


def recommend_pipe_schedule_for_task(
    task: Task,
    standards_root: Path,
) -> PipeScheduleRecommendation | None:
    """Recommend schedule when t_m and NPS are available."""
    t_m = task.outputs.get("t_m")
    if t_m is None:
        t_m = task.outputs.get("minimum_required_thickness")
    if t_m is None:
        return None

    nps = resolve_task_nps(task, standards_root)
    if not nps:
        return None

    return recommend_pipe_schedule(
        nps=nps,
        minimum_required_thickness_mm=float(t_m),
        standards_root=standards_root,
    )


def build_b36_10_schedule_lookup_trace_entry(
    task: Task,
    standards_root: Path,
) -> dict[str, Any] | None:
    """Build execution trace lookup payload for B36.10 schedule rows (display renders only)."""
    recommendation = recommend_pipe_schedule_for_task(task, standards_root)
    if recommendation is None:
        return None

    try:
        lookup = PipeDimensionLookup(standards_root)
        schedules = lookup.list_schedules_for_nps(recommendation.nps)
    except (FileNotFoundError, ValueError):
        return None

    if not schedules:
        return None

    deduped = _dedupe_schedules(schedules)
    rows: list[dict[str, Any]] = []
    for entry in sorted(deduped, key=lambda item: item.wall_thickness_mm):
        rows.append(
            {
                "schedule": entry.schedule,
                "wall_thickness_mm": round(float(entry.wall_thickness_mm), 4),
            }
        )

    return {
        "node_id": B36_10_TRACE_NODE_ID,
        "status": "completed",
        "trace": {
            "lookup": {
                "table_id": recommendation.table_id or B36_10_TRACE_NODE_ID,
                "standard": recommendation.standard_slug,
                "title": f"{B36_10_DISPLAY} pipe schedules for NPS {recommendation.nps}",
                "rows": rows,
                "highlight": {
                    "column": "schedule",
                    "value": recommendation.schedule,
                },
                "recommendation": {
                    "nps": recommendation.nps,
                    "schedule": recommendation.schedule,
                    "minimum_required_thickness_mm": recommendation.minimum_required_thickness_mm,
                    "wall_thickness_mm": recommendation.wall_thickness_mm,
                },
                "recommendation_summary": format_schedule_recommendation_text(recommendation),
            }
        },
        "outputs": {},
    }


def append_schedule_lookup_trace_to_payload(
    task: Task,
    trace_payload: list[dict[str, Any]],
    standards_root: Path,
) -> bool:
    """Append B36.10 schedule lookup trace entry once when t_m and NPS are available."""
    for entry in trace_payload:
        if isinstance(entry, dict) and str(entry.get("node_id")) == B36_10_TRACE_NODE_ID:
            return False

    entry = build_b36_10_schedule_lookup_trace_entry(task, standards_root)
    if entry is None:
        return False

    trace_payload.append(entry)
    return True


def format_schedule_recommendation_text(recommendation: PipeScheduleRecommendation) -> str:
    """Human-readable schedule recommendation for display blocks and reports."""
    tm_text = _format_thickness_mm(recommendation.minimum_required_thickness_mm)
    wall_text = _format_thickness_mm(recommendation.wall_thickness_mm)
    schedule_label = _format_schedule_label(recommendation.schedule)
    nps_label = _format_nps_label(recommendation.nps)
    return (
        f"Select {schedule_label} for {nps_label}: its nominal wall thickness "
        f"({wall_text}) is the next standard thickness not less than t_m "
        f"({tm_text}) per {recommendation.standard_display}."
    )


def _format_thickness_mm(value: float) -> str:
    return f"{round(float(value), 3):.3f} mm"


def _select_next_schedule(
    schedules: list[PipeScheduleEntry],
    minimum_required_thickness_mm: float,
) -> PipeScheduleEntry | None:
    deduped = _dedupe_schedules(schedules)
    for entry in sorted(deduped, key=lambda item: item.wall_thickness_mm):
        if entry.wall_thickness_mm + 1e-9 >= minimum_required_thickness_mm:
            return entry
    return None


def _dedupe_schedules(schedules: list[PipeScheduleEntry]) -> list[PipeScheduleEntry]:
    """Keep one schedule label per nominal wall thickness, preferring numeric designations."""
    by_thickness: dict[float, PipeScheduleEntry] = {}
    for entry in schedules:
        canonical = _canonical_schedule(entry.schedule)
        normalized = PipeScheduleEntry(
            schedule=canonical,
            wall_thickness_in=entry.wall_thickness_in,
            wall_thickness_mm=entry.wall_thickness_mm,
        )
        key = round(normalized.wall_thickness_mm, 4)
        existing = by_thickness.get(key)
        if existing is None or _schedule_label_rank(normalized.schedule) < _schedule_label_rank(
            existing.schedule
        ):
            by_thickness[key] = normalized
    return list(by_thickness.values())


def _canonical_schedule(schedule: str) -> str:
    text = str(schedule).strip().upper()
    text = re.sub(r"^SCH(?:EDULE)?\s*", "", text).strip()
    return _CANONICAL_SCHEDULE_ALIASES.get(text, text)


def _schedule_label_rank(schedule: str) -> tuple[int, str]:
    if re.fullmatch(r"\d+", schedule):
        return (0, schedule)
    return (1, schedule)


def _format_schedule_label(schedule: str) -> str:
    if re.fullmatch(r"\d+", schedule):
        return f"Schedule {schedule}"
    return f"Schedule {schedule}"


def _format_nps_label(nps: str) -> str:
    text = str(nps).strip()
    if text.isdigit() or "/" in text or "-" in text:
        return f"NPS {text}"
    return text
