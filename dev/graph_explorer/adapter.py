"""Read active task subgraph from session state and GraphStore."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from config.loader import CLIConfig
from engine.graph.graph_engine import normalize_root_id, resolve_workflow_node_id
from engine.graph.graph_store import GraphStore
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.reference.standards_paths import list_standard_packs
from engine.state.state_manager import TaskStateManager
from models.task import Task
from storage.migrate_legacy_sessions import migrate_legacy_sessions
from storage.project_repository import ProjectRepository
from storage.project_session_store import ProjectSessionStore, get_database_for_config

from dev.graph_explorer.serializer import (
    EdgeRefDto,
    GraphContextDto,
    GraphEdgeDto,
    GraphNodeDto,
    GraphSnapshotDto,
    NodeDetailDto,
)

_INPUT_EDGE_TYPES = frozenset({"requires", "uses", "depends_on", "uses_table", "accepts"})
_OUTPUT_EDGE_TYPES = frozenset({"calculates", "outputs", "defines", "derived_from"})


@dataclass
class TaskContext:
    task_id: str | None
    workflow_id: str | None
    active_nodes: list[str]
    session_id: str


class GraphViewProvider(Protocol):
    def get_context(self) -> GraphContextDto: ...

    def get_snapshot(self) -> GraphSnapshotDto: ...

    def get_node(self, node_id: str) -> NodeDetailDto | None: ...

    def reload(self) -> None: ...


def _node_name(record: GraphNodeRecord) -> str:
    meta = record.metadata
    for key in ("title", "symbol", "name", "id"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return record.node_id


def _node_description(record: GraphNodeRecord) -> str:
    meta = record.metadata
    for key in ("description", "summary"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    body = record.body.strip()
    if body:
        return body[:500] + ("…" if len(body) > 500 else "")
    return ""


def _workflow_id_from_task(task: Task) -> str | None:
    outputs = task.outputs if isinstance(task.outputs, dict) else {}
    for key in ("workflow", "selected_root", "graph_root"):
        value = outputs.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_root_id(value.strip())
    return None


class TaskContextReader:
    """Load active task context from the same session storage as the desktop app."""

    def __init__(self, config: CLIConfig, session_id: str) -> None:
        self.config = config
        self.session_id = session_id

    def read(self) -> TaskContext:
        database = get_database_for_config(self.config.sessions_dir)
        migrate_legacy_sessions(database, self.config.sessions_dir)
        repository = ProjectRepository(database)
        if repository.get_project(self.session_id) is None:
            repository.ensure_project(self.session_id)
        store = ProjectSessionStore(database, self.config.sessions_dir, session_id=self.session_id)
        manager = store.load_state_manager()
        return self._context_from_manager(manager)

    def _context_from_manager(self, manager: TaskStateManager) -> TaskContext:
        active = manager.get_active_task()
        if active is None:
            tasks = manager.list_tasks()
            if not tasks:
                return TaskContext(
                    task_id=None,
                    workflow_id=None,
                    active_nodes=[],
                    session_id=self.session_id,
                )
            active = tasks[-1]

        workflow_id = _workflow_id_from_task(active)
        return TaskContext(
            task_id=active.task_id,
            workflow_id=workflow_id,
            active_nodes=list(active.active_nodes),
            session_id=self.session_id,
        )


class GraphExplorerAdapter:
    """Build induced subgraph snapshots from GraphStore + active task nodes."""

    def __init__(self, config: CLIConfig, session_id: str) -> None:
        self.config = config
        self.session_id = session_id
        self._context_reader = TaskContextReader(config, session_id)
        self._stores: dict[str, GraphStore] = {}
        self._node_pack: dict[str, str] = {}
        self._reload_stores()

    def reload(self) -> None:
        self._reload_stores()

    def _reload_stores(self) -> None:
        self._stores.clear()
        self._node_pack.clear()
        for slug, pack_root in list_standard_packs(self.config.standards_root):
            store = GraphStore(pack_root)
            store.load()
            if not store.available:
                continue
            self._stores[slug] = store
            for node in store.list_nodes():
                self._node_pack[node.node_id] = slug

    def get_context(self) -> GraphContextDto:
        ctx = self._context_reader.read()
        snapshot = self._build_subgraph(ctx.active_nodes)
        message = None
        if not ctx.task_id:
            message = "No active task. Create or activate a task in the desktop app."
        elif not ctx.active_nodes:
            message = "Active task has no active_nodes yet."
        return GraphContextDto(
            task_id=ctx.task_id,
            workflow_id=ctx.workflow_id,
            session_id=ctx.session_id,
            node_count=len(snapshot[0]),
            edge_count=len(snapshot[1]),
            message=message,
        )

    def get_snapshot(self) -> GraphSnapshotDto:
        ctx = self._context_reader.read()
        nodes, edges = self._build_subgraph(ctx.active_nodes)
        revision = self._compute_revision(ctx, nodes, edges)
        context = GraphContextDto(
            task_id=ctx.task_id,
            workflow_id=ctx.workflow_id,
            session_id=ctx.session_id,
            node_count=len(nodes),
            edge_count=len(edges),
            message=None if ctx.active_nodes else "Active task has no active_nodes yet.",
        )
        return GraphSnapshotDto(revision=revision, context=context, nodes=nodes, edges=edges)

    def get_node(self, node_id: str) -> NodeDetailDto | None:
        record = self._find_node(node_id)
        if record is None:
            return None
        ctx = self._context_reader.read()
        active = set(ctx.active_nodes)
        slug = self._node_pack.get(node_id, "")
        store = self._stores.get(slug)
        if store is None:
            return None

        incoming: list[EdgeRefDto] = []
        outgoing: list[EdgeRefDto] = []
        inputs: list[str] = []
        outputs: list[str] = []

        for edge in store.incoming(node_id):
            if active and edge.from_id not in active:
                continue
            incoming.append(EdgeRefDto(edge_type=edge.edge_type, peer_id=edge.from_id, direction="incoming"))
        for edge in store.outgoing(node_id):
            if active and edge.to_id not in active:
                continue
            outgoing.append(EdgeRefDto(edge_type=edge.edge_type, peer_id=edge.to_id, direction="outgoing"))
            if edge.edge_type in _INPUT_EDGE_TYPES:
                inputs.append(edge.to_id if edge.from_id == node_id else edge.from_id)
            if edge.edge_type in _OUTPUT_EDGE_TYPES:
                outputs.append(edge.to_id)

        meta = dict(record.metadata)
        standard_refs: list[str] = []
        for key in ("located_in", "anchors_to", "standard"):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                standard_refs.append(value.strip())
            elif isinstance(value, list):
                standard_refs.extend(str(item) for item in value if item)

        requires = meta.get("requires")
        if isinstance(requires, list):
            for item in requires:
                if isinstance(item, str):
                    inputs.append(item)
                elif isinstance(item, dict) and item.get("node_id"):
                    inputs.append(str(item["node_id"]))

        body = record.body.strip()
        body_preview = body[:1000] + ("…" if len(body) > 1000 else "")

        return NodeDetailDto(
            id=record.node_id,
            node_type=record.node_type,
            name=_node_name(record),
            description=_node_description(record),
            inputs=sorted(set(inputs)),
            outputs=sorted(set(outputs)),
            incoming_edges=incoming,
            outgoing_edges=outgoing,
            metadata=meta,
            standard_refs=sorted(set(standard_refs)),
            body_preview=body_preview,
        )

    def search_nodes(self, query: str, *, limit: int = 50) -> list[GraphNodeDto]:
        ctx = self._context_reader.read()
        nodes, _ = self._build_subgraph(ctx.active_nodes)
        needle = query.strip().lower()
        if not needle:
            return nodes[:limit]
        matches = [
            node
            for node in nodes
            if needle in node.id.lower() or needle in node.name.lower()
        ]
        return matches[:limit]

    def _find_node(self, node_id: str) -> GraphNodeRecord | None:
        slug = self._node_pack.get(node_id)
        if slug and slug in self._stores:
            return self._stores[slug].get_node(node_id)
        for store in self._stores.values():
            record = store.get_node(node_id)
            if record is not None:
                return record
        return None

    def _build_subgraph(
        self,
        active_nodes: list[str],
    ) -> tuple[list[GraphNodeDto], list[GraphEdgeDto]]:
        if not active_nodes:
            return [], []

        active_set = set(active_nodes)
        node_dtos: list[GraphNodeDto] = []
        edge_dtos: list[GraphEdgeDto] = []
        seen_edges: set[tuple[str, str, str]] = set()

        for node_id in active_nodes:
            record = self._find_node(node_id)
            if record is None:
                node_dtos.append(
                    GraphNodeDto(
                        id=node_id,
                        node_type="unknown",
                        name=node_id,
                        description="Node not found in compiled graph databases.",
                        pack="",
                        metadata={},
                    )
                )
                continue
            slug = self._node_pack.get(node_id, "")
            node_dtos.append(
                GraphNodeDto(
                    id=record.node_id,
                    node_type=record.node_type,
                    name=_node_name(record),
                    description=_node_description(record),
                    pack=slug,
                    metadata=dict(record.metadata),
                )
            )

        for node_id in active_nodes:
            slug = self._node_pack.get(node_id)
            store = self._stores.get(slug) if slug else None
            if store is None:
                continue
            for edge in store.outgoing(node_id):
                if edge.to_id not in active_set:
                    continue
                key = (edge.from_id, edge.to_id, edge.edge_type)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edge_dtos.append(self._edge_to_dto(edge))
            for edge in store.incoming(node_id):
                if edge.from_id not in active_set:
                    continue
                key = (edge.from_id, edge.to_id, edge.edge_type)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edge_dtos.append(self._edge_to_dto(edge))

        return node_dtos, edge_dtos

    @staticmethod
    def _edge_to_dto(edge: GraphEdgeRecord) -> GraphEdgeDto:
        edge_id = f"{edge.from_id}|{edge.edge_type}|{edge.to_id}"
        return GraphEdgeDto(
            id=edge_id,
            source=edge.from_id,
            target=edge.to_id,
            edge_type=edge.edge_type,
            metadata=dict(edge.metadata),
        )

    def _compute_revision(
        self,
        ctx: TaskContext,
        nodes: list[GraphNodeDto],
        edges: list[GraphEdgeDto],
    ) -> str:
        import hashlib

        db_mtimes: list[float] = []
        for store in self._stores.values():
            path = store.db_path
            if path.is_file():
                db_mtimes.append(path.stat().st_mtime)

        tasks_path = self.config.sessions_dir / ctx.session_id / "tasks.json"
        tasks_mtime = tasks_path.stat().st_mtime if tasks_path.is_file() else 0.0

        payload = {
            "task_id": ctx.task_id,
            "active_nodes": sorted(ctx.active_nodes),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "db_mtimes": sorted(db_mtimes),
            "tasks_mtime": tasks_mtime,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return digest[:16]
