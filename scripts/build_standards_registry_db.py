#!/usr/bin/env python3
"""Compile standards registry YAML files into standards_config.db."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import yaml

from engine.reference.material_catalog_db import (
    MaterialSourceSpec,
    load_material_registry,
    load_supplemental_materials,
    material_registry_path,
    supplemental_materials_path,
)
from engine.reference.pipe_dimensions_registry import (
    PipeDimensionSourceSpec,
    load_pipe_dimensions_registry,
    pipe_dimensions_registry_path,
)
from engine.reference.standards_config_db import StandardsConfigDatabase, standards_config_db_path


def _load_material_registry_yaml(standards_root: Path) -> list[MaterialSourceSpec]:
    path = material_registry_path(standards_root)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources: list[MaterialSourceSpec] = []
    for item in data.get("sources", []) or []:
        if not isinstance(item, dict):
            continue
        standard = str(item.get("standard", "")).strip()
        group = str(item.get("group", "")).strip()
        table_id = str(item.get("table_id", "")).strip()
        db_file = str(item.get("db_file", "")).strip()
        if not standard or not group or not table_id or not db_file:
            continue
        source_node = str(item.get("source_node", "")).strip() or None
        sources.append(
            MaterialSourceSpec(
                standard=standard,
                group=group,
                table_id=table_id,
                db_file=db_file,
                source_node=source_node,
            )
        )
    return sources


def _load_supplemental_yaml(standards_root: Path) -> list[dict]:
    path = supplemental_materials_path(standards_root)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [item for item in data.get("materials", []) or [] if isinstance(item, dict)]


def _load_pipe_registry_yaml(standards_root: Path) -> tuple[str | None, list[PipeDimensionSourceSpec]]:
    path = pipe_dimensions_registry_path(standards_root)
    if not path.is_file():
        return None, []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default_standard = str(data.get("default_standard", "")).strip() or None
    sources: list[PipeDimensionSourceSpec] = []
    for item in data.get("sources", []) or []:
        if not isinstance(item, dict):
            continue
        standard = str(item.get("standard", "")).strip()
        group = str(item.get("group", "")).strip()
        table_id = str(item.get("table_id", "")).strip()
        db_file = str(item.get("db_file", "pipe_dimensions.db")).strip()
        yaml_source = str(item.get("yaml_source", "")).strip()
        if not standard or not group or not table_id or not yaml_source:
            continue
        sources.append(
            PipeDimensionSourceSpec(
                standard=standard,
                group=group,
                table_id=table_id,
                db_file=db_file,
                yaml_source=yaml_source,
                default=bool(item.get("default", False)),
            )
        )
    return default_standard, sources


def build_all(*, standards_root: Path | None = None) -> Path:
    root = (standards_root or (_ROOT / "knowledge" / "standards")).resolve()
    database = StandardsConfigDatabase(standards_config_db_path(root))
    database.clear_all()

    for spec in _load_material_registry_yaml(root):
        database.upsert_material_source(spec)
    for item in _load_supplemental_yaml(root):
        database.upsert_supplemental_material(item)

    default_standard, pipe_sources = _load_pipe_registry_yaml(root)
    for spec in pipe_sources:
        database.upsert_pipe_dimension_source(spec)
    database.set_pipe_dimension_default(default_standard)

    print(f"Built {database.db_path}")
    return database.db_path


if __name__ == "__main__":
    build_all()
