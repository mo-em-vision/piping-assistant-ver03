#!/usr/bin/env python3
"""One-shot migration: B31.3 workflow nodes to Workflow Node template."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes" / "workflows"

INPUT_TO_PARAM: dict[str, str] = {
    "straight_pipe_section": "PARAM-straight-pipe-section",
    "pressure_design_case": "PARAM-pressure-design-case",
    "design_pressure": "PARAM-design-pressure",
    "nominal_pipe_size": "PARAM-nominal-pipe-size",
    "outside_diameter": "PARAM-outside-diameter",
    "material": "PARAM-material-grade",
    "design_temperature": "PARAM-design-temperature",
    "external_design_pressure": "PARAM-external-design-pressure",
    "joint_category": "PARAM-pipe-construction-type",
    "weld_joint_efficiency": "PARAM-weld-joint-efficiency",
    "weld_joint_strength_reduction_factor_W": "PARAM-weld-strength-reduction-factor-W",
    "temperature_coefficient_Y": "PARAM-temperature-coefficient-Y",
    "corrosion_allowance": "PARAM-corrosion-allowance",
    "minimum_required_thickness": "PARAM-minimum-required-thickness",
    "pipe_schedule": "PARAM-pipe-schedule",
    "actual_wall_thickness": "PARAM-actual-wall-thickness",
    "geometry_input_mode": "PARAM-geometry-input-mode",
    "allowable_stress": "PARAM-allowable-stress",
    "mawp": "PARAM-mawp",
}

RUNTIME_KEYS = (
    "navigation",
    "assumptions",
    "interactions",
    "provisional_assumptions",
    "inputs",
    "equations",
    "conditions",
    "nomenclature",
    "texts",
    "documentation",
    "suggested_workflows",
    "goal_output",
    "engineering_intent",
    "slug",
)

STRIP_KEYS = frozenset(
    {
        "title",
        "version",
        "status",
        "purpose",
        "engineering_intent",
        "slug",
        "navigation",
        "assumptions",
        "interactions",
        "provisional_assumptions",
        "inputs",
        "equations",
        "conditions",
        "nomenclature",
        "texts",
        "documentation",
        "suggested_workflows",
        "goal_output",
    }
)

PIPE_WALL_TEMPLATE: dict[str, Any] = {
    "domain": ["piping"],
    "expected_authorities": ["AUTH-ASME-B31.3", "AUTH-ASME-B36.10M"],
    "entry_points": [
        {"paragraph": "304.1.1", "role": "definition_anchor"},
        {"paragraph": "304.1.2", "role": "internal_pressure_branch"},
        {"paragraph": "304.1.3", "role": "external_pressure_branch"},
    ],
    "expected_parameters": [
        "PARAM-straight-pipe-section",
        "PARAM-pressure-design-case",
        "PARAM-design-pressure",
        "PARAM-nominal-pipe-size",
        "PARAM-outside-diameter",
        "PARAM-material-grade",
        "PARAM-design-temperature",
        "PARAM-external-design-pressure",
        "PARAM-pipe-construction-type",
        "PARAM-weld-joint-efficiency",
        "PARAM-weld-strength-reduction-factor-W",
        "PARAM-temperature-coefficient-Y",
        "PARAM-corrosion-allowance",
        "PARAM-minimum-required-thickness",
    ],
    "goal_expansion": {
        "root_goal": {
            "goal_class": "calculation_goal",
            "target_parameter": "PARAM-minimum-required-thickness",
        },
    },
    "phases": [
        {
            "key": "expansion_assumptions",
            "purpose": "Confirm assumptions required before graph expansion.",
            "required_parameters": ["PARAM-straight-pipe-section"],
        },
        {
            "key": "path_decisions",
            "purpose": "Select applicable pressure loading branch.",
            "required_parameters": ["PARAM-pressure-design-case"],
        },
        {
            "key": "parameter_gathering",
            "purpose": "Collect design conditions and geometry.",
            "required_parameters": [
                "PARAM-design-pressure",
                "PARAM-nominal-pipe-size",
                "PARAM-outside-diameter",
                "PARAM-material-grade",
                "PARAM-design-temperature",
                "PARAM-external-design-pressure",
            ],
        },
        {
            "key": "coefficient_resolution",
            "purpose": "Resolve coefficients required by the pressure design equation.",
            "required_parameters": [
                "PARAM-pipe-construction-type",
                "PARAM-weld-joint-efficiency",
                "PARAM-weld-strength-reduction-factor-W",
                "PARAM-temperature-coefficient-Y",
            ],
        },
        {
            "key": "execution_assumptions",
            "purpose": "Resolve allowances and post-calculation assumptions.",
            "required_parameters": [],
        },
        {
            "key": "definition_equation_completion",
            "purpose": "Complete definition and equation inputs.",
            "required_parameters": ["PARAM-corrosion-allowance"],
        },
    ],
    "branches": [
        {
            "key": "internal_pressure",
            "selected_when": {
                "parameter": "PARAM-pressure-design-case",
                "value": "internal_pressure",
            },
            "entry_point": "304.1.2",
        },
        {
            "key": "external_pressure",
            "selected_when": {
                "parameter": "PARAM-pressure-design-case",
                "value": "external_pressure",
            },
            "entry_point": "304.1.3",
        },
    ],
    "applicability": {
        "applies_to": ["CONCEPT-pipe", "CONCEPT-wall-thickness", "CONCEPT-pressure"],
    },
    "report": {
        "report_type": "calculation_report",
        "required_sections": [
            "objective",
            "authority_context",
            "inputs",
            "equations",
            "calculations",
            "validation",
            "warnings",
            "conclusion",
        ],
    },
}

MAWP_TEMPLATE: dict[str, Any] = {
    "domain": ["piping"],
    "expected_authorities": ["AUTH-ASME-B31.3", "AUTH-ASME-B36.10M"],
    "entry_points": [
        {"paragraph": "304.1.2", "role": "definition_anchor"},
    ],
    "expected_parameters": [
        "PARAM-straight-pipe-section",
        "PARAM-geometry-input-mode",
        "PARAM-nominal-pipe-size",
        "PARAM-pipe-schedule",
        "PARAM-outside-diameter",
        "PARAM-actual-wall-thickness",
        "PARAM-corrosion-allowance",
        "PARAM-material-grade",
        "PARAM-design-temperature",
        "PARAM-pipe-construction-type",
        "PARAM-weld-joint-efficiency",
        "PARAM-weld-strength-reduction-factor-W",
        "PARAM-temperature-coefficient-Y",
        "PARAM-allowable-stress",
        "PARAM-mawp",
    ],
    "goal_expansion": {
        "root_goal": {
            "goal_class": "calculation_goal",
            "target_parameter": "PARAM-mawp",
        },
    },
    "phases": [
        {
            "key": "expansion_assumptions",
            "purpose": "Confirm assumptions required before graph expansion.",
            "required_parameters": ["PARAM-straight-pipe-section"],
        },
        {
            "key": "path_decisions",
            "purpose": "Select geometry input mode.",
            "required_parameters": ["PARAM-geometry-input-mode"],
        },
        {
            "key": "parameter_gathering",
            "purpose": "Collect geometry and material inputs.",
            "required_parameters": [
                "PARAM-nominal-pipe-size",
                "PARAM-pipe-schedule",
                "PARAM-outside-diameter",
                "PARAM-actual-wall-thickness",
                "PARAM-corrosion-allowance",
                "PARAM-material-grade",
                "PARAM-design-temperature",
            ],
        },
        {
            "key": "coefficient_resolution",
            "purpose": "Resolve coefficients required by the MAWP equation.",
            "required_parameters": [
                "PARAM-pipe-construction-type",
                "PARAM-weld-joint-efficiency",
                "PARAM-weld-strength-reduction-factor-W",
                "PARAM-temperature-coefficient-Y",
            ],
        },
        {
            "key": "execution_assumptions",
            "purpose": "Resolve execution assumptions.",
            "required_parameters": [],
        },
        {
            "key": "definition_equation_completion",
            "purpose": "Complete definition and equation inputs.",
            "required_parameters": [],
        },
    ],
    "applicability": {
        "applies_to": ["CONCEPT-pipe", "CONCEPT-pressure", "CONCEPT-mawp"],
    },
    "report": {
        "report_type": "calculation_report",
        "required_sections": [
            "objective",
            "authority_context",
            "inputs",
            "equations",
            "calculations",
            "validation",
            "warnings",
            "conclusion",
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


def _status(meta: dict[str, Any]) -> str:
    raw = str(meta.get("status") or "draft").lower()
    if raw in {"active", "draft", "superseded"}:
        return raw
    return "draft"


def _description(meta: dict[str, Any], title: str) -> str:
    for key in ("description", "purpose"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return title.strip()


def _collect_runtime(meta: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in RUNTIME_KEYS:
        value = meta.get(key)
        if value:
            payload[key] = value
    return payload


def _normalize_edges(meta: dict[str, Any], *, node_id: str) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for item in meta.get("edges", []) or []:
        if not isinstance(item, dict):
            continue
        edge = dict(item)
        edge_type = str(edge.get("type") or "")
        target = str(edge.get("target") or "")
        if edge_type == "requires" and target == node_id:
            continue
        if edge_type == "depends_on" and target == node_id:
            continue
        edges.append(edge)

    if node_id == "WF-PIPE-WALL-THICKNESS":
        if not any(str(e.get("target")) == "304.1.1" for e in edges):
            edges.append(
                {"type": "references", "target": "304.1.1", "role": "starts_from_paragraph"},
            )
    if node_id == "WF-MAWP":
        equation_targets = {str(e.get("target")) for e in edges if str(e.get("type")) == "equation"}
        for eq_id in ("asme_b313_pressure_design_thickness", "asme_b313_mawp_pressure"):
            if eq_id not in equation_targets:
                edges.append({"type": "equation", "target": eq_id})
    return edges


def _migrate(path: Path, template_extra: dict[str, Any]) -> None:
    meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    node_id = str(meta.get("id") or path.stem)
    key = str(meta.get("slug") or meta.get("engineering_intent") or path.stem.replace("-", "_"))
    title = str(meta.get("title") or meta.get("name") or key)

    runtime = _collect_runtime(meta)
    sidecar_dir = WORKFLOW_DIR / node_id
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = sidecar_dir / "runtime.yaml"
    runtime_path.write_text(
        yaml.safe_dump(runtime, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    new_meta: dict[str, Any] = {
        "id": node_id,
        "type": "workflow",
        "key": key,
        "name": title,
        "workflow_class": "design_calculation",
        "description": _description(meta, title),
        **template_extra,
        "edges": _normalize_edges(meta, node_id=node_id),
        "metadata": {
            "status": _status(meta),
            "version": 1,
        },
    }
    for key_name in STRIP_KEYS:
        new_meta.pop(key_name, None)

    path.write_text(_compose(new_meta, body), encoding="utf-8")
    print(f"migrated {path.name} -> {sidecar_dir / 'runtime.yaml'}")


def main() -> int:
    mapping = {
        "pipe-wall-thickness.yaml": PIPE_WALL_TEMPLATE,
        "mawp.yaml": MAWP_TEMPLATE,
    }
    for filename, template in mapping.items():
        path = WORKFLOW_DIR / filename
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 1
        _migrate(path, template)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
