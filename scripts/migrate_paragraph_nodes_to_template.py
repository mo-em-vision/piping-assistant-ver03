#!/usr/bin/env python3
"""One-shot migration: B31.3 paragraph nodes to Paragraph Node template."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPH_DIR = ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes" / "paragraph"

PARAGRAPH_CLASS: dict[str, str] = {
    "304": "definition",
    "304.1": "definition",
    "304.3": "definition",
    "304.1.1": "definition",
    "304.1.2": "calculation_requirement",
    "304.1.3": "calculation_requirement",
    "302.3.3": "definition",
    "302.3.5": "definition",
    "304.3.1": "definition",
    "304.3.2": "definition",
    "304.3.3": "calculation_requirement",
}

INPUT_TO_PARAM: dict[str, str] = {
    "design_pressure": "PARAM-design-pressure",
    "outside_diameter": "PARAM-outside-diameter",
    "allowable_stress": "PARAM-allowable-stress",
    "weld_joint_efficiency": "PARAM-weld-joint-efficiency",
    "weld_joint_strength_reduction_factor_W": "PARAM-weld-strength-reduction-factor-W",
    "temperature_coefficient_Y": "PARAM-temperature-coefficient-Y",
    "corrosion_allowance": "PARAM-corrosion-allowance",
    "straight_pipe_section": "PARAM-straight-pipe-section",
    "pressure_design_case": "PARAM-pressure-design-case",
    "thin_wall": "PARAM-thin-wall-applicability",
    "casting_quality_factor": "PARAM-casting-quality-factor",
}

EXECUTION_KEYS = (
    "interactions",
    "assumptions",
    "provisional_assumptions",
    "inputs",
    "depends_on",
    "equations",
    "conditions",
    "kind",
    "outputs",
    "lookups",
    "notes",
)

STRIP_KEYS = frozenset(
    {
        "topic",
        "version",
        "created",
        "modified",
        "revision_year",
        "purpose",
        "engineering_intent",
        "subsections",
        "nomenclature",
        "trace",
        "report",
        "ai_hints",
        "interactions",
        "assumptions",
        "provisional_assumptions",
        "inputs",
        "depends_on",
        "equations",
        "conditions",
        "kind",
        "outputs",
        "lookups",
        "notes",
        "equations",
        "formulas",
    }
)

APPLICABILITY: dict[str, dict[str, Any]] = {
    "304.1.1": {
        "applies_when": [
            {"parameter": "PARAM-straight-pipe-section", "operator": "equals", "value": True},
        ],
    },
    "304.1.2": {
        "applies_when": [
            {"parameter": "PARAM-pressure-design-case", "operator": "equals", "value": "internal_pressure"},
            {"parameter": "PARAM-straight-pipe-section", "operator": "equals", "value": True},
        ],
    },
    "304.1.3": {
        "applies_when": [
            {"parameter": "PARAM-pressure-design-case", "operator": "equals", "value": "external_pressure"},
            {"parameter": "PARAM-straight-pipe-section", "operator": "equals", "value": True},
        ],
    },
}


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text
    meta = yaml.safe_load("\n".join(lines[1:end_index])) or {}
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return meta, body


def _compose(meta: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    body_text = body.rstrip()
    if body_text:
        return f"---\n{yaml_text}\n---\n\n{body_text}\n"
    return f"---\n{yaml_text}\n---\n"


def _id_to_key(node_id: str) -> str:
    return "b313_" + node_id.replace(".", "_")


def _collect_nomenclature(meta: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in meta.get("nomenclature", []) or []:
        if isinstance(item, dict):
            entries.append(item)
    for sub in meta.get("subsections", []) or []:
        if isinstance(sub, dict):
            for item in sub.get("nomenclature", []) or []:
                if isinstance(item, dict):
                    entries.append(item)
    return entries


def _collect_execution(meta: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in EXECUTION_KEYS:
        value = meta.get(key)
        if value:
            payload[key] = value
    return payload


def _introduced_parameters(nomenclature: list[dict[str, Any]]) -> list[str]:
    params: list[str] = []
    seen: set[str] = set()
    for item in nomenclature:
        input_id = str(item.get("input_id") or "")
        if not item.get("introduced_here") or not input_id:
            continue
        param = INPUT_TO_PARAM.get(input_id, f"PARAM-{input_id.replace('_', '-')}")
        if param not in seen:
            seen.add(param)
            params.append(param)
    return params


def _referenced_equations(meta: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for edge in meta.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type")) == "equation":
            target = str(edge.get("target") or "")
            if target and target not in seen:
                seen.add(target)
                refs.append(target)
    for eq in meta.get("equations", []) or []:
        if isinstance(eq, dict):
            eq_id = str(eq.get("id") or "")
            if eq_id and eq_id not in seen:
                seen.add(eq_id)
                refs.append(eq_id)
    return refs


def _template_limitations(meta: dict[str, Any]) -> list[dict[str, Any]] | None:
    limitations: list[dict[str, Any]] = []
    for item in meta.get("limitations", []) or []:
        if not isinstance(item, dict):
            continue
        lim_id = str(item.get("id") or "")
        description = str(item.get("condition") or item.get("description") or "").strip()
        if not lim_id and not description:
            continue
        entry: dict[str, Any] = {
            "id": lim_id or f"LIMIT-{item.get('parameter', 'unknown')}",
            "description": description,
        }
        parameter = item.get("parameter")
        if parameter:
            mapped = INPUT_TO_PARAM.get(str(parameter), None)
            if mapped:
                entry["related_parameter"] = mapped
        limitations.append(entry)
    return limitations or None


def _normalize_edges(meta: dict[str, Any]) -> list[dict[str, Any]]:
    edges = [dict(item) for item in meta.get("edges", []) or [] if isinstance(item, dict)]
    has_authority = any(
        str(edge.get("target")) == "AUTH-ASME-B31.3"
        for edge in edges
    )
    if not has_authority:
        edges.insert(
            0,
            {"type": "references", "target": "AUTH-ASME-B31.3", "role": "belongs_to_authority"},
        )
    return edges


def _status(meta: dict[str, Any]) -> str:
    raw = str(meta.get("status") or "active").lower()
    if raw in {"active", "draft", "superseded"}:
        return raw
    return "active"


def _description(meta: dict[str, Any], title: str) -> str:
    for key in ("description", "purpose"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return title


def migrate_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    node_id = str(meta.get("id") or path.stem)
    title = str(meta.get("title") or node_id)

    nomenclature = _collect_nomenclature(meta)
    execution = _collect_execution(meta)

    sidecar_dir = path.parent / node_id
    if nomenclature:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        nom_path = sidecar_dir / "nomenclature.yaml"
        nom_path.write_text(
            _compose({"nomenclature": nomenclature}, ""),
            encoding="utf-8",
        )
        print(f"  wrote {nom_path.relative_to(ROOT)}")

    if execution:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        exec_path = sidecar_dir / "execution.yaml"
        exec_path.write_text(_compose(execution, ""), encoding="utf-8")
        print(f"  wrote {exec_path.relative_to(ROOT)}")

    new_meta: dict[str, Any] = {
        "id": node_id,
        "type": "paragraph",
        "key": _id_to_key(node_id),
        "title": title,
        "authority": "AUTH-ASME-B31.3",
        "edition": 2024,
        "paragraph_number": node_id,
        "paragraph_class": PARAGRAPH_CLASS.get(node_id, "definition"),
        "description": _description(meta, title),
        "metadata": {
            "status": _status(meta),
            "node_version": 1,
            "source_revision_year": int(meta.get("revision_year") or 2024),
        },
        "edges": _normalize_edges(meta),
    }

    if node_id in APPLICABILITY:
        new_meta["applicability"] = APPLICABILITY[node_id]

    if nomenclature:
        introduced = _introduced_parameters(nomenclature)
        if introduced:
            new_meta["introduced_parameters"] = introduced

    referenced_eq = _referenced_equations(meta)
    if referenced_eq:
        new_meta["referenced_equations"] = referenced_eq

    limitations = _template_limitations(meta)
    if limitations:
        new_meta["limitations"] = limitations

    if node_id == "304.1.1" and execution.get("interactions"):
        new_meta["referenced_concepts"] = ["CONCEPT-pressure", "CONCEPT-wall-thickness"]

    path.write_text(_compose(new_meta, body), encoding="utf-8")
    print(f"migrated {path.name}")


def main() -> int:
    paths = sorted(PARAGRAPH_DIR.glob("*.yaml"))
    if not paths:
        print("No paragraph YAML files found", file=sys.stderr)
        return 1
    for path in paths:
        migrate_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
