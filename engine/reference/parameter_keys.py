"""Canonical runtime parameter keys aligned with global PARAM-* node ``key`` fields."""

from __future__ import annotations

import re
from typing import Any

from models.fact import Fact, fact_scalar_value
from models.task import Task

# Matches ``key`` on knowledge/global/parameters/nodes/PARAM-material-grade.yaml
MATERIAL_GRADE_KEY = "material_grade"
INTERNAL_DESIGN_GAGE_PRESSURE_KEY = "internal_design_gage_pressure"
LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY = (
    "basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes"
)
LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_PARAM = (
    "PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes"
)

# Legacy keys still accepted when reading stored facts or submitted payloads.
LEGACY_PARAMETER_KEY_ALIASES: dict[str, str] = {
    "material": MATERIAL_GRADE_KEY,
    "material_specification": MATERIAL_GRADE_KEY,
    "pipe_material": MATERIAL_GRADE_KEY,
    "design_pressure": INTERNAL_DESIGN_GAGE_PRESSURE_KEY,
    "joint_category": "pipe_construction_type",
    "measured_wall_thickness": "actual_wall_thickness",
    "weld_joint_efficiency": LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
}


def canonical_parameter_key(key: str) -> str:
    text = str(key or "").strip()
    return LEGACY_PARAMETER_KEY_ALIASES.get(text, text)


def api_parameter_id(key: str) -> str:
    """Canonical parameter id for API/UI payloads (timeline rows, parameter definitions)."""
    return canonical_parameter_key(key)


def is_material_grade_parameter(parameter_id: str) -> bool:
    return canonical_parameter_key(parameter_id) == MATERIAL_GRADE_KEY


def read_parameter_value(inputs: dict[str, Any], canonical_key: str) -> Any:
    if canonical_key in inputs:
        return inputs[canonical_key]
    for legacy, target in LEGACY_PARAMETER_KEY_ALIASES.items():
        if target == canonical_key and legacy in inputs:
            return inputs[legacy]
    return None


def read_fact_value(inputs: dict[str, Any], canonical_key: str) -> Any:
    raw = read_parameter_value(inputs, canonical_key)
    if raw is None:
        return None
    if isinstance(raw, Fact):
        return fact_scalar_value(raw)
    if hasattr(raw, "value"):
        return raw.value
    return raw


def parameter_is_ready(inputs: dict[str, Any], canonical_key: str) -> bool:
    from models.fact import fact_is_expansion_ready

    raw = read_parameter_value(inputs, canonical_key)
    if raw is None:
        return False
    if isinstance(raw, Fact):
        value = fact_scalar_value(raw)
        if value is None or str(value).strip() == "":
            return False
        return fact_is_expansion_ready(raw)
    return True


def active_fact_for_key(task: Task, canonical_key: str) -> Fact | None:
    fact = task.fact_store.active_fact(canonical_key)
    if fact is not None:
        return fact
    for legacy, target in LEGACY_PARAMETER_KEY_ALIASES.items():
        if target != canonical_key:
            continue
        legacy_fact = task.fact_store.active_fact(legacy)
        if legacy_fact is not None:
            return legacy_fact
    return None


def fact_for_task_input(task_inputs: dict[str, Any], input_id: str) -> Fact | None:
    """Resolve a node/table input id to a task fact, including legacy aliases."""
    canonical = canonical_parameter_key(input_id)
    if input_id in task_inputs:
        stored = task_inputs[input_id]
        return stored if isinstance(stored, Fact) else None
    if canonical in task_inputs:
        stored = task_inputs[canonical]
        return stored if isinstance(stored, Fact) else None
    for legacy, target in LEGACY_PARAMETER_KEY_ALIASES.items():
        if target != canonical:
            continue
        if legacy in task_inputs:
            stored = task_inputs[legacy]
            return stored if isinstance(stored, Fact) else None
    return None


def active_material_grade_fact(task: Task) -> Fact | None:
    return active_fact_for_key(task, MATERIAL_GRADE_KEY)


def param_node_id_for_input(input_id: str) -> str:
    """Return global PARAM-* node id for a runtime input / fact key."""
    canonical = canonical_parameter_key(input_id)
    if canonical.upper().startswith("PARAM-"):
        return canonical
    return f"PARAM-{canonical.replace('_', '-')}"


