"""Resolve nominal pipe size submissions to outside diameter via standards tables."""

from __future__ import annotations

from pathlib import Path

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.assumption_checker import field_value
from engine.state.task_facts import (
    active_facts,
    fact_scalar_value,
    fact_unit,
    store_lookup_categorical_fact,
    store_lookup_numeric_fact,
    store_system_categorical_fact,
)
from models.fact import Fact
from models.task import Task

B36_10_TABLE_REF = "asme_b36.10/table-2-1"

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
    if text in {"DIMENSIONLESS", "1", ""}:
        return "NPS"
    raise ValueError(f"Unsupported nominal pipe size unit: {unit}")


def _nps_entry_unit(fact: Fact) -> str:
    if fact.original_unit:
        return _normalize_entry_unit(fact.original_unit)
    return _normalize_entry_unit(fact_unit(fact))


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
    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    if nps_input is None or fact_scalar_value(nps_input) is None:
        return

    raw_nps = str(fact_scalar_value(nps_input)).strip()
    if not raw_nps:
        raise ValueError("Nominal pipe size is required.")

    entry_unit = _nps_entry_unit(nps_input)
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

    store_lookup_categorical_fact(
        task,
        key="nominal_pipe_size",
        label=str(result.nps),
        table_ref=B36_10_TABLE_REF,
        original_value=nps_input.original_value or raw_nps,
    )

    if field_value("d_input_mode", active_facts(task)) != "direct_od":
        store_system_categorical_fact(task, key="d_input_mode", label="nps_lookup")

    store_lookup_numeric_fact(
        task,
        key="outside_diameter",
        amount=result.outside_diameter_mm,
        unit="mm",
        table_ref=B36_10_TABLE_REF,
        symbol="D",
        description="Outside diameter from ASME B36.10M",
    )

    task.outputs["outside_diameter_lookup"] = {
        "standard": result.standard_slug or lookup.standard_slug,
        "table_id": result.table_id,
        "nps": result.nps,
        "outside_diameter_in": result.outside_diameter_in,
        "outside_diameter_mm": result.outside_diameter_mm,
    }

    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)
