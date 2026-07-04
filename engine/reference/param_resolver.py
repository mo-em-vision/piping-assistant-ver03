"""Resolve runtime parameter keys to canonical PARAM-* node ids."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_KEY_ALIASES: dict[str, str] = {
    "material": "PARAM-material-grade",
    "pipe_material": "PARAM-material-grade",
    "material_grade": "PARAM-material-grade",
    "metallurgical_group": "PARAM-metallurgical-group",
    "joint_category": "PARAM-pipe-construction-type",
    "pipe_construction_type": "PARAM-pipe-construction-type",
    "minimum_required_thickness": "PARAM-minimum-required-thickness",
    "t_m": "PARAM-minimum-required-thickness",
    "design_temperature": "PARAM-design-temperature",
    "corrosion_allowance": "PARAM-corrosion-allowance",
    "allowable_stress": "PARAM-allowable-stress",
    "S": "PARAM-allowable-stress",
    "inside_diameter": "PARAM-inside-diameter",
    "measured_wall_thickness": "PARAM-measured-wall-thickness",
    "maximum_allowable_working_pressure": "PARAM-maximum-allowable-working-pressure",
    "mawp": "PARAM-maximum-allowable-working-pressure",
    "MAWP": "PARAM-maximum-allowable-working-pressure",
}


@lru_cache(maxsize=1)
def _global_param_keys() -> dict[str, str]:
    """Map parameter key -> PARAM-* id from global ontology YAML."""
    root = Path(__file__).resolve().parents[2] / "knowledge" / "global" / "parameters" / "nodes"
    mapping: dict[str, str] = dict(_KEY_ALIASES)
    if not root.is_dir():
        return mapping
    try:
        from engine.reference.standards_markdown import split_frontmatter
    except ImportError:
        return mapping
    for path in sorted(root.glob("PARAM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        param_id = str(meta.get("id", path.stem))
        key = str(meta.get("key", "")).strip()
        if key:
            mapping[key] = param_id
    return mapping


def resolve_parameter_id(key: str) -> str:
    """Return canonical PARAM-* id for a runtime parameter key."""
    text = str(key).strip()
    if text.startswith("PARAM-"):
        return text
    resolved = _global_param_keys().get(text)
    if resolved:
        return resolved
    slug = text.replace("_", "-")
    return f"PARAM-{slug}"
