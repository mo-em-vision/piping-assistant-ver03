"""Compile virtual parameter nodes from paragraph/workflow nomenclature."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.units.unit_ids import unit_id_from_legacy_symbol


def _param_node_id(symbol: str, input_id: str) -> str:
    sym = str(symbol or "").strip()
    if sym:
        return f"param-{sym}"
    return f"param-{input_id}"


def nomenclature_entry_to_parameter(
    entry: dict[str, Any],
    *,
    parent_id: str,
) -> dict[str, Any] | None:
    """Build parameter metadata from a nomenclature row with ``introduced_here``."""
    if not entry.get("introduced_here"):
        return None
    symbol = str(entry.get("symbol", "")).strip()
    input_id = str(entry.get("input_id", "")).strip() or symbol
    if not symbol and not input_id:
        return None

    node_id = _param_node_id(symbol, input_id)
    meta: dict[str, Any] = {
        "id": node_id,
        "type": "parameter",
        "symbol": symbol or input_id,
        "input_id": input_id,
        "title": str(entry.get("title") or symbol or input_id).strip(),
        "description": str(entry.get("description", "")).strip(),
        "defined_in": [parent_id],
        "located_in": [parent_id],
        "parent_node_id": parent_id,
        "source_container": "nomenclature",
    }

    unit = entry.get("unit")
    if unit:
        unit_text = str(unit).strip()
        if unit_text.startswith("UNIT-"):
            meta["canonical_unit"] = unit_text
        else:
            unit_id = unit_id_from_legacy_symbol(unit_text)
            if unit_id:
                meta["canonical_unit"] = unit_id
            meta["unit"] = unit_text

    allowed = entry.get("allowed_units")
    if isinstance(allowed, list) and allowed:
        meta["allowed_units"] = allowed

    resolution = entry.get("resolution")
    if resolution is not None:
        meta["resolution"] = resolution

    kind = entry.get("kind")
    if kind in {"designation", "quantity"}:
        meta["kind"] = str(kind)
        if kind == "quantity" and entry.get("dimension"):
            meta["dimension"] = str(entry["dimension"])

    question = entry.get("question")
    if question:
        meta["user_prompt"] = {"prompt": str(question).strip()}

    return prepare_parameter_metadata(meta)


def iter_nomenclature_parameters(
    parent_id: str,
    metadata: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(node_id, parameter_metadata)`` synthesized from nomenclature."""
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for entry in metadata.get("nomenclature", []) or []:
        if not isinstance(entry, dict):
            continue
        param = nomenclature_entry_to_parameter(entry, parent_id=parent_id)
        if param is None:
            continue
        node_id = str(param["id"])
        if node_id in seen:
            continue
        seen.add(node_id)
        out.append((node_id, param))
    return out
