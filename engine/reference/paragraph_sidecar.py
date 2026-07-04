from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_markdown import split_frontmatter

_EXECUTION_KEYS = (
    "interactions",
    "assumptions",
    "provisional_assumptions",
    "parameter_defaults",
    "inputs",
    "depends_on",
    "equations",
    "validation_rules",
    "conditions",
    "kind",
    "outputs",
    "lookups",
    "notes",
)


def paragraph_sidecar_dir(record_path: Path, node_id: str) -> Path:
    """Directory for sidecars: paragraph/304.1.1.yaml -> paragraph/304.1.1/."""
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


def merge_paragraph_sidecar_metadata(
    metadata: dict[str, Any],
    *,
    record_path: Path | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Merge nomenclature and execution sidecars into metadata for runtime adapters."""
    merged = dict(metadata)
    if record_path is None or not node_id:
        return merged

    sidecar_dir = paragraph_sidecar_dir(record_path, node_id)
    flat_nomenclature = record_path.parent / f"{node_id}.nomenclature.yaml"
    flat_execution = record_path.parent / f"{node_id}.execution.yaml"

    for path in (sidecar_dir / "nomenclature.yaml", flat_nomenclature):
        if path.is_file():
            data = _load_yaml(path)
            if data.get("nomenclature"):
                merged["nomenclature"] = data["nomenclature"]
            break

    for path in (sidecar_dir / "execution.yaml", flat_execution):
        if path.is_file():
            data = _load_yaml(path)
            for key in _EXECUTION_KEYS:
                if key in data and data[key]:
                    merged[key] = data[key]
            break

    return merged


def parse_applicability_as_interactions(
    metadata: dict[str, Any],
    node_id: str,
) -> list[dict[str, Any]]:
    """Synthesize legacy-style interaction dicts from template applicability block."""
    applicability = metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return []
    applies_when = applicability.get("applies_when") or []
    interactions: list[dict[str, Any]] = []
    for item in applies_when:
        if not isinstance(item, dict):
            continue
        param = str(item.get("parameter") or "")
        field = _param_to_field(param) if param.startswith("PARAM-") else ""
        if not field:
            continue
        operator = str(item.get("operator") or "equals")
        value = item.get("value")
        if field == "pressure_loading" and operator == "equals":
            interactions.append(
                {
                    "variable": "pressure_loading",
                    "mode": "decision",
                    "required": True,
                    "required_for_expansion": True,
                    "options": ["internal_pressure", "external_pressure"],
                    "aliases": {
                        "internal": "internal_pressure",
                        "internal_pressure": "internal_pressure",
                        "external": "external_pressure",
                        "external_pressure": "external_pressure",
                    },
                }
            )
        elif field == "straight_pipe_section" and operator == "equals" and value is True:
            continue
    return interactions


def parse_applicability_as_assumptions(
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Synthesize expansion assumptions from template applicability/limitations."""
    assumptions: list[dict[str, Any]] = []
    applicability = metadata.get("applicability") or {}
    if isinstance(applicability, dict):
        for item in applicability.get("applies_when") or []:
            if not isinstance(item, dict):
                continue
            param = str(item.get("parameter") or "")
            field = _param_to_field(param) if param.startswith("PARAM-") else ""
            if field == "straight_pipe_section":
                assumptions.append(
                    {
                        "id": "straight_pipe_section",
                        "field": "straight_pipe_section",
                        "description": "Applied to a straight section of a pipe.",
                        "required_for_expansion": True,
                        "requires_confirmation": True,
                        "allowed_values": [True, False],
                        "blocks_expansion_on": [False],
                        "expansion_block_message": (
                            "Non-straight pipe sections are not yet supported. "
                            "A future node will cover fittings and bends."
                        ),
                    }
                )
    for item in metadata.get("limitations") or []:
        if not isinstance(item, dict):
            continue
        if item.get("severity") == "blocking" or item.get("action") == "warning":
            continue
    return assumptions


def _param_to_field(param_id: str) -> str:
    slug = param_id.replace("PARAM-", "").replace("-", "_")
    mapping = {
        "pressure_loading": "pressure_loading",
        "straight_pipe_section": "straight_pipe_section",
        "design_pressure": "design_pressure",
        "outside_diameter": "outside_diameter",
        "allowable_stress": "allowable_stress",
        "weld_joint_efficiency": "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_w": "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_y": "temperature_coefficient_Y",
        "corrosion_allowance": "corrosion_allowance",
        "material_specification": "material",
    }
    return mapping.get(slug, slug)
