"""Build ready-to-display blocks for an activated standards definition node."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from api.display_block_metadata import (
    DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW,
    DISPLAY_ROLE_ACTIVATION,
    tag_display_block,
)
from engine.reference.formula_display import (
    _resolve_equation_display_from_data,
    _resolve_equation_node_id,
    load_equation_context,
    resolve_equation_display_variables,
)
from engine.reference.node_types import is_section_node
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader


def build_activated_node_blocks(
    reader: StandardsReader,
    node_id: str,
    *,
    standard_label: str = "ASME B31.3",
) -> list[dict[str, Any]]:
    """Return ordered display blocks for a definition node at workflow start."""
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return []

    metadata = record.metadata
    node_type = str(metadata.get("type", ""))
    if is_section_node(metadata, node_type):
        blocks: list[dict[str, Any]] = []
        for ref in metadata.get("contains", []) or []:
            ref_id = str(ref)
            try:
                eq_record = reader.load(ref_id)
            except FileNotFoundError:
                continue
            if str(eq_record.metadata.get("type", "")) != "equation":
                continue
            display = str(
                eq_record.metadata.get("display_latex")
                or eq_record.metadata.get("sympy")
                or ""
            ).strip()
            if not display:
                continue
            paragraph = str(metadata.get("paragraph", "")).strip()
            block: dict[str, Any] = {
                "id": f"node-activation-equation-{ref_id}",
                "type": "equation",
                "display": display,
                "content": display,
            }
            if paragraph:
                block["nomenclature_reference"] = {
                    "node_id": node_id,
                    "label": f"§{paragraph}(b)",
                    "paragraph": paragraph,
                }
            tag_display_block(
                block,
                display_role=DISPLAY_ROLE_ACTIVATION,
                equation_node_id=ref_id,
                source_node_id=node_id,
                display_channel=DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW,
            )
            blocks.append(block)
        blocks.extend(_equation_blocks(reader, record, metadata, node_id))
        return blocks

    if node_type != "definition":
        return []

    blocks: list[dict[str, Any]] = []

    assumption_lines = _assumption_lines(metadata)
    if assumption_lines:
        assumption_text = "; ".join(assumption_lines)
        blocks.append(
            {
                "id": f"node-activation-assumptions-{node_id}",
                "type": "text",
                "title": None,
                "content": assumption_text,
                "variant": "assumption",
            }
        )

    blocks.extend(_equation_blocks(reader, record, metadata, node_id))

    return blocks


def _reference_links_from_metadata(
    metadata: dict[str, Any],
    reader: StandardsReader,
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in metadata.get("references", []) or []:
        if not isinstance(item, dict):
            continue
        ref_node_id = item.get("node_id")
        if not ref_node_id:
            continue
        node_id = str(ref_node_id)
        if node_id in seen:
            continue
        seen.add(node_id)
        try:
            ref_record = reader.load(node_id)
            paragraph = str(ref_record.metadata.get("paragraph", "")).strip()
            label = f"§{paragraph}" if paragraph else node_id
        except FileNotFoundError:
            label = node_id
            paragraph = ""
        links.append(
            {
                "node_id": node_id,
                "label": label,
                "paragraph": paragraph or None,
            }
        )

    for item in metadata.get("depends_on", []) or []:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id", ""))
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        try:
            ref_record = reader.load(node_id)
            paragraph = str(ref_record.metadata.get("paragraph", "")).strip()
            label = f"§{paragraph}" if paragraph else node_id
        except FileNotFoundError:
            label = node_id
            paragraph = ""
        links.append(
            {
                "node_id": node_id,
                "label": label,
                "paragraph": paragraph or None,
            }
        )

    return links


def _assumption_lines(metadata: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in metadata.get("assumptions", []) or []:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description", "")).strip()
        if description:
            lines.append(_collapse_whitespace(description))
    return lines


def _calculation_summary(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in metadata.get("references", []) or []:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason", "")).strip()
        if reason:
            parts.append(_collapse_whitespace(reason))

    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        for equation in subsection.get("equations", []) or []:
            if not isinstance(equation, dict):
                continue
            description = str(equation.get("description", "")).strip()
            if description:
                parts.append(_collapse_whitespace(description))

    if parts:
        return "\n".join(f"• {part}" for part in parts)

    purpose = str(metadata.get("purpose", "")).strip()
    return _collapse_whitespace(purpose) if purpose else ""


def _equation_blocks(
    reader: StandardsReader,
    record,
    metadata: dict[str, Any],
    node_id: str,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_displays: set[str] = set()

    equation_entries: list[dict[str, Any]] = []
    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        for equation in subsection.get("equations", []) or []:
            if isinstance(equation, dict):
                equation_entries.append(equation)

    for equation in metadata.get("equations", []) or []:
        if isinstance(equation, dict):
            equation_entries.append(equation)

    for index, equation in enumerate(equation_entries):
        file_rel = equation.get("file")
        data: dict[str, Any] = {}
        if file_rel:
            path = record.path.parent / str(file_rel)
            if path.exists():
                data = _parse_equation_frontmatter(path)
            else:
                text = reader.read_asset_text(record, str(file_rel))
                data, _ = split_frontmatter(text) if text else ({}, "")
        elif equation.get("source"):
            data, _ = split_frontmatter(str(equation["source"]))
        elif equation.get("display"):
            data = dict(equation)
        else:
            continue
        if isinstance(data, dict):
            merged = dict(equation)
            merged.update(data)
            data = merged
        display = str(data.get("display") or equation.get("display") or "").strip().strip('"')
        if not display or display in seen_displays:
            continue
        seen_displays.add(display)

        name = str(data.get("name") or equation.get("description") or "Governing equation").strip()
        resolved = _resolve_equation_display_from_data(reader, data, metadata)
        equation_node_id = str(data.get("id") or "").strip() or _resolve_equation_node_id(
            reader, str(data.get("key") or node_id)
        )
        equation_block: dict[str, Any] = {
            "id": f"node-activation-equation-{node_id}-{index}",
            "type": "equation",
            "title": name,
            "content": _display_to_latex(display),
            "display": display,
            "variables": resolved.get("variables") or [],
        }
        nomenclature_reference = resolved.get("nomenclature_reference")
        if nomenclature_reference:
            equation_block["nomenclature_reference"] = nomenclature_reference
        tag_display_block(
            equation_block,
            display_role=DISPLAY_ROLE_ACTIVATION,
            equation_node_id=equation_node_id or None,
            source_node_id=node_id,
            display_channel=DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW,
        )
        blocks.append(equation_block)

    if not blocks:
        context = load_equation_context(reader, node_id)
        display = context.get("display")
        if display:
            resolved = resolve_equation_display_variables(reader, node_id)
            equation_node_id = _resolve_equation_node_id(reader, node_id)
            equation_block: dict[str, Any] = {
                "id": f"node-activation-equation-{node_id}-fallback",
                "type": "equation",
                "title": str(context.get("name") or "Governing equation"),
                "content": _display_to_latex(str(display)),
                "display": str(display),
                "variables": resolved.get("variables") or [],
            }
            nomenclature_reference = resolved.get("nomenclature_reference")
            if nomenclature_reference:
                equation_block["nomenclature_reference"] = nomenclature_reference
            tag_display_block(
                equation_block,
                display_role=DISPLAY_ROLE_ACTIVATION,
                equation_node_id=equation_node_id,
                source_node_id=node_id,
                display_channel=DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW,
            )
            blocks.append(equation_block)

    return blocks


def _nomenclature_block(metadata: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    rows: list[dict[str, str]] = []
    for item in metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        description = str(item.get("description", "")).strip()
        if not symbol or not description:
            continue
        rows.append(
            {
                "symbol": symbol,
                "description": _collapse_whitespace(description),
            }
        )

    if not rows:
        return None

    return {
        "id": f"node-activation-nomenclature-{node_id}",
        "type": "table",
        "title": "Equation parameters",
        "columns": [
            {"key": "symbol", "label": "Symbol", "sortable": True},
            {"key": "description", "label": "Description", "sortable": True},
        ],
        "rows": rows,
        "searchable": True,
    }


def _equation_variable_rows(
    equation_data: dict[str, Any],
    metadata: dict[str, Any],
) -> list[dict[str, str]]:
    variables = equation_data.get("variables") or {}
    if not isinstance(variables, dict):
        return _symbols_to_variable_rows([], metadata)

    rows: list[dict[str, str]] = []
    nomenclature = {
        str(item.get("symbol", "")): item
        for item in (metadata.get("nomenclature", []) or [])
        if isinstance(item, dict)
    }

    for key, payload in variables.items():
        if not isinstance(payload, dict):
            continue
        symbol = str(payload.get("symbol") or key).strip()
        name = str(payload.get("description") or "").strip()
        if not name:
            entry = nomenclature.get(symbol)
            if entry:
                name = _collapse_whitespace(str(entry.get("description", "")))
        rows.append({"symbol": symbol, "name": name or symbol})

    return rows


def _symbols_to_variable_rows(
    symbols: list[str],
    metadata: dict[str, Any],
) -> list[dict[str, str]]:
    nomenclature = {
        str(item.get("symbol", "")): item
        for item in (metadata.get("nomenclature", []) or [])
        if isinstance(item, dict)
    }
    rows: list[dict[str, str]] = []
    for symbol in symbols:
        entry = nomenclature.get(symbol)
        name = _collapse_whitespace(str(entry.get("description", ""))) if entry else symbol
        rows.append({"symbol": symbol, "name": name})
    return rows


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


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _display_to_latex(display: str) -> str:
    text = display.strip()
    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
    return re.sub(r"\s+", " ", text)
