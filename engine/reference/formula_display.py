"""Load equation display strings from standards node equation files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader


def load_formula_display(reader: StandardsReader, node_id: str) -> str | None:
    """Return the human-readable display equation for a calculation node."""
    node = reader.load(node_id)
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    for equation in equations:
        if isinstance(equation, dict) and equation.get("file"):
            display = _display_from_equation(reader, node, str(equation["file"]))
            if display:
                return display
    return None


def load_equation_context(reader: StandardsReader, node_id: str) -> dict[str, Any]:
    """Load display formula, name, and ordered variable symbols for a node."""
    node = reader.load(node_id)
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    display: str | None = None
    name: str | None = None
    variables: list[str] = []
    purpose = str(node.metadata.get("purpose", "")).strip()

    for equation in equations:
        if not isinstance(equation, dict) or not equation.get("file"):
            continue
        file_ref = str(equation["file"])
        path = reader.resolve_asset_path(node, file_ref)
        if path is not None and path.is_file():
            data = _parse_equation_frontmatter(path)
        else:
            text = reader.read_asset_text(node, file_ref)
            metadata, _ = split_frontmatter(text) if text else ({}, "")
            data = metadata if isinstance(metadata, dict) else {}
        if data:
            display = display or str(data.get("display", "")).strip().strip('"') or None
            name = name or str(data.get("name", "")).strip() or None
            var_block = data.get("variables") or {}
            if isinstance(var_block, dict):
                variables = list(var_block.keys())

    if not display:
        display = load_formula_display(reader, node_id)

    if not variables:
        for spec in node.metadata.get("inputs", []) or []:
            if isinstance(spec, dict) and spec.get("name"):
                sym = str(spec["name"])
                if sym not in variables and sym not in {"NPS", "joint_category"}:
                    variables.append(sym)

    return {
        "display": display,
        "name": name,
        "variables": variables,
        "purpose": purpose,
        "node_id": node_id,
        "title": str(node.metadata.get("title", "")).strip(),
    }


def resolve_equation_display_variables(
    reader: StandardsReader,
    node_id: str,
) -> dict[str, Any]:
    """Resolve equation variable rows and nomenclature reference for display blocks."""
    node = reader.load(node_id)
    equation_data = _primary_equation_data(reader, node_id)
    if not equation_data:
        return {"variables": [], "nomenclature_reference": None}
    return _resolve_equation_display_from_data(reader, equation_data, node.metadata)


def _resolve_equation_display_from_data(
    reader: StandardsReader,
    equation_data: dict[str, Any],
    node_metadata: dict[str, Any],
) -> dict[str, Any]:
    from engine.reference.nomenclature_resolver import (
        entry_for_symbol,
        load_nomenclature,
        load_nomenclature_for_node,
    )

    nomenclature_ref = str(equation_data.get("nomenclature_ref", "")).strip()
    nomenclature: dict[str, Any] = {}
    if nomenclature_ref:
        nomenclature = load_nomenclature(reader, nomenclature_ref)
    nomenclature.update(load_nomenclature_for_node(reader, node_metadata))

    variables_block = equation_data.get("variables") or {}
    if not isinstance(variables_block, dict):
        variables_block = {}

    rows: list[dict[str, str]] = []
    for key, payload in variables_block.items():
        if not isinstance(payload, dict):
            continue
        symbol = str(payload.get("symbol") or key).strip()
        if not symbol:
            continue
        name = _resolve_variable_description(
            payload,
            nomenclature=nomenclature,
            symbol=symbol,
            key=str(key),
        )
        row: dict[str, str] = {"symbol": symbol, "name": name}
        unit = str(payload.get("unit", "")).strip()
        if unit and unit != "dimensionless":
            row["unit"] = unit
        rows.append(row)

    return {
        "variables": rows,
        "nomenclature_reference": _nomenclature_reference_link(reader, nomenclature_ref),
    }


def _primary_equation_data(reader: StandardsReader, node_id: str) -> dict[str, Any]:
    node = reader.load(node_id)
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    for equation in equations:
        if not isinstance(equation, dict) or not equation.get("file"):
            continue
        path = node.path.parent / str(equation["file"])
        if not path.exists():
            continue
        data = _parse_equation_frontmatter(path)
        if data:
            return data
    return {}


def _resolve_variable_description(
    payload: dict[str, Any],
    *,
    nomenclature: dict[str, Any],
    symbol: str,
    key: str,
) -> str:
    from engine.reference.nomenclature_resolver import entry_for_symbol

    description = _collapse_whitespace(str(payload.get("description", "")).strip())
    if description:
        return description

    entry = entry_for_symbol(nomenclature, symbol=symbol, input_id=key)
    if entry is not None and entry.description:
        return _collapse_whitespace(entry.description)

    return symbol


def _nomenclature_reference_link(
    reader: StandardsReader,
    nomenclature_ref: str,
) -> dict[str, str] | None:
    if not nomenclature_ref:
        return None
    try:
        record = reader.load(nomenclature_ref)
    except FileNotFoundError:
        return {"node_id": nomenclature_ref, "label": nomenclature_ref}

    paragraph = str(record.metadata.get("paragraph", "")).strip()
    label = f"§{paragraph}(b)" if paragraph else nomenclature_ref
    return {
        "node_id": nomenclature_ref,
        "label": label,
        "paragraph": paragraph or None,
    }


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _display_from_equation(reader: StandardsReader, node, file_ref: str) -> str | None:
    path = reader.resolve_asset_path(node, file_ref)
    if path is not None and path.is_file():
        return _display_from_equation_file(path)
    text = reader.read_asset_text(node, file_ref)
    if not text:
        return None
    metadata, _ = split_frontmatter(text)
    if isinstance(metadata, dict) and metadata.get("display"):
        return str(metadata["display"]).strip().strip('"')
    for line in text.splitlines():
        if line.strip().startswith("display:"):
            return line.split("display:", 1)[1].strip().strip('"')
    return None


def _display_from_equation_file(path: Path) -> str | None:
    data = _parse_equation_frontmatter(path)
    if data and data.get("display"):
        return str(data["display"]).strip().strip('"')
    if path.exists() and "display:" in path.read_text(encoding="utf-8"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("display:"):
                return line.split("display:", 1)[1].strip().strip('"')
    return None


def _parse_equation_frontmatter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
