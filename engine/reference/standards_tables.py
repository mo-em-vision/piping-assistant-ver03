"""SQLite-backed standards lookup tables for a standards pack."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS lookup_tables (
    table_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    version TEXT,
    unit TEXT,
    temperature_unit TEXT,
    interpolation INTEGER NOT NULL DEFAULT 0,
    keys_json TEXT NOT NULL DEFAULT '[]',
    layout TEXT NOT NULL DEFAULT 'flat_rows',
    subsection TEXT,
    source_node TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS lookup_table_aliases (
    alias TEXT PRIMARY KEY,
    table_id TEXT NOT NULL,
    FOREIGN KEY (table_id) REFERENCES lookup_tables(table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lookup_table_materials (
    table_id TEXT NOT NULL,
    material_key TEXT NOT NULL,
    display_name TEXT,
    PRIMARY KEY (table_id, material_key),
    FOREIGN KEY (table_id) REFERENCES lookup_tables(table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lookup_table_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id TEXT NOT NULL,
    material_key TEXT,
    row_json TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (table_id) REFERENCES lookup_tables(table_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lookup_table_rows_table
    ON lookup_table_rows(table_id);
CREATE INDEX IF NOT EXISTS idx_lookup_table_rows_material
    ON lookup_table_rows(table_id, material_key);
"""


