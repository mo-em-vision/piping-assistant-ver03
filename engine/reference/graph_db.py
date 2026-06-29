"""SQLite-backed micro-graph nodes and semantic edges for a standards pack."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    body TEXT NOT NULL DEFAULT '',
    source_rel_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    relationship_key TEXT NOT NULL DEFAULT '',
    metadata_json TEXT,
    UNIQUE (from_id, to_id, edge_type, relationship_key),
    FOREIGN KEY (from_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (to_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS graph_aliases (
    alias TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    FOREIGN KEY (node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS graph_cache_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON graph_edges(from_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON graph_edges(to_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
"""


@dataclass
class GraphNodeRecord:
    node_id: str
    node_type: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str


@dataclass
class GraphEdgeRecord:
    from_id: str
    to_id: str
    edge_type: str
    metadata: dict[str, Any]


def relationship_key_for_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""
    alias = metadata.get("alias")
    if alias is not None and str(alias).strip():
        return f"alias:{str(alias).strip()}"
    return ""


def _migrate_graph_edges_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(graph_edges)").fetchall()
    if not rows:
        return
    columns = {str(row[1]) for row in rows}
    if "relationship_key" in columns:
        return
    connection.executescript(
        """
        CREATE TABLE graph_edges_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            relationship_key TEXT NOT NULL DEFAULT '',
            metadata_json TEXT,
            UNIQUE (from_id, to_id, edge_type, relationship_key),
            FOREIGN KEY (from_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
        );
        INSERT INTO graph_edges_v2 (from_id, to_id, edge_type, relationship_key, metadata_json)
        SELECT from_id, to_id, edge_type, '', metadata_json FROM graph_edges;
        DROP TABLE graph_edges;
        ALTER TABLE graph_edges_v2 RENAME TO graph_edges;
        CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON graph_edges(from_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON graph_edges(to_id);
        """
    )


