"""Dev studio business logic."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from api.desktop_service import ApiError
from api.dev_studio.graph_sync import remove_node_from_graph_db, sync_node_to_graph_db
from api.dev_studio.node_repository import NodeRepository, StoredNode
from api.dev_studio.revision import compute_pack_revision
from api.dev_studio.serializers import (
    list_node_types,
    node_detail,
    node_summary,
    relationships_payload,
)
from api.dev_studio.validation import validate_node_payload
from engine.equation.sympy_evaluator import evaluate_equation
from engine.reference.graph_db import GraphDatabase
from engine.reference.node_types import is_section_node
from engine.reference.pack_graph_db import resolve_pack_graph_db


@dataclass
class DevStudioService:
    standards_root: Path
    on_pack_changed: Callable[[str], None] | None = None
    _repo: NodeRepository = field(init=False)
    _revision_cache: dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._repo = NodeRepository(self.standards_root)

    def _notify_changed(self, pack: str) -> None:
        self._revision_cache.pop(pack, None)
        if self.on_pack_changed:
            self.on_pack_changed(pack)

    def _graph_db(self, pack: str) -> GraphDatabase:
        pack_root = self._repo.pack_root(pack)
        db_path = resolve_pack_graph_db(pack_root)
        return GraphDatabase(db_path)

    def _all_stored(self, pack: str) -> list[StoredNode]:
        return self._repo.discover_nodes(self._repo.pack_root(pack))

    def _node_exists(self, pack: str) -> Callable[[str], bool]:
        ids = {item.node_id for item in self._all_stored(pack)}

        def exists(node_id: str) -> bool:
            return node_id in ids

        return exists

    def _load_metadata(self, pack: str) -> Callable[[str], dict[str, Any]]:
        by_id = {item.node_id: item.metadata for item in self._all_stored(pack)}

        def load(node_id: str) -> dict[str, Any]:
            return dict(by_id.get(node_id, {}))

        return load

    def list_packs(self) -> dict[str, Any]:
        packs = []
        for item in self._repo.list_packs():
            rev = compute_pack_revision(Path(item["path"]))
            packs.append({**item, **rev.__dict__})
        return {"packs": packs}

    def get_node_types(self) -> dict[str, Any]:
        return list_node_types()

    def list_nodes(self, pack: str, *, node_type: str | None = None) -> dict[str, Any]:
        stored = self._all_stored(pack)
        if node_type:
            stored = [item for item in stored if item.node_type == node_type]
        db = self._graph_db(pack)
        summaries = []
        for item in stored:
            record = db.get_node(item.node_id) if db.exists else None
            if record is not None:
                summaries.append(node_summary(record))
            else:
                summaries.append(
                    {
                        "id": item.node_id,
                        "type": item.node_type,
                        "title": str(item.metadata.get("title") or item.node_id),
                        "description": str(item.metadata.get("description") or ""),
                        "source_rel_path": item.source_rel_path,
                        "unit": str(item.metadata.get("unit") or ""),
                        "category": str(item.metadata.get("topic") or ""),
                        "tags": item.metadata.get("tags") if isinstance(item.metadata.get("tags"), list) else [],
                    }
                )
        return {"pack": pack, "nodes": summaries, "count": len(summaries)}

    def search_nodes(
        self,
        pack: str,
        *,
        query: str = "",
        node_type: str | None = None,
    ) -> dict[str, Any]:
        q = query.strip().lower()
        stored = self._all_stored(pack)
        if node_type:
            stored = [item for item in stored if item.node_type == node_type]
        if not q:
            return self.list_nodes(pack, node_type=node_type)
        matches = []
        for item in stored:
            meta = item.metadata
            haystack = " ".join(
                [
                    item.node_id,
                    item.node_type,
                    str(meta.get("title") or ""),
                    str(meta.get("description") or ""),
                    str(meta.get("sympy") or ""),
                    str(meta.get("unit") or ""),
                    str(meta.get("topic") or meta.get("section") or ""),
                    " ".join(str(t) for t in meta.get("tags", []) if t),
                ]
            ).lower()
            if q in haystack:
                matches.append(item)
        db = self._graph_db(pack)
        summaries = []
        for item in matches:
            record = db.get_node(item.node_id) if db.exists else None
            if record is not None:
                summaries.append(node_summary(record))
            else:
                summaries.append(
                    {
                        "id": item.node_id,
                        "type": item.node_type,
                        "title": str(item.metadata.get("title") or item.node_id),
                        "description": str(item.metadata.get("description") or ""),
                        "source_rel_path": item.source_rel_path,
                        "unit": str(item.metadata.get("unit") or ""),
                        "category": str(item.metadata.get("topic") or ""),
                        "tags": [],
                    }
                )
        return {"pack": pack, "query": query, "nodes": summaries, "count": len(summaries)}

    def get_node(self, pack: str, node_id: str) -> dict[str, Any]:
        stored = self._repo.get_node(pack, node_id)
        if stored is None:
            raise ApiError("not_found", f"Node not found: {node_id}", status=404)
        db = self._graph_db(pack)
        record = db.get_node(node_id) if db.exists else None
        if record is None:
            from engine.reference.graph_db import GraphNodeRecord

            record = GraphNodeRecord(
                node_id=stored.node_id,
                node_type=stored.node_type,
                metadata=stored.metadata,
                body=stored.body,
                source_rel_path=stored.source_rel_path,
            )
        incoming = db.get_incoming(node_id) if db.exists else []
        outgoing = db.get_outgoing(node_id) if db.exists else []
        return node_detail(record, pack=pack, incoming=incoming, outgoing=outgoing)

    def validate_payload(
        self,
        pack: str,
        *,
        metadata: dict[str, Any],
        body: str = "",
        existing_id: str | None = None,
    ) -> dict[str, Any]:
        stored = self._all_stored(pack)
        all_ids = {item.node_id for item in stored}
        all_titles = {
            item.node_id: str(item.metadata.get("title") or "")
            for item in stored
            if item.metadata.get("title")
        }
        result = validate_node_payload(
            pack=pack,
            metadata=metadata,
            body=body,
            node_exists=self._node_exists(pack),
            load_metadata=self._load_metadata(pack),
            existing_id=existing_id,
            all_ids=all_ids,
            all_titles=all_titles,
        )
        return result.to_dict()

    def create_node(self, pack: str, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(payload.get("metadata") or payload)
        body = str(payload.get("body") or "")
        source_rel_path = payload.get("source_rel_path")
        validation = self.validate_payload(pack, metadata=metadata, body=body)
        if not validation["valid"]:
            raise ApiError(
                "validation_failed",
                "Node validation failed",
                status=400,
                details=validation,
            )
        stored = self._repo.write_node(
            pack,
            metadata=metadata,
            body=body,
            source_rel_path=str(source_rel_path) if source_rel_path else None,
        )
        sync_node_to_graph_db(
            self._repo.pack_root(pack),
            node_id=stored.node_id,
            node_type=stored.node_type,
            metadata=stored.metadata,
            body=stored.body,
            source_rel_path=stored.source_rel_path,
        )
        self._notify_changed(pack)
        return self.get_node(pack, stored.node_id)

    def update_node(self, pack: str, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._repo.get_node(pack, node_id)
        if existing is None:
            raise ApiError("not_found", f"Node not found: {node_id}", status=404)
        metadata = dict(payload.get("metadata") or payload)
        body = payload.get("body")
        if body is None:
            body = existing.body
        else:
            body = str(body)
        source_rel_path = payload.get("source_rel_path") or existing.source_rel_path
        new_id = str(metadata.get("id") or node_id).strip()
        force = bool(payload.get("force"))

        if new_id != node_id:
            refs = self._find_references(pack, node_id)
            if refs and not force:
                raise ApiError(
                    "rename_blocked",
                    f"Node is referenced by: {', '.join(refs)}",
                    status=409,
                    details={"references": refs},
                )
            stored = self._repo.rename_node_id(
                pack,
                node_id,
                new_id,
                force=force,
                find_references=lambda nid: self._find_references(pack, nid),
            )
            remove_node_from_graph_db(self._repo.pack_root(pack), node_id)
        else:
            validation = self.validate_payload(
                pack, metadata=metadata, body=body, existing_id=node_id
            )
            if not validation["valid"]:
                raise ApiError(
                    "validation_failed",
                    "Node validation failed",
                    status=400,
                    details=validation,
                )
            stored = self._repo.write_node(
                pack,
                metadata=metadata,
                body=body,
                source_rel_path=str(source_rel_path),
            )

        sync_node_to_graph_db(
            self._repo.pack_root(pack),
            node_id=stored.node_id,
            node_type=stored.node_type,
            metadata=stored.metadata,
            body=stored.body,
            source_rel_path=stored.source_rel_path,
        )
        self._notify_changed(pack)
        return self.get_node(pack, stored.node_id)

    def delete_node(self, pack: str, node_id: str) -> dict[str, Any]:
        if self._repo.get_node(pack, node_id) is None:
            raise ApiError("not_found", f"Node not found: {node_id}", status=404)
        self._repo.delete_node(pack, node_id)
        remove_node_from_graph_db(self._repo.pack_root(pack), node_id)
        self._notify_changed(pack)
        return {"deleted": True, "id": node_id}

    def duplicate_node(
        self,
        pack: str,
        node_id: str,
        *,
        new_id: str,
        source_rel_path: str | None = None,
    ) -> dict[str, Any]:
        if self._repo.get_node(pack, new_id) is not None:
            raise ApiError("duplicate_id", f"Node already exists: {new_id}", status=409)
        stored = self._repo.duplicate_node(
            pack,
            node_id,
            new_id=new_id,
            source_rel_path=source_rel_path,
        )
        sync_node_to_graph_db(
            self._repo.pack_root(pack),
            node_id=stored.node_id,
            node_type=stored.node_type,
            metadata=stored.metadata,
            body=stored.body,
            source_rel_path=stored.source_rel_path,
        )
        self._notify_changed(pack)
        return self.get_node(pack, stored.node_id)

    def get_relationships(self, pack: str, node_id: str) -> dict[str, Any]:
        db = self._graph_db(pack)
        if not db.exists or db.get_node(node_id) is None:
            stored = self._repo.get_node(pack, node_id)
            if stored is None:
                raise ApiError("not_found", f"Node not found: {node_id}", status=404)
            return relationships_payload(node_id, incoming=[], outgoing=[], connected={})
        incoming = db.get_incoming(node_id)
        outgoing = db.get_outgoing(node_id)
        connected = self._connected_nodes(pack, node_id, db)
        return relationships_payload(
            node_id,
            incoming=incoming,
            outgoing=outgoing,
            connected=connected,
        )

    def get_revision(self, pack: str) -> dict[str, Any]:
        rev = compute_pack_revision(self._repo.pack_root(pack))
        return rev.__dict__

    def preview_equation(
        self,
        pack: str,
        node_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        stored = self._repo.get_node(pack, node_id)
        meta = stored.metadata if stored else {}
        sympy_expr = str(payload.get("sympy") or meta.get("sympy") or "")
        display_latex = str(payload.get("display_latex") or meta.get("display_latex") or "")
        symbol_values = payload.get("symbol_values") or {}
        if not isinstance(symbol_values, dict):
            raise ApiError("invalid_request", "symbol_values must be an object", status=400)
        floats = {str(k): float(v) for k, v in symbol_values.items()}
        try:
            result = evaluate_equation(
                sympy_expr=sympy_expr,
                display_latex=display_latex,
                symbol_values=floats,
            )
            return {
                "valid": True,
                "outputs": result.outputs,
                "substitution": result.substitution,
                "result_text": result.result_text,
                "display": result.display,
            }
        except Exception as exc:  # noqa: BLE001
            return {"valid": False, "error": str(exc)}

    def bulk_action(self, pack: str, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action") or "")
        node_ids = [str(item) for item in payload.get("node_ids") or []]
        if not node_ids:
            raise ApiError("invalid_request", "node_ids is required", status=400)

        if action == "delete":
            deleted = []
            for node_id in node_ids:
                try:
                    self.delete_node(pack, node_id)
                    deleted.append(node_id)
                except ApiError:
                    continue
            return {"action": action, "deleted": deleted}

        if action == "add_tags":
            tags = [str(t) for t in payload.get("tags") or []]
            updated = []
            for node_id in node_ids:
                node = self._repo.get_node(pack, node_id)
                if node is None:
                    continue
                meta = dict(node.metadata)
                existing = meta.get("tags") if isinstance(meta.get("tags"), list) else []
                meta["tags"] = list(dict.fromkeys([*existing, *tags]))
                self.update_node(pack, node_id, {"metadata": meta, "body": node.body})
                updated.append(node_id)
            return {"action": action, "updated": updated}

        if action == "remove_tags":
            tags = {str(t) for t in payload.get("tags") or []}
            updated = []
            for node_id in node_ids:
                node = self._repo.get_node(pack, node_id)
                if node is None:
                    continue
                meta = dict(node.metadata)
                existing = meta.get("tags") if isinstance(meta.get("tags"), list) else []
                meta["tags"] = [t for t in existing if t not in tags]
                self.update_node(pack, node_id, {"metadata": meta, "body": node.body})
                updated.append(node_id)
            return {"action": action, "updated": updated}

        if action == "set_topic":
            topic = str(payload.get("topic") or "")
            updated = []
            for node_id in node_ids:
                node = self._repo.get_node(pack, node_id)
                if node is None:
                    continue
                meta = dict(node.metadata)
                meta["topic"] = topic
                self.update_node(pack, node_id, {"metadata": meta, "body": node.body})
                updated.append(node_id)
            return {"action": action, "updated": updated}

        raise ApiError("invalid_request", f"Unknown bulk action: {action}", status=400)

    def export_nodes(
        self,
        pack: str,
        *,
        node_ids: list[str] | None = None,
        fmt: str = "json",
    ) -> dict[str, Any]:
        stored = self._all_stored(pack)
        if node_ids:
            wanted = set(node_ids)
            stored = [item for item in stored if item.node_id in wanted]
        if fmt == "json":
            payload = [
                {
                    "metadata": item.metadata,
                    "body": item.body,
                    "source_rel_path": item.source_rel_path,
                }
                for item in stored
            ]
            return {"format": "json", "content": payload, "count": len(payload)}
        if fmt == "markdown":
            files = []
            for item in stored:
                from engine.reference.standards_markdown import compose_frontmatter

                files.append(
                    {
                        "path": f"{item.source_rel_path}/node.yaml",
                        "content": compose_frontmatter(item.metadata, item.body),
                    }
                )
            return {"format": "markdown", "files": files, "count": len(files)}
        if fmt == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["id", "type", "title", "source_rel_path", "description"])
            for item in stored:
                writer.writerow(
                    [
                        item.node_id,
                        item.node_type,
                        item.metadata.get("title", ""),
                        item.source_rel_path,
                        item.metadata.get("description", ""),
                    ]
                )
            return {"format": "csv", "content": buffer.getvalue(), "count": len(stored)}
        raise ApiError("invalid_request", f"Unsupported export format: {fmt}", status=400)

    def import_nodes(self, pack: str, payload: dict[str, Any]) -> dict[str, Any]:
        fmt = str(payload.get("format") or "json")
        created: list[str] = []
        updated: list[str] = []
        errors: list[dict[str, str]] = []

        if fmt == "json":
            items = payload.get("nodes") or payload.get("content") or []
            if not isinstance(items, list):
                raise ApiError("invalid_request", "Expected nodes array", status=400)
            for item in items:
                if not isinstance(item, dict):
                    continue
                meta = dict(item.get("metadata") or item)
                body = str(item.get("body") or "")
                node_id = str(meta.get("id") or "")
                rel = item.get("source_rel_path")
                try:
                    if self._repo.get_node(pack, node_id):
                        self.update_node(
                            pack,
                            node_id,
                            {"metadata": meta, "body": body, "source_rel_path": rel},
                        )
                        updated.append(node_id)
                    else:
                        self.create_node(
                            pack,
                            {"metadata": meta, "body": body, "source_rel_path": rel},
                        )
                        created.append(node_id)
                except ApiError as exc:
                    errors.append({"id": node_id, "message": exc.message})
            return {"created": created, "updated": updated, "errors": errors}

        raise ApiError("invalid_request", f"Unsupported import format: {fmt}", status=400)

    def _find_references(self, pack: str, node_id: str) -> list[str]:
        refs: list[str] = []
        for item in self._all_stored(pack):
            if item.node_id == node_id:
                continue
            text = json.dumps(item.metadata, default=str)
            if node_id in text:
                refs.append(item.node_id)
        return refs

    def _connected_nodes(
        self,
        pack: str,
        node_id: str,
        db: GraphDatabase,
    ) -> dict[str, list[str]]:
        equations: set[str] = set()
        workflows: set[str] = set()
        sections: set[str] = set()
        visited: set[str] = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            record = db.get_node(current)
            if record is None:
                continue
            if record.node_type == "equation":
                equations.add(current)
            elif record.node_type == "workflow":
                workflows.add(current)
            elif is_section_node(record.metadata, record.node_type):
                sections.add(current)
            for edge in db.get_outgoing(current) + db.get_incoming(current):
                other = edge.to_id if edge.from_id == current else edge.from_id
                if other not in visited:
                    queue.append(other)
        return {
            "equations": sorted(equations),
            "workflows": sorted(workflows),
            "sections": sorted(sections),
        }
