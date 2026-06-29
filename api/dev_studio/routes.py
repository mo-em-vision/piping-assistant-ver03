"""HTTP route handlers for dev studio API."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs

from api.desktop_service import ApiError
from api.dev_studio.service import DevStudioService


def dev_studio_enabled() -> bool:
    return os.environ.get("DEV_STUDIO_ENABLED", "").strip() in {"1", "true", "yes"}


def require_dev_studio(service: DevStudioService | None) -> DevStudioService:
    if not dev_studio_enabled():
        raise ApiError("not_found", "Dev studio is not enabled", status=404)
    if service is None:
        raise ApiError("not_found", "Dev studio service unavailable", status=404)
    return service


def _pack_from_query(query: dict[str, list[str]], body: dict[str, Any] | None = None) -> str:
    if body and body.get("pack"):
        return str(body["pack"])
    pack = str(query.get("pack", ["asme_b31.3"])[0] or "asme_b31.3")
    return pack


def handle_dev_get(
    path: str,
    query: dict[str, list[str]],
    service: DevStudioService | None,
) -> dict[str, Any]:
    dev = require_dev_studio(service)
    pack = _pack_from_query(query)

    if path == "/api/v1/dev/packs":
        return dev.list_packs()
    if path == "/api/v1/dev/node-types":
        return dev.get_node_types()
    if path == "/api/v1/dev/nodes":
        node_type = query.get("type", [None])[0]
        return dev.list_nodes(pack, node_type=str(node_type) if node_type else None)
    if path == "/api/v1/dev/search":
        q = str(query.get("q", [""])[0] or "")
        node_type = query.get("type", [None])[0]
        return dev.search_nodes(
            pack,
            query=q,
            node_type=str(node_type) if node_type else None,
        )
    if path == "/api/v1/dev/revision":
        return dev.get_revision(pack)
    if path == "/api/v1/dev/relationships":
        node_id = str(query.get("node_id", [""])[0] or "")
        if not node_id:
            raise ApiError("invalid_request", "node_id is required", status=400)
        return dev.get_relationships(pack, node_id)
    if path.startswith("/api/v1/dev/nodes/"):
        node_id = path.removeprefix("/api/v1/dev/nodes/").strip("/")
        if not node_id or "/" in node_id:
            raise ApiError("invalid_request", "Invalid node id", status=400)
        return dev.get_node(pack, node_id)
    if path == "/api/v1/dev/export":
        fmt = str(query.get("format", ["json"])[0] or "json")
        ids_raw = query.get("ids", [""])[0] or ""
        node_ids = [item.strip() for item in ids_raw.split(",") if item.strip()] or None
        return dev.export_nodes(pack, node_ids=node_ids, fmt=fmt)

    raise ApiError("not_found", f"No dev route for {path}", status=404)


def handle_dev_post(
    path: str,
    query: dict[str, list[str]],
    body: dict[str, Any],
    service: DevStudioService | None,
) -> tuple[int, dict[str, Any]]:
    dev = require_dev_studio(service)
    pack = _pack_from_query(query, body)

    if path == "/api/v1/dev/nodes":
        return 201, dev.create_node(pack, body)
    if path == "/api/v1/dev/nodes/validate":
        metadata = dict(body.get("metadata") or body)
        existing_id = body.get("existing_id")
        return 200, dev.validate_payload(
            pack,
            metadata=metadata,
            body=str(body.get("body") or ""),
            existing_id=str(existing_id) if existing_id else None,
        )
    if path == "/api/v1/dev/nodes/bulk":
        return 200, dev.bulk_action(pack, body)
    if path == "/api/v1/dev/import":
        body = dict(body)
        body.setdefault("pack", pack)
        return 200, dev.import_nodes(pack, body)
    if path.startswith("/api/v1/dev/nodes/") and path.endswith("/duplicate"):
        node_id = path.removeprefix("/api/v1/dev/nodes/").removesuffix("/duplicate").strip("/")
        new_id = str(body.get("new_id") or "")
        if not new_id:
            raise ApiError("invalid_request", "new_id is required", status=400)
        rel = body.get("source_rel_path")
        return 201, dev.duplicate_node(
            pack,
            node_id,
            new_id=new_id,
            source_rel_path=str(rel) if rel else None,
        )
    if path.startswith("/api/v1/dev/nodes/") and path.endswith("/equation/preview"):
        node_id = (
            path.removeprefix("/api/v1/dev/nodes/")
            .removesuffix("/equation/preview")
            .strip("/")
        )
        return 200, dev.preview_equation(pack, node_id, body)

    raise ApiError("not_found", f"No dev route for {path}", status=404)


def handle_dev_put(
    path: str,
    query: dict[str, list[str]],
    body: dict[str, Any],
    service: DevStudioService | None,
) -> dict[str, Any]:
    dev = require_dev_studio(service)
    pack = _pack_from_query(query, body)
    if not path.startswith("/api/v1/dev/nodes/"):
        raise ApiError("not_found", f"No dev route for {path}", status=404)
    node_id = path.removeprefix("/api/v1/dev/nodes/").strip("/")
    if not node_id or "/" in node_id:
        raise ApiError("invalid_request", "Invalid node id", status=400)
    return dev.update_node(pack, node_id, body)


def handle_dev_delete(
    path: str,
    query: dict[str, list[str]],
    service: DevStudioService | None,
) -> dict[str, Any]:
    dev = require_dev_studio(service)
    pack = _pack_from_query(query)
    if not path.startswith("/api/v1/dev/nodes/"):
        raise ApiError("not_found", f"No dev route for {path}", status=404)
    node_id = path.removeprefix("/api/v1/dev/nodes/").strip("/")
    if not node_id or "/" in node_id:
        raise ApiError("invalid_request", "Invalid node id", status=400)
    return dev.delete_node(pack, node_id)
