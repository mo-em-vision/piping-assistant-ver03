"""Global standards configuration compiled from registry YAML sources."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.reference.material_catalog_db import MaterialSourceSpec
from engine.reference.pipe_dimensions_registry import PipeDimensionSourceSpec

_SCHEMA = """
CREATE TABLE IF NOT EXISTS material_registry_sources (
    standard_slug TEXT PRIMARY KEY,
    specification_group TEXT NOT NULL,
    table_id TEXT NOT NULL,
    db_relative_path TEXT NOT NULL,
    source_node TEXT
);

CREATE TABLE IF NOT EXISTS material_supplemental (
    material_id TEXT PRIMARY KEY,
    standard_slug TEXT NOT NULL,
    grade_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS pipe_dimension_sources (
    standard_slug TEXT PRIMARY KEY,
    specification_group TEXT NOT NULL,
    table_id TEXT NOT NULL,
    db_relative_path TEXT NOT NULL,
    yaml_source TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pipe_dimension_defaults (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    default_standard TEXT
);
"""


def standards_config_db_path(standards_root: Path) -> Path:
    return standards_root.resolve() / "standards_config.db"


@dataclass
class StandardsConfigDatabase:
    db_path: Path

    def __post_init__(self) -> None:
        self.db_path = self.db_path.resolve()

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)

    def clear_all(self) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM material_registry_sources")
            connection.execute("DELETE FROM material_supplemental")
            connection.execute("DELETE FROM pipe_dimension_sources")
            connection.execute("DELETE FROM pipe_dimension_defaults")
            connection.commit()

    def upsert_material_source(self, spec: MaterialSourceSpec) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO material_registry_sources (
                    standard_slug, specification_group, table_id, db_relative_path, source_node
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(standard_slug) DO UPDATE SET
                    specification_group = excluded.specification_group,
                    table_id = excluded.table_id,
                    db_relative_path = excluded.db_relative_path,
                    source_node = excluded.source_node
                """,
                (
                    spec.standard,
                    spec.group,
                    spec.table_id,
                    spec.db_relative_path,
                    spec.source_node,
                ),
            )
            connection.commit()

    def upsert_supplemental_material(self, item: dict[str, Any]) -> None:
        material_id = str(item.get("material_id", "")).strip()
        if not material_id:
            return
        self.initialize_schema()
        aliases = item.get("aliases", []) or []
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO material_supplemental (
                    material_id, standard_slug, grade_key, display_name, aliases_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(material_id) DO UPDATE SET
                    standard_slug = excluded.standard_slug,
                    grade_key = excluded.grade_key,
                    display_name = excluded.display_name,
                    aliases_json = excluded.aliases_json
                """,
                (
                    material_id,
                    str(item.get("standard_slug", "")),
                    str(item.get("grade_key", "")),
                    str(item.get("display_name", "")),
                    json.dumps(aliases),
                ),
            )
            connection.commit()

    def upsert_pipe_dimension_source(self, spec: PipeDimensionSourceSpec) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO pipe_dimension_sources (
                    standard_slug, specification_group, table_id, db_relative_path,
                    yaml_source, is_default
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(standard_slug) DO UPDATE SET
                    specification_group = excluded.specification_group,
                    table_id = excluded.table_id,
                    db_relative_path = excluded.db_relative_path,
                    yaml_source = excluded.yaml_source,
                    is_default = excluded.is_default
                """,
                (
                    spec.standard,
                    spec.group,
                    spec.table_id,
                    spec.db_relative_path,
                    spec.yaml_source,
                    int(spec.default),
                ),
            )
            connection.commit()

    def set_pipe_dimension_default(self, default_standard: str | None) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM pipe_dimension_defaults")
            connection.execute(
                "INSERT INTO pipe_dimension_defaults (id, default_standard) VALUES (1, ?)",
                (default_standard,),
            )
            connection.commit()

    def load_material_sources(self) -> list[MaterialSourceSpec]:
        if not self.exists:
            return []
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT standard_slug, specification_group, table_id, db_relative_path, source_node
                FROM material_registry_sources ORDER BY standard_slug
                """
            ).fetchall()
        specs: list[MaterialSourceSpec] = []
        for row in rows:
            db_rel = str(row["db_relative_path"])
            db_file = Path(db_rel).name
            specs.append(
                MaterialSourceSpec(
                    standard=str(row["standard_slug"]),
                    group=str(row["specification_group"]),
                    table_id=str(row["table_id"]),
                    db_file=db_file,
                    source_node=str(row["source_node"]) if row["source_node"] else None,
                )
            )
        return specs

    def load_supplemental_materials(self) -> list[dict[str, Any]]:
        if not self.exists:
            return []
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT material_id, standard_slug, grade_key, display_name, aliases_json
                FROM material_supplemental ORDER BY material_id
                """
            ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            aliases = json.loads(str(row["aliases_json"] or "[]"))
            items.append(
                {
                    "material_id": str(row["material_id"]),
                    "standard_slug": str(row["standard_slug"]),
                    "grade_key": str(row["grade_key"]),
                    "display_name": str(row["display_name"]),
                    "aliases": aliases if isinstance(aliases, list) else [],
                }
            )
        return items

    def load_pipe_dimension_sources(self) -> tuple[str | None, list[PipeDimensionSourceSpec]]:
        if not self.exists:
            return None, []
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            default_row = connection.execute(
                "SELECT default_standard FROM pipe_dimension_defaults WHERE id = 1"
            ).fetchone()
            rows = connection.execute(
                """
                SELECT standard_slug, specification_group, table_id, db_relative_path,
                       yaml_source, is_default
                FROM pipe_dimension_sources ORDER BY standard_slug
                """
            ).fetchall()
        default_standard = (
            str(default_row["default_standard"]).strip() if default_row and default_row["default_standard"] else None
        )
        sources: list[PipeDimensionSourceSpec] = []
        for row in rows:
            db_rel = str(row["db_relative_path"])
            sources.append(
                PipeDimensionSourceSpec(
                    standard=str(row["standard_slug"]),
                    group=str(row["specification_group"]),
                    table_id=str(row["table_id"]),
                    db_file=Path(db_rel).name,
                    yaml_source=str(row["yaml_source"]),
                    default=bool(row["is_default"]),
                )
            )
        return default_standard, sources
