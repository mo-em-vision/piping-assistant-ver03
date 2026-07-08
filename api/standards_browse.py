"""Build standards browse tree payloads for the desktop UI."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from api.serializers import _workflow_meta
from engine.graph.graph_engine import normalize_root_id
from engine.reference.graph_compile import LEGACY_NODE_ID_ALIASES
from engine.reference.standards_paths import resolve_global_tasks_db, resolve_standard_pack
from engine.reference.standards_reader import StandardsReader
from engine.reference.standards_tasks_db import StandardsTasksDatabase

_DEFAULT_STANDARD_LABEL = "ASME B31.3"
_SUPPORTED_BROWSE_STANDARDS = frozenset({"asme_b31.3"})
_INDEX_WORKFLOW_ALIASES = {
    "pipe-wall-thickness": "pipe_wall_thickness_design",
    "pipe-wall-thickness.yaml": "pipe_wall_thickness_design",
    "mawp": "mawp_design",
    "mawp.yaml": "mawp_design",
}


def _workflow_slug_from_metadata(metadata: dict[str, Any], source_ref: str) -> str:
    for field in ("key", "engineering_intent"):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    slug = normalize_root_id(source_ref)
    if slug.endswith(".yaml"):
        slug = slug[:-5]
    return _INDEX_WORKFLOW_ALIASES.get(slug, slug)


def _is_pack_workflow_record(source_rel_path: str) -> bool:
    return source_rel_path.startswith("workflows/")


def _workflow_linked_node_ids(metadata: dict[str, Any]) -> set[str]:
    nodes: set[str] = set()
    anchors_to = metadata.get("anchors_to")
    if isinstance(anchors_to, str) and anchors_to.strip():
        nodes.add(anchors_to.strip())
    depends_on = metadata.get("depends_on") or []
    if isinstance(depends_on, list):
        for dep in depends_on:
            if isinstance(dep, dict):
                node_id = str(dep.get("node_id") or "").strip()
                if node_id:
                    nodes.add(node_id)
    for edge in metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        edge_type = str(edge.get("type") or "").strip()
        target = str(edge.get("target") or "").strip()
        if not target or edge_type not in {"depends_on", "starts_from_paragraph"}:
            continue
        if target.startswith(("WF-", "B313-WF-")):
            continue
        nodes.add(target)
    for entry in metadata.get("entry_points") or []:
        if isinstance(entry, dict):
            paragraph = str(entry.get("paragraph") or "").strip()
            if paragraph:
                nodes.add(paragraph)
    return nodes


def _node_metadata(reader: StandardsReader, node_id: str) -> dict[str, Any]:
    record = reader.nodes_database.get_node(node_id)
    if record is None:
        return {}
    metadata = record.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _resolve_table_id_for_node(
    reader: StandardsReader,
    node_id: str,
    metadata: dict[str, Any],
) -> str | None:
    lookups = metadata.get("lookups") or []
    if isinstance(lookups, list):
        for lookup in lookups:
            if isinstance(lookup, dict):
                table_id = str(lookup.get("table_id") or "").strip()
                if table_id:
                    resolved = reader.tables_database.resolve_table_id(table_id)
                    return resolved or table_id

    lookup_block = metadata.get("lookup")
    if isinstance(lookup_block, dict):
        table_id = str(lookup_block.get("table") or "").strip()
        if table_id:
            resolved = reader.tables_database.resolve_table_id(table_id)
            return resolved or table_id

    if node_id.startswith("B313-table-"):
        suffix = node_id.removeprefix("B313-table-")
        candidates = [
            suffix,
            suffix.replace("-", "."),
            f"table_{suffix.replace('-', '_')}",
        ]
        for candidate in candidates:
            resolved = reader.tables_database.resolve_table_id(candidate)
            if resolved:
                return resolved

    if node_id.startswith("asme-b313-table-"):
        suffix = node_id.removeprefix("asme-b313-table-")
        candidates = [
            node_id,
            f"asme_b31.3_{suffix}",
            suffix,
            f"table_{suffix.replace('-', '_')}",
        ]
        for candidate in candidates:
            resolved = reader.tables_database.resolve_table_id(candidate)
            if resolved:
                return resolved

    table_number = str(metadata.get("table_number") or "").strip()
    if table_number:
        resolved = reader.tables_database.resolve_table_id(table_number)
        if resolved:
            return resolved

    return reader.tables_database.resolve_table_id(node_id)


def _content_kind(node_type: str, node_id: str, source_rel_path: str = "") -> str:
    normalized = source_rel_path.replace("\\", "/")
    if (
        node_type == "lookup"
        or node_id.startswith("B313-table-")
        or "/nodes/tables/" in normalized
        or normalized.startswith("nodes/tables/")
    ):
        return "table"
    return "node"


def _leaf_kind(content_kind: str) -> str:
    return "table" if content_kind == "table" else "node"


def _path_segments_after_nodes(source_rel_path: str) -> list[str]:
    normalized = source_rel_path.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    if parts and parts[0] == "nodes":
        parts = parts[1:]
    return parts


def _top_section_folder(source_rel_path: str) -> str | None:
    parts = _path_segments_after_nodes(source_rel_path)
    return parts[0] if parts else None


def _workflow_group_key(summary: dict[str, Any]) -> str | None:
    paragraph = str(summary.get("paragraph") or "").strip()
    if paragraph and paragraph[0].isdigit():
        return paragraph.split(".", 1)[0]
    node_id = str(summary.get("node_id") or "")
    if node_id.startswith("B313-table-") or node_id.startswith("B313-lookup-"):
        return "appendix_A"
    return _top_section_folder(str(summary.get("source_rel_path") or ""))


def _flat_layout_subgroup(leaf: dict[str, Any]) -> str | None:
    content_kind = str(leaf.get("content_kind") or "")
    if content_kind == "table":
        return "tables"
    node_id = str(leaf.get("node_id") or "")
    if node_id.startswith("B313-lookup-"):
        return "lookups"
    return None


def _workflow_summary(workflow_id: str) -> dict[str, Any]:
    meta = _workflow_meta(workflow_id)
    return {
        "id": str(meta["id"]),
        "name": str(meta["name"]),
        "description": str(meta["description"]),
        "discipline": str(meta["discipline"]),
        "available": bool(meta["available"]),
    }


def _dedupe_workflows(workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for item in workflows:
        workflow_id = str(item["id"])
        if workflow_id in seen:
            continue
        seen.add(workflow_id)
        ordered.append(item)
    return ordered


def _build_node_workflow_map(
    *,
    standards_root: Path,
    standard_slug: str,
    summaries: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    tasks_db_path = resolve_global_tasks_db(standards_root)
    if not tasks_db_path.is_file():
        return {}

    database = StandardsTasksDatabase(tasks_db_path)
    node_workflows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    folder_workflows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    prefix = f"{standard_slug}/"
    for root_id in database.list_node_ids():
        record = database.get_node(root_id)
        if record is None:
            continue
        metadata = record.get("metadata") or {}
        if str(metadata.get("type") or "") not in {"root", "workflow"}:
            continue
        source_rel_path = str(record.get("source_rel_path") or "")
        if not _is_pack_workflow_record(source_rel_path) and not source_rel_path.startswith(prefix):
            continue

        workflow_id = _workflow_slug_from_metadata(metadata, source_rel_path)
        workflow = _workflow_summary(workflow_id)

        depended_nodes = _workflow_linked_node_ids(metadata)

        for node_id in depended_nodes:
            node_workflows[node_id].append(workflow)
            summary = summaries.get(node_id)
            if summary is None:
                continue
            top_folder = _workflow_group_key(summary)
            if top_folder:
                folder_workflows[top_folder].append(workflow)

    for node_id, summary in summaries.items():
        top_folder = _workflow_group_key(summary)
        if not top_folder:
            continue
        node_workflows[node_id].extend(folder_workflows.get(top_folder, []))

    return {node_id: _dedupe_workflows(items) for node_id, items in node_workflows.items()}


def _short_section_label(label: str) -> str:
    text = label.strip()
    if " — " in text:
        return text.split(" — ", 1)[0].strip()
    if " - " in text:
        return text.split(" - ", 1)[0].strip()
    return text


def _workflow_leaf(*, workflow_id: str, label: str, workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"workflow:{workflow_id}",
        "kind": "workflow",
        "label": label,
        "description": workflow["description"],
        "workflow_id": workflow_id,
        "related_workflows": [workflow],
    }


def _build_available_tasks_entries(
    *,
    standards_root: Path,
    standard_slug: str,
) -> list[dict[str, Any]]:
    tasks_db_path = resolve_global_tasks_db(standards_root)
    if not tasks_db_path.is_file():
        return []

    database = StandardsTasksDatabase(tasks_db_path)
    entries: list[dict[str, Any]] = []

    for root_id in database.list_node_ids():
        record = database.get_node(root_id)
        if record is None:
            continue
        metadata = record.get("metadata") or {}
        if str(metadata.get("type") or "") not in {"root", "workflow"}:
            continue
        source_rel_path = str(record.get("source_rel_path") or "")
        if not _is_pack_workflow_record(source_rel_path):
            continue

        workflow_id = _workflow_slug_from_metadata(metadata, source_rel_path)
        workflow = _workflow_summary(workflow_id)
        if not workflow["available"]:
            continue

        title = str(metadata.get("title") or workflow["name"]).strip() or workflow["name"]
        entries.append(_workflow_leaf(workflow_id=workflow_id, label=title, workflow=workflow))

    return entries


def _build_available_tasks_group(
    *,
    standards_root: Path,
    standard_slug: str,
    pack_root: Path,
) -> dict[str, Any] | None:
    entries = _build_available_tasks_entries(
        standards_root=standards_root,
        standard_slug=standard_slug,
    )
    if not entries:
        entries = _parse_analysis_entry_points(pack_root)
        entries = [
            entry
            for entry in entries
            if entry.get("related_workflows")
            and entry["related_workflows"][0].get("available")
        ]

    if not entries:
        return None

    return {
        "id": "section:available-tasks",
        "kind": "group",
        "label": "Available tasks",
        "children": entries,
    }


def _parse_analysis_entry_points(pack_root: Path) -> list[dict[str, Any]]:
    index_path = pack_root / "index.md"
    if not index_path.is_file():
        return []

    entries: list[dict[str, Any]] = []
    in_section = False
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Analysis entry points"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|") or line.startswith("|--") or "Analysis" in line:
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue

        title = cells[0].strip()
        link_match = link_pattern.search(cells[1])
        if not title or link_match is None:
            continue

        workflow_id = _workflow_slug_from_metadata({}, link_match.group(1))
        workflow = _workflow_summary(workflow_id)
        entries.append(_workflow_leaf(workflow_id=workflow_id, label=title, workflow=workflow))

    return entries


def _normalize_path_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _folder_parts_after_section_root(folder_parts: list[str], section_label: str) -> list[str]:
    if not folder_parts:
        return folder_parts

    normalized_section = _normalize_path_token(section_label)
    normalized_first = _normalize_path_token(folder_parts[0])
    if normalized_section and normalized_first == normalized_section:
        return folder_parts[1:]
    return folder_parts


def _ensure_group(
    children: list[dict[str, Any]],
    *,
    group_id: str,
    label: str,
) -> dict[str, Any]:
    for child in children:
        if child.get("id") == group_id and child.get("kind") == "group":
            return child

    group = {
        "id": group_id,
        "kind": "group",
        "label": label,
        "children": [],
    }
    children.append(group)
    return group


def _insert_leaf(
    section_children: list[dict[str, Any]],
    *,
    section_label: str,
    section_key: str,
    source_rel_path: str,
    leaf: dict[str, Any],
) -> None:
    parts = _path_segments_after_nodes(source_rel_path)
    if not parts:
        section_children.append(leaf)
        return

    folder_parts = _folder_parts_after_section_root(parts[:-1], section_label)
    if not folder_parts and len(parts) <= 1:
        subgroup = _flat_layout_subgroup(leaf)
        if subgroup:
            group_id = f"group:{section_key}/{subgroup}"
            group = _ensure_group(section_children, group_id=group_id, label=subgroup)
            group.setdefault("children", []).append(leaf)
            return

    current_children = section_children
    path_prefix = section_key

    for folder in folder_parts:
        path_prefix = f"{path_prefix}/{folder}"
        group_id = f"group:{path_prefix}"
        group = _ensure_group(current_children, group_id=group_id, label=folder)
        current_children = group.setdefault("children", [])

    current_children.append(leaf)


def _build_section_tree(
    *,
    section_label: str,
    rows: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
    node_workflows: dict[str, list[dict[str, Any]]],
    reader: StandardsReader,
) -> dict[str, Any]:
    section_key = section_label.replace(" ", "-").lower()
    section_children: list[dict[str, Any]] = []

    for row in rows:
        node_id = str(row.get("node_id") or "").strip()
        if not node_id:
            continue
        summary = summaries.get(node_id, {})
        node_type = str(summary.get("node_type") or "node")
        content_kind = _content_kind(
            node_type,
            node_id,
            str(summary.get("source_rel_path") or ""),
        )
        paragraph = summary.get("paragraph")
        title = summary.get("title")
        label = f"§{paragraph}" if paragraph else (title or node_id)
        description = str(row.get("description") or "").strip() or None

        leaf: dict[str, Any] = {
            "id": node_id,
            "kind": _leaf_kind(content_kind),
            "label": label,
            "description": description,
            "node_id": node_id,
            "content_kind": content_kind,
            "related_workflows": node_workflows.get(
                LEGACY_NODE_ID_ALIASES.get(node_id, node_id),
                node_workflows.get(node_id, []),
            ),
        }
        if content_kind == "table":
            table_id = _resolve_table_id_for_node(reader, node_id, _node_metadata(reader, node_id))
            if table_id:
                leaf["table_id"] = table_id
        _insert_leaf(
            section_children,
            section_label=section_label,
            section_key=section_key,
            source_rel_path=str(summary.get("source_rel_path") or ""),
            leaf=leaf,
        )

    return {
        "id": f"section:{section_key}",
        "kind": "group",
        "label": _short_section_label(section_label),
        "children": section_children,
    }


def _revision_year_from_summaries(summaries: dict[str, dict[str, Any]]) -> int | None:
    for summary in summaries.values():
        value = summary.get("revision_year")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def build_standards_browse_payload(reader: StandardsReader, *, standard: str) -> dict[str, Any]:
    standard_slug = standard.strip().lower()
    if standard_slug not in _SUPPORTED_BROWSE_STANDARDS:
        raise FileNotFoundError(f"Standards browse is not available for: {standard}")

    if not reader.nodes_db_available:
        raise FileNotFoundError("Standards nodes database is not available")

    nodes_db = reader.nodes_database
    summaries = nodes_db.get_node_summaries()
    pack_index = nodes_db.list_pack_index()
    node_workflows = _build_node_workflow_map(
        standards_root=reader.standards_root,
        standard_slug=standard_slug,
        summaries=summaries,
    )

    tree: list[dict[str, Any]] = []

    available_tasks_group = _build_available_tasks_group(
        standards_root=reader.standards_root,
        standard_slug=standard_slug,
        pack_root=reader.pack_root,
    )
    if available_tasks_group is not None:
        tree.append(available_tasks_group)

    section_order: list[str] = []
    section_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pack_index:
        section = _short_section_label(str(row.get("section") or "Standards").strip() or "Standards")
        if section not in section_order:
            section_order.append(section)
        section_rows[section].append(row)

    for section_label in section_order:
        tree.append(
            _build_section_tree(
                section_label=section_label,
                rows=section_rows[section_label],
                summaries=summaries,
                node_workflows=node_workflows,
                reader=reader,
            )
        )

    workflow_index: dict[str, list[dict[str, Any]]] = {}
    for node_id, workflows in node_workflows.items():
        workflow_index[node_id] = workflows

    return {
        "standard": _DEFAULT_STANDARD_LABEL,
        "standard_slug": standard_slug,
        "revision_year": _revision_year_from_summaries(summaries),
        "tree": tree,
        "workflow_index": workflow_index,
    }


def resolve_browse_standard(standards_root: Path, standard: str | None) -> str:
    wanted = (standard or "asme_b31.3").strip().lower()
    resolve_standard_pack(standards_root, wanted)
    return wanted
