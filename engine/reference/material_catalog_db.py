"""Global material search index across registered standards packs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_tables import StandardsTablesDatabase

_SCHEMA = """
CREATE TABLE IF NOT EXISTS material_sources (
    standard_slug TEXT PRIMARY KEY,
    specification TEXT NOT NULL,
    table_id TEXT NOT NULL,
    db_relative_path TEXT NOT NULL,
    source_node TEXT
);

CREATE TABLE IF NOT EXISTS material_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_slug TEXT NOT NULL,
    grade_key TEXT NOT NULL,
    alias TEXT NOT NULL,
    display_name TEXT NOT NULL,
    search_key TEXT NOT NULL,
    UNIQUE (standard_slug, search_key),
    FOREIGN KEY (standard_slug) REFERENCES material_sources(standard_slug) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_material_aliases_search
    ON material_aliases(search_key);
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


def global_material_catalog_path(standards_root: Path) -> Path:
    return standards_root / "materials" / "materials.db"


def load_material_registry(standards_root: Path) -> list[MaterialSourceSpec]:
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


def _expand_material_aliases(table: dict[str, Any], standard_slug: str) -> list[dict[str, str]]:
    grade_aliases = _grade_alias_map(table)
    materials = table.get("materials", {}) or {}
    rows: list[dict[str, str]] = []

    for grade_key, payload in materials.items():
        if not isinstance(payload, dict):
            continue
        display_name = str(payload.get("display_name", grade_key))
        for alias in _aliases_for_grade(str(grade_key), payload, grade_aliases):
            rows.append(
                {
                    "standard_slug": standard_slug,
                    "grade_key": str(grade_key),
                    "alias": alias,
                    "display_name": display_name,
                    "search_key": alias.lower(),
                }
            )
    return rows


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
        self.initialize_schema()
        sources = load_material_registry(self.standards_root)
        alias_count = 0

        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM material_aliases")
            connection.execute("DELETE FROM material_sources")

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

                for row in _expand_material_aliases(table, source.standard):
                    connection.execute(
                        """
                        INSERT INTO material_aliases (
                            standard_slug, grade_key, alias, display_name, search_key
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            row["standard_slug"],
                            row["grade_key"],
                            row["alias"],
                            row["display_name"],
                            row["search_key"],
                        ),
                    )
                    alias_count += 1

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
                    a.grade_key,
                    a.alias,
                    a.display_name,
                    a.standard_slug,
                    a.search_key,
                    s.specification,
                    CASE WHEN a.search_key LIKE ? THEN 0 ELSE 1 END AS rank
                FROM material_aliases AS a
                JOIN material_sources AS s ON s.standard_slug = a.standard_slug
                WHERE a.search_key LIKE ?
                ORDER BY rank, a.standard_slug, a.grade_key, length(a.search_key), a.search_key
                """,
                (f"{needle}%", f"%{needle}%"),
            ).fetchall()

        best_by_grade: dict[tuple[str, str], sqlite3.Row] = {}
        for row in rows:
            key = (str(row["standard_slug"]), str(row["grade_key"]))
            if key not in best_by_grade:
                best_by_grade[key] = row

        ordered = sorted(
            best_by_grade.values(),
            key=lambda row: (int(row["rank"]), str(row["standard_slug"]), str(row["grade_key"])),
        )

        return [
            {
                "value": str(row["grade_key"]),
                "label": str(row["display_name"]),
                "standard": str(row["standard_slug"]),
                "specification": str(row["specification"]),
            }
            for row in ordered[:limit]
        ]


def search_materials(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return material matches from the global catalog."""
    return GlobalMaterialCatalog(standards_root).search(query, limit=limit)
