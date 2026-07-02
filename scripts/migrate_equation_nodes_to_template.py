#!/usr/bin/env python3
"""One-shot migration: ASME B31.3 equations to Equation Node template."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3"
EQUATION_DIR = PACK / "nodes" / "equation"
PARAGRAPH_DIR = PACK / "nodes" / "paragraph"
WORKFLOW_DIR = PACK / "nodes" / "workflows"

SYMBOL_TO_PARAM: dict[str, tuple[str, str]] = {
    "P": ("PARAM-design-pressure", "Internal design gage pressure"),
    "D": ("PARAM-outside-diameter", "Outside diameter of pipe"),
    "S": ("PARAM-allowable-stress", "Allowable stress"),
    "E": ("PARAM-weld-joint-efficiency", "Joint efficiency"),
    "W": ("PARAM-weld-strength-reduction-factor-W", "Weld strength reduction factor"),
    "Y": ("PARAM-temperature-coefficient-Y", "Temperature coefficient Y"),
    "c": ("PARAM-corrosion-allowance", "Corrosion allowance"),
    "t": ("PARAM-required-wall-thickness", "Pressure design thickness"),
    "t_m": ("PARAM-minimum-required-thickness", "Minimum required thickness"),
    "t_actual": ("PARAM-actual-wall-thickness", "Actual wall thickness"),
    "MAWP": ("PARAM-mawp", "Maximum allowable working pressure"),
    "d": ("PARAM-inside-diameter", "Inside diameter"),
}

OUTPUT_SYMBOL_TO_PARAM: dict[str, tuple[str, str]] = {
    "t": ("PARAM-required-wall-thickness", "Pressure design thickness"),
    "t_m": ("PARAM-minimum-required-thickness", "Minimum required thickness"),
    "MAWP": ("PARAM-mawp", "Maximum allowable working pressure"),
    "S_A": ("PARAM-allowable-displacement-stress-range", "Allowable displacement stress range"),
    "f": ("PARAM-stress-range-factor", "Stress range factor"),
    "A_1": ("PARAM-required-reinforcement-area", "Required reinforcement area"),
    "reinforcement_adequate": ("PARAM-reinforcement-adequate", "Reinforcement adequacy"),
    "A_2": ("PARAM-run-excess-thickness-area", "Run excess thickness area"),
    "A_3": ("PARAM-branch-excess-thickness-area", "Branch excess thickness area"),
}

LEGACY_ID_MAP: dict[str, str] = {
    "304.1.1-eq-2": "asme_b313_304_1_1_eq_2",
    "B313-eq-2": "asme_b313_304_1_1_eq_2",
    "eq-2": "asme_b313_304_1_1_eq_2",
    "304.1.2": "asme_b313_304_1_2_wall_thickness",
    "wall_thickness": "asme_b313_304_1_2_wall_thickness",
    "B313-eq-wall-thickness": "asme_b313_304_1_2_wall_thickness",
    "WF-MAWP": "asme_b313_mawp_pressure",
    "mawp_pressure": "asme_b313_mawp_pressure",
    "B313-eq-mawp": "asme_b313_mawp_pressure",
    "thick_wall_y": "asme_b313_thick_wall_y",
    "pressure_design_thickness": "asme_b313_pressure_design_thickness",
    "eq-1a": "asme_b313_302_3_5_eq_1a",
    "eq-1b": "asme_b313_302_3_5_eq_1b",
    "eq-1c": "asme_b313_302_3_5_eq_1c",
    "eq-6": "asme_b313_304_3_3_eq_6",
    "eq-6a": "asme_b313_304_3_3_eq_6a",
    "eq-7": "asme_b313_304_3_3_eq_7",
    "eq-8": "asme_b313_304_3_3_eq_8",
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
    return meta if isinstance(meta, dict) else {}, body


def _compose(meta: dict[str, Any], body: str = "") -> str:
    yaml_text = yaml.safe_dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    body_text = body.rstrip()
    if body_text:
        return f"---\n{yaml_text}\n---\n\n{body_text}\n"
    return f"---\n{yaml_text}\n---\n"


def _parse_embedded_source(item: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source = item.get("source")
    if isinstance(source, str) and source.strip().startswith("---"):
        return _split_frontmatter(source)
    return {}, ""


def _display_block(meta: dict[str, Any]) -> dict[str, str]:
    display = meta.get("display")
    if isinstance(display, dict):
        return display
    text = str(display or meta.get("equation") or "").strip()
    if not text:
        return {}
    return {"text": text}


def _requires_from_variables(variables: dict[str, Any]) -> list[dict[str, Any]]:
    requires: list[dict[str, Any]] = []
    for _key, spec in (variables or {}).items():
        if not isinstance(spec, dict):
            continue
        symbol = str(spec.get("symbol") or _key)
        entry: dict[str, Any] = {
            "symbol": symbol,
            "required": True,
            "description": str(spec.get("description") or ""),
        }
        mapped = SYMBOL_TO_PARAM.get(symbol)
        if mapped:
            entry["parameter"] = mapped[0]
        requires.append(entry)
    return requires


def _calculates_from_outputs(outputs: list[Any], variables: dict[str, Any]) -> list[dict[str, Any]]:
    calculates: list[dict[str, Any]] = []
    for item in outputs or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "")
        if not symbol:
            continue
        entry: dict[str, Any] = {"symbol": symbol}
        mapped = OUTPUT_SYMBOL_TO_PARAM.get(symbol)
        if mapped:
            entry["parameter"] = mapped[0]
        calculates.append(entry)
    if calculates:
        return calculates
    for key in ("t_m", "t", "MAWP", "S_A", "f", "A_1", "A_2", "A_3"):
        if key in (variables or {}):
            entry = {"symbol": key}
            mapped = OUTPUT_SYMBOL_TO_PARAM.get(key)
            if mapped:
                entry["parameter"] = mapped[0]
            calculates.append(entry)
    return calculates


def _edges(
    *,
    parent: str,
    requires: list[dict[str, Any]],
    calculates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = [
        {"type": "references", "target": parent, "role": "authorized_by"},
        {"type": "parent", "target": parent},
    ]
    for req in requires:
        param = req.get("parameter")
        if not param:
            continue
        meta: dict[str, Any] = {"alias": req.get("symbol")}
        if req.get("description"):
            meta["role"] = req["description"]
        edges.append({"type": "requires", "target": param, **meta})
    for calc in calculates:
        param = calc.get("parameter")
        if not param:
            continue
        edges.append({"type": "parameter", "target": param, "role": "calculates"})
    return edges


def _execution_sidecar(legacy: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in (
        "variables",
        "steps",
        "executor",
        "execution_function",
        "calculation_module",
        "outputs",
        "equation_id",
        "nomenclature_ref",
        "display",
        "applies_when",
        "paragraph",
    ):
        if key in legacy and legacy[key]:
            payload[key] = legacy[key]
    return payload


def _write_equation(
    *,
    new_id: str,
    parent: str,
    legacy_meta: dict[str, Any],
    body: str,
    equation_class: str = "calculation",
    calculation_kind: str = "function",
    applicability: dict[str, Any] | None = None,
) -> None:
    variables = legacy_meta.get("variables") or {}
    if isinstance(legacy_meta.get("symbols"), list):
        for item in legacy_meta["symbols"]:
            if isinstance(item, dict):
                sym = str(item.get("symbol") or "")
                if sym and sym not in variables:
                    variables[sym] = item
    outputs = legacy_meta.get("outputs") or []
    requires = _requires_from_variables(variables if isinstance(variables, dict) else {})
    calculates = _calculates_from_outputs(outputs, variables if isinstance(variables, dict) else {})
    display = _display_block(legacy_meta)
    executor = legacy_meta.get("executor") or legacy_meta.get("execution_function")
    if executor and not legacy_meta.get("executor"):
        legacy_meta = dict(legacy_meta)
        legacy_meta["executor"] = executor

    frontmatter: dict[str, Any] = {
        "id": new_id,
        "type": "equation",
        "key": new_id,
        "name": str(legacy_meta.get("name") or legacy_meta.get("title") or new_id),
        "equation_class": equation_class,
        "calculation_kind": calculation_kind,
        "description": str(legacy_meta.get("name") or legacy_meta.get("title") or new_id),
        "authority": {"authorized_by": [parent], "authority_context_required": True},
        "requires": requires,
        "calculates": calculates,
        "edges": _edges(parent=parent, requires=requires, calculates=calculates),
        "metadata": {"status": "active", "version": 1, "legacy_equation_id": legacy_meta.get("equation_id")},
    }
    if display:
        frontmatter["display"] = display
    if applicability:
        frontmatter["applicability"] = applicability
    if legacy_meta.get("expression") or legacy_meta.get("equation"):
        frontmatter["expression"] = {
            "language": "sympy",
            "formula": str(legacy_meta.get("expression") or legacy_meta.get("equation")),
        }
        frontmatter["calculation_kind"] = "algebraic"

    eq_path = EQUATION_DIR / f"{new_id}.yaml"
    eq_path.parent.mkdir(parents=True, exist_ok=True)
    eq_path.write_text(_compose(frontmatter, body), encoding="utf-8")

    exec_payload = _execution_sidecar(legacy_meta)
    if exec_payload:
        sidecar_dir = EQUATION_DIR / new_id
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = sidecar_dir / "execution.yaml"
        sidecar_path.write_text(
            yaml.safe_dump(exec_payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def _load_sidecar_yaml(path: Path) -> dict[str, Any]:
    meta, _body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return meta


def _collect_legacy_equations() -> list[tuple[str, str, dict[str, Any], str]]:
    """Return (new_id, parent_paragraph, legacy_meta, body)."""
    collected: dict[str, tuple[str, dict[str, Any], str]] = {}

    eq2_path = PARAGRAPH_DIR / "304.1.1" / "equations" / "eq-2.md"
    if eq2_path.is_file():
        meta, body = _split_frontmatter(eq2_path.read_text(encoding="utf-8"))
        collected["asme_b313_304_1_1_eq_2"] = ("304.1.1", meta, body)

    exec_304_1_2 = PARAGRAPH_DIR / "304.1.2" / "execution.yaml"
    if exec_304_1_2.is_file():
        data = _load_sidecar_yaml(exec_304_1_2)
        for item in data.get("equations") or []:
            if not isinstance(item, dict):
                continue
            legacy_id = str(item.get("id") or "")
            new_id = LEGACY_ID_MAP.get(legacy_id)
            if not new_id:
                continue
            meta, body = _parse_embedded_source(item)
            if legacy_id == "thick_wall_y":
                meta.setdefault("name", "Thick-Wall Temperature Coefficient Y")
                meta.setdefault("equation", meta.get("equation") or "Y = (d + 2c) / (D + d + 2c)")
            collected[new_id] = ("304.1.2", meta, body)

    exec_302_3_5 = PARAGRAPH_DIR / "302.3.5" / "execution.yaml"
    if exec_302_3_5.is_file():
        data = _load_sidecar_yaml(exec_302_3_5)
        for item in data.get("equations") or []:
            if not isinstance(item, dict):
                continue
            legacy_id = str(item.get("id") or "")
            new_id = LEGACY_ID_MAP.get(legacy_id)
            if not new_id:
                continue
            meta, body = _parse_embedded_source(item)
            collected[new_id] = ("302.3.5", meta, body)

    exec_304_3_3 = PARAGRAPH_DIR / "304.3.3" / "execution.yaml"
    if exec_304_3_3.is_file():
        data = _load_sidecar_yaml(exec_304_3_3)
        for item in data.get("equations") or []:
            if not isinstance(item, dict):
                continue
            legacy_id = str(item.get("id") or "")
            new_id = LEGACY_ID_MAP.get(legacy_id)
            if not new_id:
                continue
            meta, body = _parse_embedded_source(item)
            collected[new_id] = ("304.3.3", meta, body)

    mawp_path = WORKFLOW_DIR / "mawp.yaml"
    if mawp_path.is_file():
        meta, _body = _split_frontmatter(mawp_path.read_text(encoding="utf-8"))
        seen_pdt = False
        for item in meta.get("equations") or []:
            if not isinstance(item, dict):
                continue
            legacy_id = str(item.get("id") or "")
            if legacy_id == "pressure_design_thickness":
                if seen_pdt:
                    continue
                seen_pdt = True
            new_id = LEGACY_ID_MAP.get(legacy_id)
            if not new_id or new_id in collected:
                continue
            emeta, ebody = _parse_embedded_source(item)
            if not emeta and legacy_id == "mawp_pressure":
                emeta = {
                    "equation_id": "mawp_pressure",
                    "name": "Maximum Allowable Working Pressure",
                    "display": item.get("display") or "MAWP = 2SEWt / (D - 2Yt)",
                    "executor": item.get("execution_function") or "calculate_mawp",
                }
            collected[new_id] = ("304.1.2" if legacy_id == "mawp_pressure" else "WF-MAWP", emeta, ebody)

    return [(nid, parent, meta, body) for nid, (parent, meta, body) in collected.items()]


def _rewrite_paragraph_execution_equations() -> None:
    rel_file = "../equation/{id}.yaml"
    slim_refs = {
        "304.1.2": [
            {
                "id": "asme_b313_304_1_2_wall_thickness",
                "file": rel_file.format(id="asme_b313_304_1_2_wall_thickness"),
                "execution_function": "calculate_wall_thickness",
            },
            {
                "id": "asme_b313_mawp_pressure",
                "file": rel_file.format(id="asme_b313_mawp_pressure"),
                "execution_function": "calculate_mawp",
            },
            {
                "id": "asme_b313_thick_wall_y",
                "file": rel_file.format(id="asme_b313_thick_wall_y"),
            },
        ],
        "302.3.5": [
            {
                "id": "asme_b313_302_3_5_eq_1a",
                "file": rel_file.format(id="asme_b313_302_3_5_eq_1a"),
                "execution_function": "calculate_allowable_displacement_stress_range",
            },
            {
                "id": "asme_b313_302_3_5_eq_1b",
                "file": rel_file.format(id="asme_b313_302_3_5_eq_1b"),
                "execution_function": "calculate_allowable_displacement_stress_range_with_margin",
            },
            {
                "id": "asme_b313_302_3_5_eq_1c",
                "file": rel_file.format(id="asme_b313_302_3_5_eq_1c"),
                "execution_function": "calculate_stress_range_factor",
            },
        ],
        "304.3.3": [
            {"id": f"asme_b313_304_3_3_{slug}", "file": rel_file.format(id=f"asme_b313_304_3_3_{slug}")}
            for slug in ("eq_6", "eq_6a", "eq_7", "eq_8")
        ],
    }
    for para_id, refs in slim_refs.items():
        path = PARAGRAPH_DIR / para_id / "execution.yaml"
        if not path.is_file():
            continue
        data = _load_sidecar_yaml(path)
        data["equations"] = refs
        path.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def _rewrite_mawp_workflow() -> None:
    path = WORKFLOW_DIR / "mawp.yaml"
    meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    meta["equations"] = [
        {
            "id": "asme_b313_pressure_design_thickness",
            "file": "../equation/asme_b313_pressure_design_thickness.yaml",
            "execution_function": "calculate_pressure_design_thickness",
        },
        {
            "id": "asme_b313_mawp_pressure",
            "file": "../equation/asme_b313_mawp_pressure.yaml",
            "execution_function": "calculate_mawp",
        },
    ]
    for item in meta.get("nomenclature") or []:
        if not isinstance(item, dict):
            continue
        for citation in item.get("citations") or []:
            if isinstance(citation, dict) and citation.get("node_id") == "WF-MAWP":
                citation["node_id"] = "asme_b313_mawp_pressure"
    path.write_text(_compose(meta, body), encoding="utf-8")


def _rewrite_paragraph_yaml_refs() -> None:
    updates = {
        "304.1.1.yaml": {
            "edge_targets": {"304.1.1-eq-2": "asme_b313_304_1_1_eq_2"},
            "referenced_equations": ["asme_b313_304_1_1_eq_2"],
        },
        "304.1.2.yaml": {
            "referenced_equations": [
                "asme_b313_mawp_pressure",
                "asme_b313_thick_wall_y",
                "asme_b313_304_1_2_wall_thickness",
            ],
        },
        "302.3.5.yaml": {
            "referenced_equations": [
                "asme_b313_302_3_5_eq_1a",
                "asme_b313_302_3_5_eq_1b",
                "asme_b313_302_3_5_eq_1c",
            ],
        },
        "304.3.3.yaml": {
            "referenced_equations": [
                "asme_b313_304_3_3_eq_6",
                "asme_b313_304_3_3_eq_6a",
                "asme_b313_304_3_3_eq_7",
                "asme_b313_304_3_3_eq_8",
            ],
        },
    }
    for filename, spec in updates.items():
        path = PARAGRAPH_DIR / filename
        meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        if "referenced_equations" in spec:
            meta["referenced_equations"] = spec["referenced_equations"]
        for old, new in (spec.get("edge_targets") or {}).items():
            for edge in meta.get("edges") or []:
                if isinstance(edge, dict) and edge.get("target") == old:
                    edge["target"] = new
        path.write_text(_compose(meta, body), encoding="utf-8")


def _rewrite_nomenclature_citations() -> None:
    nom_path = PARAGRAPH_DIR / "304.1.1" / "nomenclature.yaml"
    if not nom_path.is_file():
        return
    text = nom_path.read_text(encoding="utf-8")
    text = text.replace("node_id: 304.1.1-eq-2", "node_id: asme_b313_304_1_1_eq_2")
    text = text.replace("equation: eq-2", "equation: asme_b313_304_1_1_eq_2")
    text = text.replace(
        "file: nodes/304.1.2/equations/thick_wall_y.md",
        "file: ../equation/asme_b313_thick_wall_y.yaml",
    )
    nom_path.write_text(text, encoding="utf-8")


def _remove_legacy_eq2() -> None:
    legacy = PARAGRAPH_DIR / "304.1.1" / "equations" / "eq-2.md"
    if legacy.is_file():
        legacy.unlink()


def main() -> int:
    equations = _collect_legacy_equations()
    if len(equations) < 12:
        print(f"Warning: expected 12 equations, found {len(equations)}", file=sys.stderr)
    for new_id, parent, meta, body in equations:
        calc_kind = "function" if meta.get("executor") or meta.get("execution_function") else "algebraic"
        eq_class = "validation" if meta.get("equation_id") == "eq-6a" else "calculation"
        applicability = None
        if parent == "304.1.2" and new_id == "asme_b313_304_1_2_wall_thickness":
            applicability = {
                "applies_when": [
                    {"parameter": "PARAM-pressure-loading", "operator": "equals", "value": "internal_pressure"},
                    {"parameter": "PARAM-straight-pipe-section", "operator": "equals", "value": True},
                ]
            }
        _write_equation(
            new_id=new_id,
            parent=parent if parent != "WF-MAWP" else "304.1.2",
            legacy_meta=meta,
            body=body,
            equation_class=eq_class,
            calculation_kind=calc_kind,
            applicability=applicability,
        )
        print(f"Wrote {new_id}")

    _rewrite_paragraph_execution_equations()
    _rewrite_mawp_workflow()
    _rewrite_paragraph_yaml_refs()
    _rewrite_nomenclature_citations()
    _remove_legacy_eq2()
    print("Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
