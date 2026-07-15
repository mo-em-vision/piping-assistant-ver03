"""Generic input resolvers for lookup_rules v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.coefficient_resolver import _filter_y_rows_for_material, _normalize_joint_category
from engine.reference.material_resolver import canonical_material_id, resolve_material_table_key
from engine.reference.nps_normalization import to_nps_lookup_key

RESOLVER_NPS_KEY = "nps_key"
RESOLVER_SCHEDULE_KEY = "schedule_key"
RESOLVER_MATERIAL_CATALOG = "material_catalog"
RESOLVER_METALLURGICAL_GROUP_KEY = "metallurgical_group_key"
RESOLVER_JOINT_CATEGORY_NORMALIZE = "joint_category_normalize"
RESOLVER_IDENTITY = "identity"

KNOWN_RESOLVERS = frozenset(
    {
        RESOLVER_NPS_KEY,
        RESOLVER_SCHEDULE_KEY,
        RESOLVER_MATERIAL_CATALOG,
        RESOLVER_METALLURGICAL_GROUP_KEY,
        RESOLVER_JOINT_CATEGORY_NORMALIZE,
        RESOLVER_IDENTITY,
    }
)


def _row_material_token(row: dict[str, Any]) -> str:
    return str(row.get("material_id") or row.get("material") or "")


def resolve_material_catalog_key(
    material: str,
    *,
    table_data: dict[str, Any],
    standards_root: Path,
) -> str:
    materials = table_data.get("materials", {}) or {}
    if materials:
        material_key = resolve_material_table_key(
            materials,
            material,
            standards_root=standards_root,
        )
    else:
        rows = table_data.get("rows", []) or []
        material_key = resolve_material_table_key(
            {_row_material_token(row): row for row in rows if isinstance(row, dict)},
            material,
            standards_root=standards_root,
        )
    if material_key is None:
        canonical = canonical_material_id(material, standards_root=standards_root) or material
        raise ValueError(f"Material not found in lookup table: {canonical}")
    return material_key


def resolve_input_value(
    raw_value: Any,
    *,
    resolver: str,
    logical_key: str,
    inputs: dict[str, Any],
    table_data: dict[str, Any] | None = None,
    standards_root: Path | None = None,
) -> Any:
    if raw_value is None:
        raise ValueError(f"{logical_key} is required for table lookup")
    text = str(raw_value).strip()
    if not text and resolver != RESOLVER_IDENTITY:
        raise ValueError(f"{logical_key} is required for table lookup")

    if resolver == RESOLVER_IDENTITY:
        return raw_value

    if resolver == RESOLVER_NPS_KEY:
        entry_unit = str(inputs.get("nominal_pipe_size_unit") or "NPS").strip().upper()
        return to_nps_lookup_key(text, entry_unit if entry_unit in {"NPS", "DN"} else "NPS")

    if resolver == RESOLVER_SCHEDULE_KEY:
        import re

        cleaned = re.sub(r"^SCH(?:EDULE)?\s*", "", text.upper()).strip()
        aliases = (table_data or {}).get("aliases", {}).get("schedule", {}) or {}
        for alias, target in aliases.items():
            if cleaned == str(alias).upper():
                return str(target)
        return cleaned

    if resolver == RESOLVER_METALLURGICAL_GROUP_KEY:
        return text

    if resolver == RESOLVER_JOINT_CATEGORY_NORMALIZE:
        return _normalize_joint_category(text)

    if resolver == RESOLVER_MATERIAL_CATALOG:
        if table_data is None or standards_root is None:
            raise ValueError("material_catalog resolver requires table_data and standards_root")
        return resolve_material_catalog_key(text, table_data=table_data, standards_root=standards_root)

    raise ValueError(f"Unknown lookup input resolver: {resolver!r}")


def filter_rows_by_material_group(
    rows: list[dict[str, Any]],
    group: str,
) -> list[dict[str, Any]]:
    return _filter_y_rows_for_material(rows, group)
