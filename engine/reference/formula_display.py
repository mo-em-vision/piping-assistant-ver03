"""Load equation display strings from standards node equation files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from engine.graph.assumption_checker import field_value
from engine.graph.param_priority import require_target_id
from engine.reference.embedded_nodes import find_embedded_body
from engine.reference.node_types import is_section_node
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader


def _nomenclature_section_label(paragraph: str, fallback: str) -> str:
    paragraph = str(paragraph or "").strip()
    if not paragraph:
        return f"§{fallback}"
    if re.match(r".+-[a-z]$", paragraph):
        return f"§{paragraph}"
    if paragraph.endswith("(b)"):
        return f"§{paragraph}"
    return f"§{paragraph}(b)"


def load_formula_display(reader: StandardsReader, node_id: str) -> str | None:
    """Return the human-readable display equation for a calculation node."""
    node = reader.load(node_id)
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    for equation in equations:
        if isinstance(equation, dict) and equation.get("file"):
            display = _display_from_equation(reader, node, str(equation["file"]))
            if display:
                return display
    primary = _primary_equation_data(reader, node_id)
    if primary:
        display = str(primary.get("display", "")).strip().strip('"')
        return display or None
    return None


def load_equation_context(
    reader: StandardsReader,
    node_id: str,
    *,
    task_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load display formula, name, and ordered variable symbols for a node."""
    resolved_id = _resolve_equation_node_id(reader, node_id, task_facts=task_facts)
    node = reader.load(resolved_id)
    if str(node.metadata.get("type", "")) == "equation":
        return _equation_context_from_micro_node(reader, node)

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

    if not display or not variables:
        primary = _primary_equation_data(reader, resolved_id)
        if primary:
            display = display or str(primary.get("display", "")).strip().strip('"') or None
            name = name or str(primary.get("name", "")).strip() or None
            var_block = primary.get("variables") or {}
            if isinstance(var_block, dict) and not variables:
                variables = list(var_block.keys())

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


def _resolve_equation_node_id(
    reader: StandardsReader,
    node_id: str,
    *,
    task_facts: dict[str, Any] | None = None,
) -> str:
    record = reader.load(node_id)
    node_type = str(record.metadata.get("type", ""))
    if node_type == "equation":
        return node_id

    equation_id = _equation_reference_from_edges(
        reader,
        record.metadata,
        task_facts=task_facts,
    )
    if equation_id:
        return equation_id

    if not is_section_node(record.metadata, node_type):
        return node_id
    for ref in record.metadata.get("contains", []) or []:
        ref_id = str(ref)
        try:
            child = reader.load(ref_id)
        except FileNotFoundError:
            continue
        if str(child.metadata.get("type", "")) == "equation":
            return ref_id
    return node_id


def _equation_display_text(metadata: dict[str, Any]) -> str | None:
    display = metadata.get("display_latex") or metadata.get("sympy")
    if display:
        text = str(display).strip()
        return text or None
    nested = metadata.get("display")
    if isinstance(nested, dict):
        text = nested.get("text") or nested.get("latex")
        if text:
            return str(text).strip() or None
    if isinstance(nested, str) and nested.strip():
        return nested.strip()
    return None


def _equation_reference_from_edges(
    reader: StandardsReader,
    metadata: dict[str, Any],
    *,
    task_facts: dict[str, Any] | None = None,
) -> str | None:
    facts = task_facts or {}
    for edge in metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type", "")) != "references_equation":
            continue
        target = str(edge.get("target", "")).strip()
        if not target:
            continue
        when = edge.get("when")
        if isinstance(when, dict) and not _edge_when_applies(when, facts):
            continue
        try:
            target_record = reader.load(target)
        except FileNotFoundError:
            continue
        if str(target_record.metadata.get("type", "")) == "equation":
            return target
    return None


def _edge_when_applies(when: dict[str, Any], facts: dict[str, Any]) -> bool:
    field_name = str(when.get("field", "")).strip()
    if when.get("absent"):
        return field_value(field_name, facts) is None
    if when.get("present"):
        return field_value(field_name, facts) is not None
    allowed = when.get("in")
    if field_name and isinstance(allowed, list):
        value = field_value(field_name, facts)
        return value in allowed
    equals = when.get("equals")
    if field_name and equals is not None:
        return field_value(field_name, facts) == equals
    return True


