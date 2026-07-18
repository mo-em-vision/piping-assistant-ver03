"""Load workflow node sidecar files (runtime/navigation metadata)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.node_authoring_policy import LEGACY_SIDECAR_COMPAT
from engine.reference.node_block_extractor import extract_nested_blocks
from engine.reference.standards_markdown import split_frontmatter

from engine.reference.parameter_keys import (
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_PARAM,
)
from engine.reference.workflow_authoring_policy import WORKFLOW_RUNTIME_KEYS as _RUNTIME_KEYS

_PARAM_TO_FIELD: dict[str, str] = {
    "PARAM-straight-pipe-section": "straight_pipe_section",
    "PARAM-pressure-design-case": "pressure_design_case",
    "PARAM-internal-design-gage-pressure": "internal_design_gage_pressure",
    "PARAM-outside-diameter": "outside_diameter",
    "PARAM-nominal-pipe-size": "nominal_pipe_size",
    "PARAM-material-grade": "material_grade",
    "PARAM-metallurgical-group": "metallurgical_group",
    "PARAM-design-temperature": "design_temperature",
    "PARAM-external-design-pressure": "external_design_pressure",
    "PARAM-basic-casting-quality-factor": "basic_casting_quality_factor",
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_PARAM: LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    "PARAM-weld-strength-reduction-factor-w": "weld_strength_reduction_factor_w",
    "PARAM-temperature-coefficient-y": "temperature_coefficient_y",
    "PARAM-pipe-construction-type": "pipe_construction_type",
    "PARAM-corrosion-allowance": "corrosion_allowance",
    "PARAM-actual-wall-thickness": "actual_wall_thickness",
    "PARAM-pipe-schedule": "pipe_schedule",
    "PARAM-allowable-stress": "allowable_stress",
    "PARAM-required-wall-thickness": "required_wall_thickness",
    "PARAM-minimum-required-thickness": "minimum_required_thickness",
    "PARAM-maximum-allowable-working-pressure": "mawp",
}

_PROJECT_RUNTIME_WORKFLOW_IDS: dict[str, tuple[str, ...]] = {
    "WF-PIPE-WALL-THICKNESS": ("WF-PIPE-WALL-THICKNESS",),
    "B313-WF-PIPE-WALL-THICKNESS": ("WF-PIPE-WALL-THICKNESS", "B313-WF-PIPE-WALL-THICKNESS"),
    "pipe_wall_thickness_design": ("WF-PIPE-WALL-THICKNESS",),
    "WF-MAWP": ("WF-MAWP",),
    "B313-WF-MAWP": ("WF-MAWP", "B313-WF-MAWP"),
    "mawp_design": ("WF-MAWP",),
}


def _workflow_runtime_ids(node_id: str) -> tuple[str, ...]:
    explicit = _PROJECT_RUNTIME_WORKFLOW_IDS.get(node_id)
    if explicit:
        return explicit
    return (node_id,)


def _project_runtime_paths(record_path: Path, node_id: str) -> list[Path]:
    """Locate repo-level ``workflows/<id>/runtime.yaml`` sidecars."""
    paths: list[Path] = []
    seen: set[Path] = set()
    for ancestor in record_path.resolve().parents:
        workflows_root = ancestor / "workflows"
        if not workflows_root.is_dir():
            continue
        for workflow_id in _workflow_runtime_ids(node_id):
            candidate = workflows_root / workflow_id / "runtime.yaml"
            if candidate.is_file() and candidate not in seen:
                seen.add(candidate)
                paths.append(candidate)
        if paths:
            break
    return paths


def _merge_runtime_data(merged: dict[str, Any], data: dict[str, Any]) -> None:
    for key in _RUNTIME_KEYS:
        if key in data and data[key]:
            merged[key] = data[key]


def workflow_sidecar_dir(record_path: Path, node_id: str) -> Path:
    """Directory for sidecars: workflows/foo.yaml -> workflows/foo/."""
    return record_path.parent / node_id


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    meta, _body = split_frontmatter(text)
    if isinstance(meta, dict) and meta:
        return meta
    loaded = yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else {}


def _param_to_field(param_id: str) -> str:
    param = str(param_id or "").strip()
    if param in _PARAM_TO_FIELD:
        return _PARAM_TO_FIELD[param]
    if param.startswith("PARAM-"):
        return param.replace("PARAM-", "").replace("-", "_")
    return param


def _phases_to_navigation(phases: Any) -> dict[str, Any] | None:
    if not isinstance(phases, list) or not phases:
        return None
    gate_fields: list[str] = []
    phase_map: dict[str, list[str]] = {}
    for item in phases:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        fields = [
            _param_to_field(str(param))
            for param in (item.get("required_parameters") or [])
            if str(param).strip()
        ]
        phase_map[key] = fields
        if key in {"expansion_assumptions", "path_decisions"}:
            gate_fields.extend(fields)
    if not phase_map:
        return None
    return {
        "assumption_gate_fields": list(dict.fromkeys(gate_fields)),
        "phases": phase_map,
    }


def merge_workflow_sidecar_metadata(
    metadata: dict[str, Any],
    *,
    record_path: Path | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Promote nested runtime block and merge legacy workflow sidecars."""
    merged = extract_nested_blocks(metadata, "workflow")
    if str(merged.get("type", "")) != "workflow":
        return merged

    if LEGACY_SIDECAR_COMPAT and record_path is not None and node_id:
        sidecar_dir = workflow_sidecar_dir(record_path, node_id)
        flat_runtime = record_path.parent / f"{node_id}.runtime.yaml"
        flat_navigation = record_path.parent / f"{node_id}.navigation.yaml"

        for path in (
            sidecar_dir / "runtime.yaml",
            flat_runtime,
            sidecar_dir / "navigation.yaml",
            flat_navigation,
            *_project_runtime_paths(record_path, node_id),
        ):
            if not path.is_file():
                continue
            data = _load_yaml(path)
            if path.name.startswith("navigation"):
                if merged.get("navigation"):
                    continue
                if data.get("navigation"):
                    merged["navigation"] = data["navigation"]
                elif data.get("phases") or data.get("assumption_gate_fields"):
                    merged["navigation"] = data
                else:
                    merged["navigation"] = data
                continue
            for key in _RUNTIME_KEYS:
                if key in data and data[key] and not merged.get(key):
                    merged[key] = data[key]

    if not merged.get("navigation"):
        synthesized = _phases_to_navigation(merged.get("phases"))
        if synthesized:
            merged["navigation"] = synthesized

    key = str(merged.get("key") or "").strip()
    if key:
        merged.setdefault("slug", key)
        merged.setdefault("engineering_intent", key)
    name = str(merged.get("name") or "").strip()
    if name:
        merged.setdefault("title", name)

    goal_expansion = merged.get("goal_expansion") or {}
    if isinstance(goal_expansion, dict):
        root_goal = goal_expansion.get("root_goal") or {}
        if isinstance(root_goal, dict):
            target = str(root_goal.get("target_parameter") or "").strip()
            if target:
                merged.setdefault("goal_output", _param_to_field(target))

    return merged