@dataclass
class StandardsTablesDatabase:
    """Read lookup tables from a per-pack SQLite database."""

    db_path: Path

    def __post_init__(self) -> None:
        self.db_path = self.db_path.resolve()

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def connect(self) -> sqlite3.Connection:
        if not self.exists:
            raise FileNotFoundError(f"Standards tables database not found: {self.db_path}")
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self._migrate(connection)
        return connection

    def _migrate(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(lookup_tables)").fetchall()
        }
        if "metadata_json" not in columns:
            connection.execute(
                "ALTER TABLE lookup_tables ADD COLUMN metadata_json TEXT"
            )
            connection.commit()

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)
            self._migrate(connection)

    def resolve_table_id(self, reference: str) -> str | None:
        wanted = reference.strip()
        if not wanted:
            return None

        normalized = wanted.replace("\\", "/")
        if normalized.endswith(".yaml"):
            normalized = normalized[:-5]

        with self.connect() as connection:
            row = connection.execute(
                "SELECT table_id FROM lookup_tables WHERE table_id = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["table_id"])

            row = connection.execute(
                "SELECT table_id FROM lookup_table_aliases WHERE alias = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["table_id"])

            stem = Path(normalized).stem
            if stem and stem != wanted:
                row = connection.execute(
                    "SELECT table_id FROM lookup_tables WHERE table_id = ?",
                    (stem,),
                ).fetchone()
                if row is not None:
                    return str(row["table_id"])
                row = connection.execute(
                    "SELECT table_id FROM lookup_table_aliases WHERE alias = ?",
                    (stem,),
                ).fetchone()
                if row is not None:
                    return str(row["table_id"])

        return None

    def get_table(self, reference: str) -> dict[str, Any] | None:
        table_id = self.resolve_table_id(reference)
        if table_id is None:
            return None

        with self.connect() as connection:
            meta = connection.execute(
                """
                SELECT table_id, title, version, unit, temperature_unit,
                       interpolation, keys_json, layout, subsection, source_node,
                       metadata_json
                FROM lookup_tables
                WHERE table_id = ?
                """,
                (table_id,),
            ).fetchone()
            if meta is None:
                return None

            keys = json.loads(str(meta["keys_json"] or "[]"))
            layout = str(meta["layout"] or "flat_rows")

            result: dict[str, Any] = {
                "table_id": str(meta["table_id"]),
                "title": str(meta["title"]),
                "version": meta["version"],
                "keys": keys,
                "interpolation": bool(meta["interpolation"]),
            }
            if meta["unit"]:
                result["unit"] = meta["unit"]
            if meta["temperature_unit"]:
                result["temperature_unit"] = meta["temperature_unit"]
            if meta["subsection"]:
                result["subsection"] = meta["subsection"]
            if meta["source_node"]:
                result["source_node"] = meta["source_node"]
            if meta["metadata_json"]:
                extra = json.loads(str(meta["metadata_json"]))
                if isinstance(extra, dict):
                    for key, value in extra.items():
                        if key not in result:
                            result[key] = value

            if layout == "material_rows":
                materials: dict[str, Any] = {}
                material_rows = connection.execute(
                    """
                    SELECT material_key, display_name
                    FROM lookup_table_materials
                    WHERE table_id = ?
                    ORDER BY material_key
                    """,
                    (table_id,),
                ).fetchall()
                for material in material_rows:
                    material_key = str(material["material_key"])
                    rows = connection.execute(
                        """
                        SELECT row_json
                        FROM lookup_table_rows
                        WHERE table_id = ? AND material_key = ?
                        ORDER BY sort_order, id
                        """,
                        (table_id, material_key),
                    ).fetchall()
                    materials[material_key] = {
                        "display_name": material["display_name"],
                        "rows": [json.loads(str(row["row_json"])) for row in rows],
                    }
                result["materials"] = materials
            elif layout == "material_catalog":
                materials = {}
                material_rows = connection.execute(
                    """
                    SELECT material_key, display_name
                    FROM lookup_table_materials
                    WHERE table_id = ?
                    ORDER BY material_key
                    """,
                    (table_id,),
                ).fetchall()
                for material in material_rows:
                    material_key = str(material["material_key"])
                    row = connection.execute(
                        """
                        SELECT row_json
                        FROM lookup_table_rows
                        WHERE table_id = ? AND material_key = ?
                        ORDER BY sort_order, id
                        LIMIT 1
                        """,
                        (table_id, material_key),
                    ).fetchone()
                    if row is None:
                        continue
                    materials[material_key] = json.loads(str(row["row_json"]))
                result["materials"] = materials
            else:
                rows = connection.execute(
                    """
                    SELECT row_json
                    FROM lookup_table_rows
                    WHERE table_id = ? AND material_key IS NULL
                    ORDER BY sort_order, id
                    """,
                    (table_id,),
                ).fetchall()
                result["rows"] = [json.loads(str(row["row_json"])) for row in rows]

            return result

    def list_table_ids(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT table_id FROM lookup_tables ORDER BY table_id"
            ).fetchall()
        return [str(row["table_id"]) for row in rows]

    def upsert_table(
        self,
        *,
        table_id: str,
        title: str,
        version: str | None = None,
        unit: str | None = None,
        temperature_unit: str | None = None,
        interpolation: bool = False,
        keys: list[str] | None = None,
        layout: str = "flat_rows",
        subsection: str | None = None,
        source_node: str | None = None,
        metadata: dict[str, Any] | None = None,
        aliases: list[str] | None = None,
        materials: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO lookup_tables (
                    table_id, title, version, unit, temperature_unit,
                    interpolation, keys_json, layout, subsection, source_node,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(table_id) DO UPDATE SET
                    title = excluded.title,
                    version = excluded.version,
                    unit = excluded.unit,
                    temperature_unit = excluded.temperature_unit,
                    interpolation = excluded.interpolation,
                    keys_json = excluded.keys_json,
                    layout = excluded.layout,
                    subsection = excluded.subsection,
                    source_node = excluded.source_node,
                    metadata_json = excluded.metadata_json
                """,
                (
                    table_id,
                    title,
                    version,
                    unit,
                    temperature_unit,
                    int(interpolation),
                    json.dumps(keys or []),
                    layout,
                    subsection,
                    source_node,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            connection.execute(
                "DELETE FROM lookup_table_aliases WHERE table_id = ?",
                (table_id,),
            )
            connection.execute(
                "DELETE FROM lookup_table_materials WHERE table_id = ?",
                (table_id,),
            )
            connection.execute(
                "DELETE FROM lookup_table_rows WHERE table_id = ?",
                (table_id,),
            )

            for alias in aliases or []:
                alias_value = alias.strip()
                if alias_value and alias_value != table_id:
                    connection.execute(
                        """
                        INSERT INTO lookup_table_aliases (alias, table_id)
                        VALUES (?, ?)
                        ON CONFLICT(alias) DO UPDATE SET table_id = excluded.table_id
                        """,
                        (alias_value, table_id),
                    )

            if layout == "material_rows" and materials:
                for material_key, material_data in materials.items():
                    connection.execute(
                        """
                        INSERT INTO lookup_table_materials (table_id, material_key, display_name)
                        VALUES (?, ?, ?)
                        """,
                        (
                            table_id,
                            material_key,
                            material_data.get("display_name"),
                        ),
                    )
                    for sort_order, row in enumerate(material_data.get("rows", []) or []):
                        connection.execute(
                            """
                            INSERT INTO lookup_table_rows
                                (table_id, material_key, row_json, sort_order)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                table_id,
                                material_key,
                                json.dumps(row),
                                sort_order,
                            ),
                        )
            elif layout == "material_catalog" and materials:
                for sort_order, (material_key, material_data) in enumerate(materials.items()):
                    if not isinstance(material_data, dict):
                        continue
                    connection.execute(
                        """
                        INSERT INTO lookup_table_materials (table_id, material_key, display_name)
                        VALUES (?, ?, ?)
                        """,
                        (
                            table_id,
                            material_key,
                            material_data.get("display_name"),
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO lookup_table_rows
                            (table_id, material_key, row_json, sort_order)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            table_id,
                            material_key,
                            json.dumps(material_data),
                            sort_order,
                        ),
                    )
            elif rows is not None:
                for sort_order, row in enumerate(rows):
                    connection.execute(
                        """
                        INSERT INTO lookup_table_rows
                            (table_id, material_key, row_json, sort_order)
                        VALUES (?, NULL, ?, ?)
                        """,
                        (table_id, json.dumps(row), sort_order),
                    )

            connection.commit()