def _equation_context_from_micro_node(reader: StandardsReader, node: Any) -> dict[str, Any]:
    meta = node.metadata
    display = _equation_display_text(meta)
    variables: list[str] = []
    for ref in meta.get("requires", []) or []:
        ref_id = require_target_id(ref)
        if not ref_id:
            continue
        try:
            param = reader.load(ref_id)
        except FileNotFoundError:
            continue
        symbol = str(param.metadata.get("symbol") or "").strip()
        if symbol and symbol not in variables:
            variables.append(symbol)
    return {
        "display": display,
        "name": str(meta.get("equation_id") or meta.get("title") or "").strip() or None,
        "variables": variables,
        "purpose": str(meta.get("purpose", "")).strip(),
        "node_id": node.node_id,
        "title": str(meta.get("title", "")).strip(),
    }


def resolve_equation_display_variables(
    reader: StandardsReader,
    node_id: str,
) -> dict[str, Any]:
    """Resolve equation variable rows and nomenclature reference for display blocks."""
    resolved_id = _resolve_equation_node_id(reader, node_id)
    node = reader.load(resolved_id)
    if str(node.metadata.get("type", "")) == "equation":
        section_id = node_id if node_id != resolved_id else (_section_for_equation(reader, resolved_id) or node_id)
        nomenclature_ref = _nomenclature_section_for(reader, section_id) or section_id
        equation_data = _micro_equation_display_data(reader, node)
        result = _resolve_equation_display_from_data(reader, equation_data, node.metadata)
        if result.get("nomenclature_reference") is None and nomenclature_ref:
            section = reader.load(nomenclature_ref)
            paragraph = str(
                section.metadata.get("paragraph")
                or section.metadata.get("paragraph_number")
                or ""
            ).strip()
            if paragraph:
                result["nomenclature_reference"] = {
                    "node_id": nomenclature_ref,
                    "label": _nomenclature_section_label(paragraph, nomenclature_ref),
                    "paragraph": paragraph,
                }
        return result
    equation_data = _primary_equation_data(reader, resolved_id)
    if not equation_data:
        return {"variables": [], "nomenclature_reference": None}
    section_id = resolved_id if is_section_node(node.metadata) else node_id
    result = _resolve_equation_display_from_data(reader, equation_data, node.metadata)
    if result.get("nomenclature_reference") is None and section_id != resolved_id:
        section = reader.load(section_id)
        paragraph = str(
            section.metadata.get("paragraph")
            or section.metadata.get("paragraph_number")
            or ""
        ).strip()
        if paragraph:
            result["nomenclature_reference"] = {
                "node_id": section_id,
                "label": _nomenclature_section_label(paragraph, section_id),
                "paragraph": paragraph,
            }
    return result


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

    deduped_rows: list[dict[str, str]] = []
    seen_symbols: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol") or "").strip()
        if not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        deduped_rows.append(row)

    return {
        "variables": deduped_rows,
        "nomenclature_reference": _nomenclature_reference_link(reader, nomenclature_ref),
    }


def _primary_equation_data(reader: StandardsReader, node_id: str) -> dict[str, Any]:
    resolved_id = _resolve_equation_node_id(reader, node_id)
    node = reader.load(resolved_id)
    if str(node.metadata.get("type", "")) == "equation":
        return _micro_equation_display_data(reader, node)
    for child_id in node.metadata.get("contains", []) or []:
        child = str(child_id).strip()
        if "eq" not in child.lower():
            continue
        body = find_embedded_body(node.metadata, child)
        if body is None:
            slug = child.split("B313-eq-", 1)[-1].replace("-", "_") if "B313-eq-" in child else child
            body = find_embedded_body(node.metadata, f"equations/{slug}.md")
        if body is None:
            continue
        metadata, _ = split_frontmatter(body)
        if isinstance(metadata, dict) and metadata:
            return metadata
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    preferred: dict[str, Any] = {}
    fallback: dict[str, Any] = {}
    for equation in equations:
        if not isinstance(equation, dict):
            continue
        eq_id = str(equation.get("id") or "").strip()
        if eq_id:
            try:
                eq_record = reader.load(eq_id)
                data = dict(eq_record.metadata)
            except FileNotFoundError:
                data = {}
        else:
            data = {}
        if not data:
            file_ref = str(equation.get("file") or "").strip()
            if file_ref:
                text = reader.read_asset_text(node, file_ref)
                if text:
                    metadata, _ = split_frontmatter(text)
                    if isinstance(metadata, dict) and metadata:
                        data = metadata
        if not data and equation.get("source"):
            metadata, _ = split_frontmatter(str(equation["source"]))
            if isinstance(metadata, dict) and metadata:
                data = metadata
        if not data:
            continue
        executor = str(data.get("executor") or "").strip()
        eq_id = str(equation.get("id") or data.get("id") or "").strip()
        if (
            executor == "calculate_wall_thickness"
            or str(data.get("equation_id") or "") == "wall_thickness"
            or eq_id in {"asme_b313_304_1_2_eq_3a", "asme_b313_304_1_2_wall_thickness"}
        ):
            return data
        if not preferred:
            preferred = data
        if not fallback:
            fallback = data
    if preferred:
        return preferred
    if fallback:
        return fallback
    return {}


