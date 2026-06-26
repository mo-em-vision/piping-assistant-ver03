#!/usr/bin/env python3
"""Build ASTM standards lookup tables SQLite databases."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.material_ids import make_material_id
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_tables import StandardsTablesDatabase

_METADATA_KEYS = (
    "standard",
    "product_form",
    "test_method",
    "stress_unit",
    "aliases",
)


def _metadata_from_table(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in _METADATA_KEYS if key in data}


def _materials_keyed_by_id(
    materials: dict[str, Any],
    *,
    standard_slug: str,
) -> dict[str, Any]:
    keyed: dict[str, Any] = {}
    for grade_key, payload in materials.items():
        if not isinstance(payload, dict):
            continue
        entry = dict(payload)
        grade_label = str(entry.get("grade_key") or grade_key)
        material_id = str(entry.get("material_id") or make_material_id(standard_slug, grade_label))
        entry["material_id"] = material_id
        entry["grade_key"] = grade_label
        keyed[material_id] = entry
    return keyed


def import_material_properties_pack(
    pack_root: Path,
    *,
    source_node: str,
    standard_slug: str,
    seed_yaml: Path | None = None,
) -> StandardsTablesDatabase:
    yaml_path = seed_yaml or (pack_root / "tables" / "material_properties.yaml")
    if not yaml_path.exists():
        raise FileNotFoundError(f"Material properties YAML not found: {yaml_path}")

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid material properties table: {yaml_path}")

    table_id = str(data.get("table_id", "material_properties"))
    db_path = resolve_pack_tables_db(pack_root)
    if db_path.exists():
        db_path.unlink()

    database = StandardsTablesDatabase(db_path)
    database.upsert_table(
        table_id=table_id,
        title=str(data.get("title", table_id)),
        version=str(data.get("version")) if data.get("version") is not None else None,
        temperature_unit=str(data.get("temperature_unit")) if data.get("temperature_unit") else None,
        keys=[str(key) for key in data.get("keys", []) or []],
        layout="material_catalog",
        source_node=source_node,
        metadata=_metadata_from_table(data),
        materials=_materials_keyed_by_id(
            dict(data.get("materials", {}) or {}),
            standard_slug=standard_slug,
        ),
        aliases=[
            "material_properties",
            "tables/material_properties.yaml",
            "tables/material_properties",
        ],
    )
    return database


def build_all() -> list[Path]:
    packs = [
        (
            _ROOT / "standards" / "astm" / "astm_a53",
            "astm_a53",
            "ASTM-a53-material-properties",
            _ROOT / "scripts" / "seeds" / "astm_a53_material_properties.yaml",
        ),
        (
            _ROOT / "standards" / "astm" / "astm_a106",
            "astm_a106",
            "ASTM-a106-material-properties",
            _ROOT / "scripts" / "seeds" / "astm_a106_material_properties.yaml",
        ),
        (
            _ROOT / "standards" / "astm" / "astm_a312",
            "astm_a312",
            "ASTM-a312-material-properties",
            _ROOT / "scripts" / "seeds" / "astm_a312_material_properties.yaml",
        ),
        (
            _ROOT / "standards" / "astm" / "astm_stainless_castings",
            "astm_stainless_castings",
            "ASTM-stainless-castings-material-properties",
            _ROOT / "scripts" / "seeds" / "astm_stainless_castings_material_properties.yaml",
        ),
    ]
    built: list[Path] = []
    for pack_root, standard_slug, source_node, seed_yaml in packs:
        database = import_material_properties_pack(
            pack_root,
            source_node=source_node,
            standard_slug=standard_slug,
            seed_yaml=seed_yaml,
        )
        built.append(database.db_path)
        print(f"Built {database.db_path} ({database.list_table_ids()})")
    return built


if __name__ == "__main__":
    build_all()
