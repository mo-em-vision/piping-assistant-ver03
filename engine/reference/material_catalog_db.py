"""Global material search index across registered standards packs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.reference.material_ids import make_material_id
from engine.reference.standards_tables import StandardsTablesDatabase

_SCHEMA = """
CREATE TABLE IF NOT EXISTS material_sources (
    standard_slug TEXT PRIMARY KEY,
    specification TEXT NOT NULL,
    table_id TEXT NOT NULL,
    db_relative_path TEXT NOT NULL,
    source_node TEXT
);

CREATE TABLE IF NOT EXISTS materials (
    material_id TEXT PRIMARY KEY,
    standard_slug TEXT NOT NULL,
    grade_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    UNIQUE (standard_slug, grade_key)
);

CREATE TABLE IF NOT EXISTS material_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT NOT NULL,
    standard_slug TEXT NOT NULL,
    grade_key TEXT NOT NULL,
    alias TEXT NOT NULL,
    display_name TEXT NOT NULL,
    search_key TEXT NOT NULL,
    UNIQUE (standard_slug, search_key),
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_material_aliases_search
    ON material_aliases(search_key);

CREATE INDEX IF NOT EXISTS idx_materials_standard
    ON materials(standard_slug);
"""


@dataclass(frozen=True)
class MaterialSourceSpec:
    standard: str
    group: str
    table_id: str
    db_file: str
    source_node: str | None = None

    @property
    def db_relative_path(self) -> str:
        return f"{self.group}/{self.standard}/{self.db_file}"


def material_registry_path(standards_root: Path) -> Path:
    return standards_root / "materials" / "registry.yaml"


def supplemental_materials_path(standards_root: Path) -> Path:
    return standards_root / "materials" / "supplemental.yaml"


def global_material_catalog_path(standards_root: Path) -> Path:
    return standards_root / "materials" / "materials.db"


def standards_root_from_pack_root(pack_root: Path) -> Path:
    return pack_root.parent.parent


def load_material_registry(standards_root: Path) -> list[MaterialSourceSpec]:
    from engine.reference.standards_config_db import StandardsConfigDatabase, standards_config_db_path

    config_db = StandardsConfigDatabase(standards_config_db_path(standards_root))
    if config_db.exists:
        sources = config_db.load_material_sources()
        if sources:
            return sources

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


def load_supplemental_materials(standards_root: Path) -> list[dict[str, Any]]:
    from engine.reference.standards_config_db import StandardsConfigDatabase, standards_config_db_path

    config_db = StandardsConfigDatabase(standards_config_db_path(standards_root))
    if config_db.exists:
        items = config_db.load_supplemental_materials()
        if items:
            return items

    path = supplemental_materials_path(standards_root)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = data.get("materials", []) or []
    return [item for item in items if isinstance(item, dict)]


def _grade_alias_map(table: dict[str, Any]) -> dict[str, str]:
    aliases = table.get("aliases", {}).get("grade", {}) or {}
    return {str(alias): str(target) for alias, target in aliases.items()}


def _aliases_for_grade(
    grade_key: str,
    row: dict[str, Any],
    grade_aliases: dict[str, str],
) -> list[str]:
    values = [grade_key, str(row.get("display_name", grade_key))]
    values.extend(str(alias) for alias in row.get("aliases", []) or [])
    for alias, target in grade_aliases.items():
        if str(target) == grade_key:
            values.append(str(alias))
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _catalog_material_entries(
    table: dict[str, Any],
    standard_slug: str,
) -> list[dict[str, str]]:
    grade_aliases = _grade_alias_map(table)
    materials = table.get("materials", {}) or {}
    entries: list[dict[str, str]] = []

    for material_key, payload in materials.items():
        if not isinstance(payload, dict):
            continue
        grade_key = str(payload.get("grade_key") or material_key)
        material_id = str(
            payload.get("material_id") or make_material_id(standard_slug, grade_key)
        )
        display_name = str(payload.get("display_name", grade_key))
        for alias in _aliases_for_grade(grade_key, payload, grade_aliases):
            entries.append(
                {
                    "material_id": material_id,
                    "standard_slug": standard_slug,
                    "grade_key": grade_key,
                    "alias": alias,
                    "display_name": display_name,
                    "search_key": alias.lower(),
                }
            )
    return entries


class GlobalMaterialCatalog:
    """Searchable material index built from registered standards sources."""

    def __init__(self, standards_root: Path) -> None:
        self.standards_root = standards_root.resolve()
        self.db_path = global_material_catalog_path(self.standards_root)

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def connect(self) -> sqlite3.Connection:
        if not self.exists:
            raise FileNotFoundError(
                f"Global material catalog not found: {self.db_path}. "
                "Run scripts/build_material_catalog_db.py"
            )
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)

    def rebuild(self) -> int:
        """Rebuild the global catalog from registry sources. Returns alias count."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                DROP TABLE IF EXISTS material_aliases;
                DROP TABLE IF EXISTS materials;
                DROP TABLE IF EXISTS material_sources;
                """
            )
        self.initialize_schema()
        sources = load_material_registry(self.standards_root)
        supplemental = load_supplemental_materials(self.standards_root)
        alias_count = 0

        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM material_aliases")
            connection.execute("DELETE FROM materials")
            connection.execute("DELETE FROM material_sources")

            seen_material_ids: set[str] = set()

            def insert_material(
                *,
                material_id: str,
                standard_slug: str,
                grade_key: str,
                display_name: str,
            ) -> None:
                if material_id in seen_material_ids:
                    return
                connection.execute(
                    """
                    INSERT INTO materials (material_id, standard_slug, grade_key, display_name)
                    VALUES (?, ?, ?, ?)
                    """,
                    (material_id, standard_slug, grade_key, display_name),
                )
                seen_material_ids.add(material_id)

            def insert_alias_row(row: dict[str, str]) -> None:
                nonlocal alias_count
                insert_material(
                    material_id=row["material_id"],
                    standard_slug=row["standard_slug"],
                    grade_key=row["grade_key"],
                    display_name=row["display_name"],
                )
                connection.execute(
                    """
                    INSERT INTO material_aliases (
                        material_id, standard_slug, grade_key, alias, display_name, search_key
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["material_id"],
                        row["standard_slug"],
                        row["grade_key"],
                        row["alias"],
                        row["display_name"],
                        row["search_key"],
                    ),
                )
                alias_count += 1

            for source in sources:
                pack_db = self.standards_root / source.db_relative_path
                if not pack_db.is_file():
                    raise FileNotFoundError(f"Material source database not found: {pack_db}")

                table = StandardsTablesDatabase(pack_db).get_table(source.table_id)
                if table is None:
                    raise FileNotFoundError(
                        f"Material table {source.table_id!r} not found in {pack_db}"
                    )

                specification = str(table.get("standard", source.standard))
                connection.execute(
                    """
                    INSERT INTO material_sources (
                        standard_slug, specification, table_id, db_relative_path, source_node
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        source.standard,
                        specification,
                        source.table_id,
                        source.db_relative_path,
                        source.source_node,
                    ),
                )

                for row in _catalog_material_entries(table, source.standard):
                    insert_alias_row(row)

            for item in supplemental:
                material_id = str(item.get("material_id", "")).strip()
                standard_slug = str(item.get("standard_slug", "")).strip()
                grade_key = str(item.get("grade_key", "")).strip()
                display_name = str(item.get("display_name", grade_key)).strip()
                if not material_id or not standard_slug or not grade_key:
                    continue
                connection.execute(
                    """
                    INSERT OR IGNORE INTO material_sources (
                        standard_slug, specification, table_id, db_relative_path, source_node
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (standard_slug, display_name, "supplemental", "", None),
                )
                payload = {
                    "display_name": display_name,
                    "aliases": item.get("aliases", []) or [],
                }
                for alias in _aliases_for_grade(grade_key, payload, {}):
                    insert_alias_row(
                        {
                            "material_id": material_id,
                            "standard_slug": standard_slug,
                            "grade_key": grade_key,
                            "alias": alias,
                            "display_name": display_name,
                            "search_key": alias.lower(),
                        }
                    )

            connection.commit()

        return alias_count

    def search(self, query: str, *, limit: int = 12) -> list[dict[str, str]]:
        needle = query.strip().lower()
        if len(needle) < 3 or not self.exists:
            return []

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    m.material_id,
                    m.display_name,
                    m.standard_slug,
                    m.grade_key,
                    s.specification,
                    CASE WHEN a.search_key LIKE ? THEN 0 ELSE 1 END AS rank
                FROM material_aliases AS a
                JOIN materials AS m ON m.material_id = a.material_id
                JOIN material_sources AS s ON s.standard_slug = m.standard_slug
                WHERE a.search_key LIKE ?
                ORDER BY rank, m.standard_slug, m.material_id, length(a.search_key), a.search_key
                LIMIT ?
                """,
                (f"{needle}%", f"%{needle}%", max(limit * 8, 32)),
            ).fetchall()

        best_by_material: dict[str, sqlite3.Row] = {}
        for row in rows:
            material_id = str(row["material_id"])
            if material_id not in best_by_material:
                best_by_material[material_id] = row

        ordered = sorted(
            best_by_material.values(),
            key=lambda row: (int(row["rank"]), str(row["standard_slug"]), str(row["material_id"])),
        )

        return [
            {
                "value": str(row["material_id"]),
                "material_id": str(row["material_id"]),
                "label": str(row["display_name"]),
                "standard": str(row["standard_slug"]),
                "specification": str(row["specification"]),
                "grade_key": str(row["grade_key"]),
            }
            for row in ordered[:limit]
        ]

    def get_material(self, material_id: str) -> dict[str, str] | None:
        if not self.exists:
            return None
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT material_id, standard_slug, grade_key, display_name
                FROM materials
                WHERE material_id = ?
                """,
                (material_id.strip(),),
            ).fetchone()
        if row is None:
            return None
        return {
            "material_id": str(row["material_id"]),
            "standard_slug": str(row["standard_slug"]),
            "grade_key": str(row["grade_key"]),
            "display_name": str(row["display_name"]),
        }


def resolve_material_id(standards_root: Path, token: str) -> str | None:
    """Resolve a catalog material id from an id, alias, or legacy grade label."""
    cleaned = token.strip()
    if not cleaned:
        return None

    catalog = GlobalMaterialCatalog(standards_root)
    if not catalog.exists:
        return None

    direct = catalog.get_material(cleaned)
    if direct is not None:
        return direct["material_id"]

    needle = cleaned.lower()
    with catalog.connect() as connection:
        row = connection.execute(
            """
            SELECT material_id
            FROM material_aliases
            WHERE search_key = ?
            ORDER BY length(search_key), search_key
            LIMIT 1
            """,
            (needle,),
        ).fetchone()
    if row is None:
        return None
    return str(row["material_id"])


def material_display_name(standards_root: Path, material_id: str) -> str | None:
    catalog = GlobalMaterialCatalog(standards_root)
    record = catalog.get_material(material_id)
    if record is None:
        return None
    return record["display_name"]


def search_materials(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return material matches from the global catalog."""
    return GlobalMaterialCatalog(standards_root).search(query, limit=limit)
