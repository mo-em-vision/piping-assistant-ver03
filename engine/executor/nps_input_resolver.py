"""Resolve nominal pipe size submissions to outside diameter via standards tables."""

from __future__ import annotations

from pathlib import Path

from engine.graph.lookup_resolution_service import resolve_outside_diameter_from_nps
from models.task import Task

B36_10_TABLE_REF = "asme_b36.10/table-2-1"


def apply_nominal_pipe_size_lookup(task: Task, standards_root: Path) -> None:
    """Look up NPS in the pipe dimension database and store outside diameter."""
    try:
        resolve_outside_diameter_from_nps(task, standards_root)
    except ValueError as exc:
        message = str(exc)
        if "Nominal pipe size" in message and "not found" not in message.lower():
            raise ValueError(
                f"Nominal pipe size was not found in ASME B36.10. "
                f"Enter a standard NPS (for example 2, 4, or 6) or choose direct outside diameter."
            ) from exc
        raise
