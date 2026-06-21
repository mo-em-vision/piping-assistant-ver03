"""Resolve symbol definitions and defaults from nomenclature definition nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.assumption_checker import field_value, normalize_assumption_value
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput


@dataclass(frozen=True)
class NomenclatureDefault:
    value: Any
    unit: str
    condition: str | None = None
    requires_confirmation: bool = True


@dataclass(frozen=True)
class NomenclatureEntry:
    symbol: str
    description: str
    unit: str = "dimensionless"
    input_id: str | None = None
    allowed_units: tuple[str, ...] = ()
    references: tuple[dict[str, Any], ...] = ()
    defaults: tuple[NomenclatureDefault, ...] = ()


def input_applies(
    spec: dict[str, Any],
    task_inputs: dict[str, EngineeringInput],
) -> bool:
    when = spec.get("when")
    if not when or not isinstance(when, dict):
        return True
    field_name = str(when.get("field", ""))
    allowed = when.get("in") or []
    if not field_name:
        return True
    value = field_value(field_name, task_inputs)
    if value is None:
        return False
    normalized_allowed = {normalize_assumption_value(v) for v in allowed}
    return value in normalized_allowed


def load_nomenclature(reader: StandardsReader, node_id: str) -> dict[str, NomenclatureEntry]:
    """Load symbol definitions from a definition node's ``nomenclature`` block."""
    record = reader.load(node_id)
    entries: dict[str, NomenclatureEntry] = {}
    for item in record.metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        if not symbol:
            continue

        defaults: list[NomenclatureDefault] = []
        for default_item in item.get("defaults", []) or []:
            if not isinstance(default_item, dict):
                continue
            defaults.append(
                NomenclatureDefault(
                    value=default_item.get("value"),
                    unit=str(default_item.get("unit", item.get("unit", "dimensionless"))),
                    condition=(
                        str(default_item["condition"]).strip()
                        if default_item.get("condition")
                        else None
                    ),
                    requires_confirmation=bool(
                        default_item.get("requires_confirmation", True)
                    ),
                )
            )

        allowed = item.get("allowed_units") or []
        refs = item.get("references") or []
        entries[symbol] = NomenclatureEntry(
            symbol=symbol,
            description=str(item.get("description", "")).strip(),
            unit=str(item.get("unit", "dimensionless")),
            input_id=str(item["input_id"]) if item.get("input_id") else None,
            allowed_units=tuple(str(u) for u in allowed),
            references=tuple(r for r in refs if isinstance(r, dict)),
            defaults=tuple(defaults),
        )
    return entries


def entry_for_symbol(
    nomenclature: dict[str, NomenclatureEntry],
    *,
    symbol: str | None = None,
    input_id: str | None = None,
) -> NomenclatureEntry | None:
    if symbol and symbol in nomenclature:
        return nomenclature[symbol]
    if input_id:
        for entry in nomenclature.values():
            if entry.input_id == input_id:
                return entry
    return None


def resolve_input_spec(
    input_spec: dict[str, Any],
    nomenclature: dict[str, NomenclatureEntry],
) -> dict[str, Any]:
    """Merge calculation input metadata with nomenclature definitions."""
    merged = dict(input_spec)
    symbol = str(input_spec.get("name", ""))
    input_id = str(input_spec.get("id", ""))
    entry = entry_for_symbol(nomenclature, symbol=symbol or None, input_id=input_id or None)
    if entry is None:
        return merged

    if not merged.get("description"):
        merged["description"] = entry.description
    if merged.get("unit") in (None, "", "dimensionless") and entry.unit != "dimensionless":
        merged["unit"] = entry.unit
    if not merged.get("allowed_units") and entry.allowed_units:
        merged["allowed_units"] = list(entry.allowed_units)

    if entry.defaults and merged.get("default") is None:
        first = entry.defaults[0]
        merged["default"] = first.value
        if first.requires_confirmation:
            merged["requires_confirmation"] = True
            merged["source"] = merged.get("source", "default")
        merged["default_condition"] = first.condition

    return merged


def load_nomenclature_for_node(
    reader: StandardsReader,
    record_metadata: dict[str, Any],
) -> dict[str, NomenclatureEntry]:
    """Load nomenclature from explicit ref or dependency definition nodes."""
    refs: list[str] = []
    for item in record_metadata.get("inputs", []) or []:
        if isinstance(item, dict) and item.get("nomenclature_ref"):
            refs.append(str(item["nomenclature_ref"]))
    for dep in record_metadata.get("depends_on", []) or []:
        if isinstance(dep, dict) and dep.get("node_id"):
            dep_id = str(dep["node_id"])
            try:
                dep_record = reader.load(dep_id)
                if dep_record.metadata.get("type") == "definition":
                    refs.append(dep_id)
            except FileNotFoundError:
                continue

    merged: dict[str, NomenclatureEntry] = {}
    for node_id in dict.fromkeys(refs):
        merged.update(load_nomenclature(reader, node_id))
    return merged


def b36_reference(entry: NomenclatureEntry) -> dict[str, Any] | None:
    for ref in entry.references:
        standard = str(ref.get("standard", "")).lower().replace(".", "_")
        if "b36_10" in standard or standard == "asme_b36_10":
            return ref
    return None


def default_question(entry: NomenclatureEntry, default: NomenclatureDefault) -> str:
    label = entry.symbol
    if default.condition:
        return (
            f"For {label}: the default is {default.value} {default.unit} when "
            f"{default.condition}. Confirm or enter another value."
        )
    return (
        f"For {label}: the default is {default.value} {default.unit}. "
        f"Confirm or enter another value."
    )