def _micro_equation_display_data(reader: StandardsReader, node: Any) -> dict[str, Any]:
    variables: dict[str, dict[str, str]] = {}
    for key, payload in (node.metadata.get("variables") or {}).items():
        if not isinstance(payload, dict):
            continue
        symbol = str(payload.get("symbol") or key).strip()
        if not symbol:
            continue
        variables[symbol] = {
            "symbol": symbol,
            "description": _collapse_whitespace(
                str(payload.get("description") or payload.get("name") or symbol)
            ),
            "unit": str(payload.get("unit") or "dimensionless"),
        }
    section_id = _section_for_equation(reader, node.node_id)
    legacy_inputs: dict[str, dict[str, Any]] = {}
    if section_id:
        section = reader.load(section_id)
        for item in section.metadata.get("inputs", []) or []:
            if isinstance(item, dict) and item.get("id"):
                legacy_inputs[str(item["id"])] = item
    for ref in node.metadata.get("requires", []) or []:
        ref_id = require_target_id(ref)
        if not ref_id and isinstance(ref, dict) and ref.get("symbol"):
            symbol = str(ref["symbol"]).strip()
            if symbol and symbol not in variables:
                variables[symbol] = {
                    "symbol": symbol,
                    "description": _collapse_whitespace(
                        str(ref.get("description") or symbol)
                    ),
                    "unit": str(ref.get("unit") or "dimensionless"),
                }
            continue
        if not ref_id:
            continue
        try:
            param = reader.load(ref_id)
        except FileNotFoundError:
            continue
        input_id = str(param.metadata.get("input_id") or ref)
        symbol = str(param.metadata.get("symbol") or input_id)
        legacy = legacy_inputs.get(input_id, {})
        description = _collapse_whitespace(
            str(
                legacy.get("description")
                or param.metadata.get("description")
                or param.metadata.get("title")
                or symbol
            )
        )
        variables[input_id] = {
            "symbol": symbol,
            "description": description,
            "unit": str(legacy.get("unit") or param.metadata.get("unit", "dimensionless")),
        }
    nomenclature_ref = str(node.metadata.get("nomenclature_ref") or "").strip()
    if not nomenclature_ref and section_id:
        nomenclature_ref = _nomenclature_section_for(reader, section_id) or section_id
    return {
        "variables": variables,
        "nomenclature_ref": nomenclature_ref,
        "display": str(
            node.metadata.get("display_latex") or node.metadata.get("sympy") or ""
        ).strip(),
    }


def _section_for_equation(reader: StandardsReader, equation_id: str) -> str | None:
    equation = reader.load(equation_id)
    node_dir = equation.path.parent
    if node_dir.name == "equations":
        node_dir = node_dir.parent
    for name in ("node.yaml", "node.yml", "node.md"):
        candidate = node_dir / name
        if not candidate.is_file():
            continue
        from engine.reference.standards_markdown import split_frontmatter

        metadata, _ = split_frontmatter(candidate.read_text(encoding="utf-8"))
        section_id = str(metadata.get("id") or "").strip()
        if section_id:
            return section_id
    return None


def _nomenclature_section_for(reader: StandardsReader, section_id: str) -> str | None:
    try:
        section = reader.load(section_id)
    except FileNotFoundError:
        return None
    for item in section.metadata.get("depends_on", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("dependency_type", "")) == "reference" and item.get("node_id"):
            return str(item["node_id"])
    return section_id


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

    paragraph = str(
        record.metadata.get("paragraph")
        or record.metadata.get("paragraph_number")
        or ""
    ).strip()
    if paragraph.endswith("(b)"):
        label = f"§{paragraph}"
    else:
        label = _nomenclature_section_label(paragraph, nomenclature_ref)
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
