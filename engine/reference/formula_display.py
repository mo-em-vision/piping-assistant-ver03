"""Load equation display strings from standards node equation files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_reader import StandardsReader


def load_formula_display(reader: StandardsReader, node_id: str) -> str | None:
    """Return the human-readable display equation for a calculation node."""
    node = reader.load(node_id)
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    for equation in equations:
        if isinstance(equation, dict) and equation.get("file"):
            path = node.path.parent / str(equation["file"])
            display = _display_from_equation_file(path)
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
        path = node.path.parent / str(equation["file"])
        if not path.exists():
            continue
        data = _parse_equation_frontmatter(path)
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
