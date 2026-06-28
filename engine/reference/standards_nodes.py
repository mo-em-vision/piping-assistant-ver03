"""SQLite-backed engineering node content for a standards pack."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS node_records (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'node',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    body TEXT NOT NULL DEFAULT '',
    source_rel_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS node_aliases (
    alias TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    FOREIGN KEY (node_id) REFERENCES node_records(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS node_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    metadata_json TEXT,
    body TEXT NOT NULL DEFAULT '',
    UNIQUE (node_id, asset_type, relative_path),
    FOREIGN KEY (node_id) REFERENCES node_records(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pack_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT,
    node_id TEXT,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_node_assets_node
    ON node_assets(node_id);
"""


@dataclass
class NodeAssetRecord:
    node_id: str
    asset_type: str
    asset_id: str
    relative_path: str
    metadata: dict[str, Any]
    body: str


@dataclass
class StandardsNodesDatabase:
    """Read and write compiled node content for one standards pack."""

    db_path: Path

    def __post_init__(self) -> None:
        self.db_path = self.db_path.resolve()

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def connect(self) -> sqlite3.Connection:
        if not self.exists:
            raise FileNotFoundError(f"Standards nodes database not found: {self.db_path}")
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)

    def clear_all(self) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("DELETE FROM node_assets")
            connection.execute("DELETE FROM node_aliases")
            connection.execute("DELETE FROM pack_index")
            connection.execute("DELETE FROM node_records")
            connection.commit()

    def resolve_node_id(self, reference: str) -> str | None:
        wanted = reference.strip()
        if not wanted:
            return None
        normalized = wanted.replace("\\", "/")
        if normalized.endswith(".md"):
            normalized = normalized[:-3]
        with self.connect() as connection:
            row = connection.execute(
                "SELECT node_id FROM node_records WHERE node_id = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["node_id"])
            row = connection.execute(
                "SELECT node_id FROM node_aliases WHERE alias = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["node_id"])
            stem = Path(normalized).name
            if stem and stem != wanted:
                row = connection.execute(
                    "SELECT node_id FROM node_records WHERE node_id = ?",
                    (stem,),
                ).fetchone()
                if row is not None:
                    return str(row["node_id"])
        return None

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT node_id, kind, metadata_json, body, source_rel_path
                FROM node_records WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
        if row is None:
            return None
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return {
            "node_id": str(row["node_id"]),
            "kind": str(row["kind"]),
            "metadata": metadata,
            "body": str(row["body"] or ""),
            "source_rel_path": str(row["source_rel_path"]),
        }

    def list_node_ids(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT node_id FROM node_records ORDER BY node_id"
            ).fetchall()
        return [str(row["node_id"]) for row in rows]

    def list_pack_index(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT section, node_id, description, sort_order
                FROM pack_index
                ORDER BY sort_order, id
                """
            ).fetchall()
        return [
            {
                "section": str(row["section"]) if row["section"] is not None else None,
                "node_id": str(row["node_id"]) if row["node_id"] is not None else None,
                "description": str(row["description"]) if row["description"] is not None else None,
                "sort_order": int(row["sort_order"]),
            }
            for row in rows
        ]

    def get_node_summaries(self) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT node_id, metadata_json, source_rel_path
                FROM node_records
                ORDER BY node_id
                """
            ).fetchall()
        summaries: dict[str, dict[str, Any]] = {}
        for row in rows:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
            node_id = str(row["node_id"])
            node_type = str(metadata.get("type") or "node")
            summaries[node_id] = {
                "paragraph": str(metadata.get("paragraph") or "").strip() or None,
                "section": str(metadata.get("section") or "").strip() or None,
                "title": str(metadata.get("title") or "").strip() or None,
                "node_type": node_type,
                "revision_year": metadata.get("revision_year"),
                "source_rel_path": str(row["source_rel_path"] or ""),
            }
        return summaries

    def get_assets(self, node_id: str, *, asset_type: str | None = None) -> list[NodeAssetRecord]:
        query = """
            SELECT node_id, asset_type, asset_id, relative_path, metadata_json, body
            FROM node_assets WHERE node_id = ?
        """
        params: list[Any] = [node_id]
        if asset_type:
            query += " AND asset_type = ?"
            params.append(asset_type)
        query += " ORDER BY relative_path"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        assets: list[NodeAssetRecord] = []
        for row in rows:
            meta_raw = row["metadata_json"]
            metadata = json.loads(str(meta_raw)) if meta_raw else {}
            assets.append(
                NodeAssetRecord(
                    node_id=str(row["node_id"]),
                    asset_type=str(row["asset_type"]),
                    asset_id=str(row["asset_id"]),
                    relative_path=str(row["relative_path"]),
                    metadata=metadata if isinstance(metadata, dict) else {},
                    body=str(row["body"] or ""),
                )
            )
        return assets

    def get_asset_by_relative_path(
        self,
        node_id: str,
        relative_path: str,
    ) -> NodeAssetRecord | None:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT node_id, asset_type, asset_id, relative_path, metadata_json, body
                FROM node_assets
                WHERE node_id = ? AND relative_path = ?
                """,
                (node_id, normalized),
            ).fetchone()
        if row is None:
            return None
        meta_raw = row["metadata_json"]
        metadata = json.loads(str(meta_raw)) if meta_raw else {}
        return NodeAssetRecord(
            node_id=str(row["node_id"]),
            asset_type=str(row["asset_type"]),
            asset_id=str(row["asset_id"]),
            relative_path=str(row["relative_path"]),
            metadata=metadata if isinstance(metadata, dict) else {},
            body=str(row["body"] or ""),
        )

    def upsert_node(
        self,
        *,
        node_id: str,
        kind: str,
        metadata: dict[str, Any],
        body: str,
        source_rel_path: str,
        aliases: list[str] | None = None,
    ) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO node_records (node_id, kind, metadata_json, body, source_rel_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    kind = excluded.kind,
                    metadata_json = excluded.metadata_json,
                    body = excluded.body,
                    source_rel_path = excluded.source_rel_path
                """,
                (node_id, kind, json.dumps(metadata, default=str), body, source_rel_path),
            )
            connection.execute(
                "DELETE FROM node_assets WHERE node_id = ?",
                (node_id,),
            )
            for alias in aliases or []:
                alias_value = alias.strip()
                if alias_value and alias_value != node_id:
                    connection.execute(
                        """
                        INSERT INTO node_aliases (alias, node_id) VALUES (?, ?)
                        ON CONFLICT(alias) DO UPDATE SET node_id = excluded.node_id
                        """,
                        (alias_value, node_id),
                    )
            connection.commit()

    def upsert_asset(
        self,
        *,
        node_id: str,
        asset_type: str,
        asset_id: str,
        relative_path: str,
        metadata: dict[str, Any] | None,
        body: str,
    ) -> None:
        self.initialize_schema()
        normalized = relative_path.replace("\\", "/").lstrip("/")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO node_assets (
                    node_id, asset_type, asset_id, relative_path, metadata_json, body
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id, asset_type, relative_path) DO UPDATE SET
                    asset_id = excluded.asset_id,
                    metadata_json = excluded.metadata_json,
                    body = excluded.body
                """,
                (
                    node_id,
                    asset_type,
                    asset_id,
                    normalized,
                    json.dumps(metadata, default=str) if metadata else None,
                    body,
                ),
            )
            connection.commit()

    def upsert_pack_index_row(
        self,
        *,
        section: str | None,
        node_id: str | None,
        description: str | None,
        sort_order: int,
    ) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO pack_index (section, node_id, description, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (section, node_id, description, sort_order),
            )
            connection.commit()