def param_slug_from_name(name: str) -> str:
    """Derive the PARAM id slug from the human ``name`` (lowercase kebab-case words)."""
    text = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().casefold())
    return re.sub(r"-+", "-", text).strip("-")


def param_id_from_name(name: str) -> str:
    slug = param_slug_from_name(name)
    return f"PARAM-{slug}" if slug else ""


def param_key_from_param_id(param_node_id: str) -> str:
    slug = str(param_node_id or "").strip()
    if slug.upper().startswith("PARAM-"):
        slug = slug[6:]
    return slug.replace("-", "_")


def validate_parameter_identity_fields(meta: dict[str, Any]) -> list[str]:
    """Ensure ``id``, ``key``, and ``name`` follow the shared naming convention."""
    issues: list[str] = []
    node_id = str(meta.get("id") or "").strip()
    key = str(meta.get("key") or "").strip()
    name = str(meta.get("name") or "").strip()
    if not node_id or not key or not name:
        return issues
    expected_id = param_id_from_name(name)
    expected_key = param_key_from_param_id(expected_id)
    if node_id != expected_id:
        issues.append(
            f"id must match name slug: expected {expected_id!r} from name {name!r}"
        )
    if key != expected_key:
        issues.append(
            f"key must match id slug: expected {expected_key!r} from id {node_id!r}"
        )
    return issues


def param_display_name_from_id(param_node_id: str) -> str:
    """Human label from PARAM-* id slug: PARAM-required-wall-thickness → Required Wall Thickness."""
    slug = str(param_node_id or "").strip()
    if slug.upper().startswith("PARAM-"):
        slug = slug[6:]
    if not slug:
        return str(param_node_id or "").strip()
    return slug.replace("-", " ").strip().title()


def param_name_matches_id_slug(param_node_id: str, name: str) -> bool:
    """True when PARAM ``name`` matches the id-derived display label."""
    expected = param_display_name_from_id(param_node_id)
    return str(name or "").strip().casefold() == expected.casefold()


def load_parameter_node_metadata(param_node_id: str) -> dict[str, Any] | None:
    from engine.reference.knowledge_paths import parameters_root
    from engine.reference.standards_markdown import split_frontmatter

    path = parameters_root() / "nodes" / f"{param_node_id}.yaml"
    if not path.is_file():
        return None
    metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    if str(metadata.get("type", "")) != "parameter":
        return None
    return metadata


def parameter_node_description(
    *,
    reader: Any | None = None,
    param_id: str | None = None,
    input_id: str | None = None,
) -> str:
    """Return display definition text from a PARAM node's ``description`` field only."""
    node_id = (param_id or "").strip() or (
        param_node_id_for_input(input_id) if input_id else ""
    )
    if not node_id:
        return ""

    # Global PARAM nodes are authored under knowledge/global/parameters/nodes/.
    # StandardsReader graph caches can lag YAML edits; always prefer live YAML.
    if node_id.startswith("PARAM-"):
        metadata = load_parameter_node_metadata(node_id)
        if metadata is not None:
            description = str(metadata.get("description", "")).strip()
            if description:
                return re.sub(r"\s+", " ", description)
            return input_id or node_id

    metadata: dict[str, Any] | None = None
    if reader is not None:
        try:
            metadata = reader.load(node_id).metadata
        except FileNotFoundError:
            metadata = None
    if metadata is None:
        metadata = load_parameter_node_metadata(node_id)
    if metadata is None:
        return input_id or node_id

    description = str(metadata.get("description", "")).strip()
    if description:
        return re.sub(r"\s+", " ", description)
    return input_id or node_id


def parameter_display_label(parameter_id: str, *, reader: Any | None = None) -> str:
    """Return user-facing label from PARAM ``name`` metadata, not internal keys."""
    canonical = canonical_parameter_key(parameter_id)
    api_id = api_parameter_id(canonical)
    node_id = param_node_id_for_input(api_id)

    metadata: dict[str, Any] | None = None
    if node_id.startswith("PARAM-"):
        metadata = load_parameter_node_metadata(node_id)
    if metadata is None and reader is not None:
        try:
            metadata = reader.load(node_id).metadata
        except FileNotFoundError:
            metadata = None
    if metadata is None:
        metadata = load_parameter_node_metadata(node_id)

    if metadata is not None:
        name = str(metadata.get("name", "")).strip()
        if name:
            return name

    return api_id.replace("_", " ").strip().title()