@dataclass
class GraphDatabase:
    """Read and write compiled micro-graph content for one standards pack."""

    db_path: Path

    def __post_init__(self) -> None:
        self.db_path = self.db_path.resolve()

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def connect(self) -> sqlite3.Connection:
        if not self.exists:
            raise FileNotFoundError(f"Graph database not found: {self.db_path}")
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)
            _migrate_graph_edges_schema(connection)
            connection.commit()

    def clear_all(self) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("DELETE FROM graph_aliases")
            connection.execute("DELETE FROM graph_edges")
            connection.execute("DELETE FROM graph_nodes")
            connection.execute("DELETE FROM graph_cache_meta")
            connection.commit()

    def get_meta(self, key: str) -> str | None:
        if not self.exists:
            return None
        try:
            with self.connect() as connection:
                row = connection.execute(
                    "SELECT meta_value FROM graph_cache_meta WHERE meta_key = ?",
                    (key,),
                ).fetchone()
        except sqlite3.OperationalError:
            return None
        if row is None:
            return None
        return str(row["meta_value"])

    def set_meta(self, key: str, value: str) -> None:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO graph_cache_meta (meta_key, meta_value) VALUES (?, ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                """,
                (key, value),
            )
            connection.commit()

    def import_pack_graph(self, graph: Any) -> None:
        """Replace cache tables with a compiled in-memory pack graph."""
        from engine.graph.pack_graph import PackGraph

        if not isinstance(graph, PackGraph):
            raise TypeError("graph must be a PackGraph")
        self.clear_all()
        for node in graph.nodes.values():
            aliases = [
                alias
                for alias, target in graph.aliases.items()
                if target == node.node_id
            ]
            self.upsert_node(
                node_id=node.node_id,
                node_type=node.node_type,
                metadata=node.metadata,
                body=node.body,
                source_rel_path=node.source_rel_path,
                aliases=aliases or None,
            )
        for edge in graph.edges:
            self.upsert_edge(
                from_id=edge.from_id,
                to_id=edge.to_id,
                edge_type=edge.edge_type,
                metadata=edge.metadata or None,
            )
        self.set_meta("source_fingerprint", graph.source_fingerprint)

    def export_pack_graph(self, pack_root: Path) -> Any:
        """Reconstruct a pack graph from the SQLite cache."""
        from engine.graph.pack_graph import PackGraph

        nodes = {node.node_id: node for node in self.list_all_nodes()}
        aliases: dict[str, str] = {}
        if self.exists:
            with self.connect() as connection:
                rows = connection.execute(
                    "SELECT alias, node_id FROM graph_aliases ORDER BY alias"
                ).fetchall()
            for row in rows:
                aliases[str(row["alias"])] = str(row["node_id"])
        fingerprint = self.get_meta("source_fingerprint") or ""
        return PackGraph(
            pack_root=str(pack_root.resolve()),
            source_fingerprint=fingerprint,
            nodes=nodes,
            edges=self.get_edges(),
            aliases=aliases,
        )

    def resolve_node_id(self, reference: str) -> str | None:
        wanted = reference.strip()
        if not wanted:
            return None
        with self.connect() as connection:
            row = connection.execute(
                "SELECT node_id FROM graph_nodes WHERE node_id = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["node_id"])
            row = connection.execute(
                "SELECT node_id FROM graph_aliases WHERE alias = ?",
                (wanted,),
            ).fetchone()
            if row is not None:
                return str(row["node_id"])
        return None

    def get_node(self, node_id: str) -> GraphNodeRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT node_id, node_type, metadata_json, body, source_rel_path
                FROM graph_nodes WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
        if row is None:
            return None
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return GraphNodeRecord(
            node_id=str(row["node_id"]),
            node_type=str(row["node_type"]),
            metadata=metadata if isinstance(metadata, dict) else {},
            body=str(row["body"] or ""),
            source_rel_path=str(row["source_rel_path"]),
        )

    def list_node_ids(self, *, node_type: str | None = None) -> list[str]:
        with self.connect() as connection:
            if node_type:
                rows = connection.execute(
                    "SELECT node_id FROM graph_nodes WHERE node_type = ? ORDER BY node_id",
                    (node_type,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT node_id FROM graph_nodes ORDER BY node_id"
                ).fetchall()
        return [str(row["node_id"]) for row in rows]

    def list_workflows(self) -> list[GraphNodeRecord]:
        return [
            node
            for node_id in self.list_node_ids(node_type="workflow")
            if (node := self.get_node(node_id)) is not None
        ]

    def get_edges(
        self,
        *,
        from_id: str | None = None,
        to_id: str | None = None,
        edge_type: str | None = None,
    ) -> list[GraphEdgeRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if from_id:
            clauses.append("from_id = ?")
            params.append(from_id)
        if to_id:
            clauses.append("to_id = ?")
            params.append(to_id)
        if edge_type:
            clauses.append("edge_type = ?")
            params.append(edge_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT from_id, to_id, edge_type, metadata_json
                FROM graph_edges {where}
                ORDER BY from_id, to_id, edge_type
                """,
                params,
            ).fetchall()
        edges: list[GraphEdgeRecord] = []
        for row in rows:
            meta_raw = row["metadata_json"]
            metadata = json.loads(str(meta_raw)) if meta_raw else {}
            edges.append(
                GraphEdgeRecord(
                    from_id=str(row["from_id"]),
                    to_id=str(row["to_id"]),
                    edge_type=str(row["edge_type"]),
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
            )
        return edges

    def get_outgoing(self, node_id: str) -> list[GraphEdgeRecord]:
        return self.get_edges(from_id=node_id)

    def get_incoming(self, node_id: str) -> list[GraphEdgeRecord]:
        return self.get_edges(to_id=node_id)

    def upsert_node(
        self,
        *,
        node_id: str,
        node_type: str,
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
                INSERT INTO graph_nodes (node_id, node_type, metadata_json, body, source_rel_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    node_type = excluded.node_type,
                    metadata_json = excluded.metadata_json,
                    body = excluded.body,
                    source_rel_path = excluded.source_rel_path
                """,
                (
                    node_id,
                    node_type,
                    json.dumps(metadata, default=str),
                    body,
                    source_rel_path,
                ),
            )
            for alias in aliases or []:
                alias_value = alias.strip()
                if alias_value and alias_value != node_id:
                    connection.execute(
                        """
                        INSERT INTO graph_aliases (alias, node_id) VALUES (?, ?)
                        ON CONFLICT(alias) DO UPDATE SET node_id = excluded.node_id
                        """,
                        (alias_value, node_id),
                    )
            connection.commit()

    def upsert_edge(
        self,
        *,
        from_id: str,
        to_id: str,
        edge_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.initialize_schema()
        rel_key = relationship_key_for_metadata(metadata)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO graph_edges (from_id, to_id, edge_type, relationship_key, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(from_id, to_id, edge_type, relationship_key) DO UPDATE SET
                    metadata_json = excluded.metadata_json
                """,
                (
                    from_id,
                    to_id,
                    edge_type,
                    rel_key,
                    json.dumps(metadata, default=str) if metadata else None,
                ),
            )
            connection.commit()

    def delete_edges_for_node(self, node_id: str) -> None:
        """Remove all edges where node is source or target."""
        if not self.exists:
            return
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "DELETE FROM graph_edges WHERE from_id = ? OR to_id = ?",
                (node_id, node_id),
            )
            connection.commit()

    def delete_node(self, node_id: str) -> bool:
        """Delete a node, its aliases, and all connected edges."""
        if not self.exists:
            return False
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                "DELETE FROM graph_nodes WHERE node_id = ?",
                (node_id,),
            )
            connection.commit()
            return cursor.rowcount > 0

    def list_all_nodes(self) -> list[GraphNodeRecord]:
        records: list[GraphNodeRecord] = []
        for node_id in self.list_node_ids():
            record = self.get_node(node_id)
            if record is not None:
                records.append(record)
        return records

    def count_nodes(self) -> int:
        if not self.exists:
            return 0
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS c FROM graph_nodes").fetchone()
        return int(row["c"]) if row else 0
