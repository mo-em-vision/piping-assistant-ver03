"""Resolve nominal pipe size submissions to outside diameter via standards tables."""

from __future__ import annotations

from pathlib import Path

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

B36_10_TABLE_REF = "asme_b36.10/welded_seamless_pipe_dimensions"

# ISO 6708 / common DN to ASME B36.10 NPS keys used in the dimension tables.
_DN_TO_NPS: dict[str, str] = {
    "6": "1/8",
    "8": "1/4",
    "10": "3/8",
    "15": "1/2",
    "20": "3/4",
    "25": "1",
    "32": "1-1/4",
    "40": "1-1/2",
    "50": "2",
    "65": "2-1/2",
    "80": "3",
    "100": "4",
    "125": "5",
    "150": "6",
    "200": "8",
    "250": "10",
    "300": "12",
    "350": "14",
    "400": "16",
}


def _normalize_entry_unit(unit: str | None) -> str:
    text = (unit or "NPS").strip().upper()
    if text in {"NPS", "DN"}:
        return text
    if text in {"IN", "INCH", "INCHES"}:
        return "NPS"
    raise ValueError(f"Unsupported nominal pipe size unit: {unit}")


def _to_nps_lookup_key(value: str, unit: str) -> str:
    text = str(value).strip().strip('"').strip("'")
    if not text:
        raise ValueError("Nominal pipe size is required.")

    if unit == "DN":
        dn = text.upper().replace("DN", "").strip()
        mapped = _DN_TO_NPS.get(dn)
        if mapped is None:
            raise ValueError(
                f"DN size {value!r} is not recognized. "
                "Enter a standard DN value (for example 50, 100, or 150)."
            )
        return mapped

    return text


def apply_nominal_pipe_size_lookup(task: Task, standards_root: Path) -> None:
    """Look up NPS in the pipe dimension database and store outside diameter."""
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
            f"Enter a standard NPS (for example 2, 4, or 6) or choose direct outside diameter."
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

    if field_value("d_input_mode", task.inputs) != "direct_od":
        task.inputs["d_input_mode"] = EngineeringInput(
            input_id="d_input_mode",
            value="nps_lookup",
            unit="dimensionless",
            source=InputSource.SYSTEM,
            status=InputStatus.CONFIRMED,
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

    task.outputs["outside_diameter_lookup"] = {
        "standard": result.standard_slug or lookup.standard_slug,
        "table_id": result.table_id,
        "nps": result.nps,
        "outside_diameter_in": result.outside_diameter_in,
        "outside_diameter_mm": result.outside_diameter_mm,
    }

    planning = task.outputs.get("planning_summary")
    if isinstance(planning, dict):
        for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
            items = planning.get(key)
            if isinstance(items, list):
                planning[key] = [
                    item for item in items if item not in {"outside_diameter", "nominal_pipe_size"}
                ]
        phase_missing = planning.get("phase_missing")
        if isinstance(phase_missing, dict):
            for phase, fields in list(phase_missing.items()):
                if isinstance(fields, list):
                    planning["phase_missing"][phase] = [
                        item
                        for item in fields
                        if item not in {"outside_diameter", "nominal_pipe_size"}
                    ]
