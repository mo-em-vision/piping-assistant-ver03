"""Material detail payload for desktop material reference tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api.material_catalog_service import get_material_catalog, warm_material_catalog
from engine.executor.material_properties_lookup import MaterialPropertiesLookup


def _material_source(connection, standard_slug: str) -> dict[str, str] | None:
    row = connection.execute(
        """
        SELECT specification, table_id, source_node
        FROM material_sources
        WHERE standard_slug = ?
        """,
        (standard_slug,),
    ).fetchone()
    if row is None:
        return None
    return {
        "specification": str(row["specification"]),
        "table_id": str(row["table_id"]),
        "source_node": str(row["source_node"]) if row["source_node"] else "",
    }


def _grade_row(lookup: MaterialPropertiesLookup, material_id: str, grade_key: str) -> dict[str, Any]:
    materials = lookup._table.get("materials", {}) or {}
    if material_id in materials:
        row = materials[material_id]
        if isinstance(row, dict):
            return row
    if grade_key in materials:
        row = materials[grade_key]
        if isinstance(row, dict):
            return row
    for key, payload in materials.items():
        if not isinstance(payload, dict):
            continue
        if str(payload.get("grade_key", key)) == grade_key or key == material_id:
            return payload
    raise ValueError(f"Material grade row not found for {material_id}")


def _serialize_mechanical_properties(mech_block: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mech_block, dict):
        return {}
    payload: dict[str, Any] = {}
    room = mech_block.get("room_temperature")
    if isinstance(room, dict):
        payload["room_temperature"] = room
    elevated = mech_block.get("elevated_temperature")
    if isinstance(elevated, list):
        payload["elevated_temperature"] = elevated
    return payload


def get_material_detail(standards_root: Path, material_id: str) -> dict[str, Any]:
    warm_material_catalog(standards_root)
    catalog = get_material_catalog(standards_root)
    record = catalog.get_material(material_id.strip())
    if record is None:
        raise FileNotFoundError(f"Material not found: {material_id}")

    standard_slug = record["standard_slug"]
    with catalog.connect() as connection:
        source = _material_source(connection, standard_slug)

    lookup = MaterialPropertiesLookup(standards_root, standard=standard_slug)
    properties = lookup.lookup(material_id)
    row = _grade_row(lookup, material_id, record["grade_key"])

    return {
        "material_id": record["material_id"],
        "display_name": record["display_name"],
        "standard_slug": standard_slug,
        "grade_key": record["grade_key"],
        "specification": properties.specification,
        "product_form": properties.product_form,
        "uns_number": str(row.get("uns_number", "") or ""),
        "aliases": properties.aliases,
        "mechanical_properties": _serialize_mechanical_properties(
            row.get("mechanical_properties", {}) or {}
        ),
        "chemical_composition": properties.chemical_composition,
        "physical_properties": properties.physical_properties,
        "notes": properties.notes,
        "source_node": (source or {}).get("source_node", ""),
        "table_id": properties.table_id or (source or {}).get("table_id", ""),
    }
