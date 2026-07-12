"""Read engineering knowledge nodes from standards/ (reference data only)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.reference.node_types import is_section_node
from engine.reference.graph_compile import LEGACY_NODE_ID_ALIASES, parse_dependency_node_ref
from engine.reference.graph_edge_schema import edge_target, iter_stored_edges
from engine.reference.relationship_taxonomy import DEPENDENCY_TRAVERSAL_TYPES
from engine.reference.embedded_nodes import find_embedded_body, iter_embedded_node_sources
from engine.reference.equation_sidecar import merge_equation_sidecar_metadata
from engine.reference.paragraph_sidecar import merge_paragraph_sidecar_metadata
from engine.reference.workflow_sidecar import merge_workflow_sidecar_metadata
from engine.reference.pack_metadata import apply_pack_metadata, load_pack_metadata
from engine.reference.pack_graph_db import resolve_pack_graph_db
from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_markdown import compose_frontmatter, merge_dual_node_frontmatter, split_frontmatter
from engine.reference.standards_nodes import StandardsNodesDatabase
from engine.reference.standards_paths import (
    list_standard_packs,
    resolve_global_tasks_db,
    resolve_pack_workflows_dir,
    resolve_pack_tasks_dir,
    resolve_standard_pack,
)
from engine.reference.standards_tables import StandardsTablesDatabase
from engine.reference.standards_tasks_db import StandardsTasksDatabase

_logger = logging.getLogger(__name__)
_warned_missing_nodes_db: set[str] = set()


@dataclass
class NodeRecord:
    node_id: str
    path: Path
    metadata: dict[str, Any]
    body: str

    @property
    def node_type(self) -> str | None:
        return self.metadata.get("type")

    @property
    def depends_on(self) -> list[str]:
        deps: list[str] = []
        for item in iter_stored_edges(self.metadata):
            if str(item.get("type") or "") not in DEPENDENCY_TRAVERSAL_TYPES:
                continue
            target = edge_target(item)
            if target:
                base_id, _ = parse_dependency_node_ref(target)
                deps.append(base_id)
        return deps


@dataclass
class NodeSubsection:
    node_id: str
    subsection_id: str
    paragraph: str
    metadata: dict[str, Any]
    body: str


@dataclass
class ValidationIssue:
    level: str
    message: str


@dataclass
class NodeValidationResult:
    node_id: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


_LEGACY_SECTION_ENRICH_KEYS = (
    "inputs",
    "equations",
    "formulas",
    "subsections",
    "display_heading",
    "purpose",
    "references",
    "nomenclature",
    "interactions",
)


class StandardsReader:
    """Load nodes from compiled pack graph (Markdown/YAML sources) with SQLite caches."""

    def __init__(self, standards_root: Path, *, standard: str = "asme_b31.3") -> None:
        self.standards_root = standards_root.resolve()
        self.standard = standard
        self.pack_root = resolve_standard_pack(self.standards_root, standard)
        self.nodes_dir = self.pack_root / "nodes"
        self.tasks_dir = resolve_pack_workflows_dir(self.pack_root)
        self.tables_db_path = resolve_pack_tables_db(self.pack_root)
        self.nodes_db_path = resolve_pack_nodes_db(self.pack_root)
        self.graph_db_path = resolve_pack_graph_db(self.pack_root)
        self.tasks_db_path = resolve_global_tasks_db(self.standards_root)
        self._tables_db = StandardsTablesDatabase(self.tables_db_path)
        self._nodes_db = StandardsNodesDatabase(self.nodes_db_path)
        self._tasks_db = StandardsTasksDatabase(self.tasks_db_path)
        self._graph_store: Any | None = None
        self._node_path_cache: dict[str, Path | None] = {}
        self._node_record_cache: dict[str, NodeRecord] = {}
        self._pack_metadata: dict[str, Any] | None = None

    @property
    def pack_metadata(self) -> dict[str, Any]:
        if self._pack_metadata is None:
            self._pack_metadata = load_pack_metadata(self.pack_root)
        return self._pack_metadata

    @property
    def graph_store(self) -> "GraphStore":
        from engine.graph.graph_store import GraphStore

        if self._graph_store is None:
            self._graph_store = GraphStore(self.pack_root)
        return self._graph_store

    def reload(self) -> None:
        """Clear in-memory caches after graph sources or cache files change."""
        if self._graph_store is not None:
            self._graph_store.reload()
        self._node_path_cache.clear()
        self._node_record_cache.clear()

    @property
    def roots_dir(self) -> Path:
        """Legacy alias for :attr:`tasks_dir`."""
        return self.tasks_dir

    @property
    def tables_database(self) -> StandardsTablesDatabase:
        return self._tables_db

    @property
    def nodes_database(self) -> StandardsNodesDatabase:
        return self._nodes_db

    @property
    def tasks_database(self) -> StandardsTasksDatabase:
        return self._tasks_db

    @property
    def nodes_db_available(self) -> bool:
        return self._nodes_db.exists

    @property
    def tasks_db_available(self) -> bool:
        return self._tasks_db.exists

    def _warn_missing_nodes_db_once(self) -> None:
        key = str(self.pack_root)
        if key in _warned_missing_nodes_db:
            return
        _warned_missing_nodes_db.add(key)
        _logger.warning(
            "Pack nodes database not found at %s; falling back to markdown files. "
            "Run scripts/build_standards_nodes_db.py",
            self.nodes_db_path,
        )

    def _virtual_node_path(self, source_rel_path: str, *, kind: str) -> Path:
        if kind in {"root", "workflow"}:
            text = source_rel_path.replace("\\", "/")
            prefix = f"{self.standard}/"
            if text.startswith(prefix):
                text = text.removeprefix(prefix)
            direct = self.pack_root / text
            if direct.is_file():
                return direct
            return direct
        direct = self.pack_root / source_rel_path
        if direct.is_file():
            return direct
        base = direct
        for name in ("node.yaml", "node.yml", "node.md"):
            candidate = base / name
            if candidate.is_file():
                return candidate
        return base / "node.md"

    def _record_from_tasks_db(self, node_id: str) -> NodeRecord | None:
        if not self.tasks_db_available:
            return None
        resolved_id = self._tasks_db.resolve_node_id(node_id) or node_id
        data = self._tasks_db.get_node(resolved_id)
        if data is None:
            return None
        path = self._virtual_node_path(str(data["source_rel_path"]), kind=str(data.get("kind") or "workflow"))
        return NodeRecord(
            node_id=str(data["node_id"]),
            path=path,
            metadata=data["metadata"],
            body=str(data["body"]),
        )

    @property
    def graph_available(self) -> bool:
        return self.graph_store.available

    @property
    def graph_db_available(self) -> bool:
        """Legacy alias — graph is available when sources compile, not when SQLite exists."""
        return self.graph_available

    def _record_from_graph_db(self, node_id: str) -> NodeRecord | None:
        if not self.graph_available:
            return None
        store = self.graph_store
        resolved_id = store.resolve_node_id(node_id) or node_id
        record = store.get_node(resolved_id)
        if record is None:
            return None
        base = self.pack_root / record.source_rel_path
        path = base if base.is_file() else None
        if path is None:
            for name in ("node.md", "node.yaml", "node.yml"):
                candidate = base / name
                if candidate.is_file():
                    path = candidate
                    break
        if path is None:
            path = base if base.suffix in {".yaml", ".yml", ".md"} else base / "node.yaml"
        metadata = dict(record.metadata)
        metadata.setdefault("type", record.node_type)
        body = record.body
        markdown_path = base / "node.md"
        if markdown_path.is_file():
            markdown_record = self.load_file(markdown_path)
            metadata, body = merge_dual_node_frontmatter(
                base,
                metadata,
                body,
                primary_path=path if path.suffix in {".yaml", ".yml"} else markdown_path,
            )
            if len(markdown_record.body.strip()) >= len(body.strip()):
                body = markdown_record.body
        return NodeRecord(
            node_id=record.node_id,
            path=path,
            metadata=metadata,
            body=body,
        )

    def _record_from_nodes_db_only(self, node_id: str) -> NodeRecord | None:
        if not self.nodes_db_available:
            return None
        resolved_id = self._nodes_db.resolve_node_id(node_id) or node_id
        data = self._nodes_db.get_node(resolved_id)
        if data is None or str(data["kind"]) == "root":
            return None
        path = self._virtual_node_path(str(data["source_rel_path"]), kind=str(data["kind"]))
        markdown_path = path if path.suffix == ".md" else path.with_suffix(".md")
        body = str(data["body"])
        if markdown_path.is_file():
            markdown_record = self.load_file(markdown_path)
            if len(markdown_record.body.strip()) >= len(body.strip()):
                body = markdown_record.body
        return NodeRecord(
            node_id=str(data["node_id"]),
            path=path,
            metadata=data["metadata"],
            body=body,
        )

    def _record_from_embedded_source(self, node_id: str) -> NodeRecord | None:
        if not self.nodes_dir.is_dir():
            return None
        for path in self.nodes_dir.rglob("node.md"):
            record = self.load_file(path)
            if record.node_id == node_id:
                return record
            metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
            for embedded in iter_embedded_node_sources(
                parent_id=record.node_id,
                parent_source_rel_path=str(path.parent.relative_to(self.pack_root).as_posix()),
                metadata=metadata,
            ):
                if embedded.node_id == node_id:
                    return NodeRecord(
                        node_id=embedded.node_id,
                        path=path,
                        metadata=embedded.metadata,
                        body=embedded.body or body,
                    )
        for path in self.nodes_dir.rglob("node.yaml"):
            record = self.load_file(path)
            if record.node_id == node_id:
                return record
            metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
            for embedded in iter_embedded_node_sources(
                parent_id=record.node_id,
                parent_source_rel_path=str(path.parent.relative_to(self.pack_root).as_posix()),
                metadata=metadata,
            ):
                if embedded.node_id == node_id:
                    return NodeRecord(
                        node_id=embedded.node_id,
                        path=path,
                        metadata=embedded.metadata,
                        body=embedded.body or body,
                    )
        return None

    def _apply_pack_metadata(self, record: NodeRecord) -> NodeRecord:
        metadata = apply_pack_metadata(record.metadata, self.pack_metadata)
        if metadata is record.metadata:
            return record
        return NodeRecord(
            node_id=record.node_id,
            path=record.path,
            metadata=metadata,
            body=record.body,
        )

    def _enrich_equation_record(self, record: NodeRecord) -> NodeRecord:
        if str(record.metadata.get("type", "")) != "equation":
            return record
        metadata = merge_equation_sidecar_metadata(
            record.metadata,
            record_path=record.path,
            node_id=record.node_id,
        )
        if metadata is record.metadata:
            return record
        return NodeRecord(
            node_id=record.node_id,
            path=record.path,
            metadata=metadata,
            body=record.body,
        )

    def _enrich_paragraph_record(self, record: NodeRecord) -> NodeRecord:
        if str(record.metadata.get("type", "")) != "paragraph":
            return record
        metadata = dict(record.metadata)
        if record.path is not None and record.path.is_file():
            file_record = self.load_file(record.path)
            metadata = file_record.metadata
        metadata = merge_paragraph_sidecar_metadata(
            metadata,
            record_path=record.path,
            node_id=record.node_id,
        )
        if (
            not metadata.get("presentation")
            and record.path is not None
            and record.path.is_file()
        ):
            file_meta = self.load_file(record.path).metadata
            presentation = file_meta.get("presentation")
            if isinstance(presentation, dict) and presentation:
                metadata = dict(metadata)
                metadata["presentation"] = presentation
        if metadata is record.metadata:
            return record
        return NodeRecord(
            node_id=record.node_id,
            path=record.path,
            metadata=metadata,
            body=record.body,
        )

    def _enrich_workflow_record(self, record: NodeRecord) -> NodeRecord:
        if str(record.metadata.get("type", "")) != "workflow":
            return record
        metadata = dict(record.metadata)
        if record.path is not None and record.path.is_file():
            file_record = self.load_file(record.path)
            metadata = file_record.metadata
        metadata = merge_workflow_sidecar_metadata(
            metadata,
            record_path=record.path,
            node_id=record.node_id,
        )
        if metadata is record.metadata:
            return record
        return NodeRecord(
            node_id=record.node_id,
            path=record.path,
            metadata=metadata,
            body=record.body,
        )

    def _enrich_standard_section_record(self, record: NodeRecord) -> NodeRecord:
        if not is_section_node(record.metadata):
            return record
        legacy = self._record_from_nodes_db_only(record.node_id)
        if legacy is None or str(legacy.metadata.get("status", "")).lower() != "superseded":
            return record
        metadata = dict(record.metadata)
        for key in _LEGACY_SECTION_ENRICH_KEYS:
            legacy_value = legacy.metadata.get(key)
            if legacy_value and not metadata.get(key):
                metadata[key] = legacy_value
        body = legacy.body if len(legacy.body.strip()) > len(record.body.strip()) else record.body
        return NodeRecord(
            node_id=record.node_id,
            path=record.path,
            metadata=metadata,
            body=body,
        )

    def _record_from_db(self, node_id: str) -> NodeRecord | None:
        root_record = self._record_from_tasks_db(node_id)
        if root_record is not None:
            return root_record
        nodes_record = self._record_from_nodes_db_only(node_id)
        if nodes_record is not None:
            return nodes_record
        graph_record = self._record_from_graph_db(node_id)
        if graph_record is not None:
            return self._enrich_standard_section_record(graph_record)
        return None

    def load_table(self, table_ref: str) -> dict[str, Any]:
        """Load a lookup table from the pack SQLite database."""
        data = self._tables_db.get_table(table_ref)
        if data is None:
            raise FileNotFoundError(f"Table not found in standards pack: {table_ref}")
        return data

    def find_table_path(self, table_id: str) -> Path | None:
        if self._tables_db.resolve_table_id(table_id) is None:
            return None
        return self.tables_db_path

    def load_table_by_id(self, table_id: str) -> tuple[Path, dict[str, Any]]:
        data = self._tables_db.get_table(table_id)
        if data is None:
            raise FileNotFoundError(f"Table not found in standards pack: {table_id}")
        return self.tables_db_path, data

    @staticmethod
    def resolve_pack(standards_root: Path, standard: str) -> Path:
        return resolve_standard_pack(standards_root, standard)

    @staticmethod
    def list_packs(standards_root: Path) -> list[tuple[str, Path]]:
        return list_standard_packs(standards_root)

    def find_node_path(self, node_id: str) -> Path | None:
        if node_id in self._node_path_cache:
            return self._node_path_cache[node_id]

        resolved: Path | None = None
        if self.nodes_db_available:
            data = self._nodes_db.get_node(self._nodes_db.resolve_node_id(node_id) or node_id)
            if data is not None:
                resolved = self._virtual_node_path(str(data["source_rel_path"]), kind=str(data["kind"]))

        if resolved is None and (node_id.endswith("/root") or node_id.endswith("root.md")):
            slug = node_id.replace("/root", "").replace("root.md", "").strip("/")
            if slug:
                candidate = self.tasks_dir / slug / "root.md"
                if candidate.exists():
                    resolved = candidate
        if resolved is None and node_id.startswith("tasks/"):
            candidate = self.standards_root / node_id
            if candidate.suffix != ".md":
                candidate = candidate / "root.md"
            if candidate.exists():
                resolved = candidate
        if resolved is None and node_id.startswith("roots/"):
            candidate = self.pack_root / node_id
            if candidate.suffix != ".md":
                candidate = candidate / "root.md"
            if candidate.exists():
                resolved = candidate

        if resolved is None and self.nodes_dir.is_dir():
            from engine.reference.node_sources import iter_node_source_paths

            for path in iter_node_source_paths(self.nodes_dir):
                record = self.load_file(path)
                if record.node_id == node_id:
                    resolved = path
                    break
            if resolved is None:
                for name in ("node.yaml", "node.yml", "node.md"):
                    direct = self.nodes_dir / node_id / name
                    if direct.is_file():
                        resolved = direct
                        break
            if resolved is None:
                self._warn_missing_nodes_db_once()
                for path in self.nodes_dir.rglob("node.md"):
                    record = self.load_file(path)
                    if record.node_id == node_id:
                        resolved = path
                        break
                if resolved is None:
                    embedded = self._record_from_embedded_source(node_id)
                    if embedded is not None:
                        resolved = embedded.path

        if resolved is None and self.tasks_dir.is_dir():
            self._warn_missing_nodes_db_once()
            for path in self.tasks_dir.glob("*/root.md"):
                record = self.load_file(path)
                if record.node_id == node_id or path.parent.name == node_id:
                    resolved = path
                    break

        self._node_path_cache[node_id] = resolved
        return resolved

    def load(self, node_id: str) -> NodeRecord:
        node_id = LEGACY_NODE_ID_ALIASES.get(node_id, node_id)
        if node_id in self._node_record_cache:
            return self._node_record_cache[node_id]

        record = self._record_from_db(node_id)
        if record is None:
            path = self.find_node_path(node_id)
            if path is None:
                embedded = self._record_from_embedded_source(node_id)
                if embedded is None:
                    raise FileNotFoundError(f"Node not found in standards pack: {node_id}")
                record = embedded
            elif path.is_file():
                record = self.load_file(path)
                if record.node_id != node_id:
                    embedded = self._record_from_embedded_source(node_id)
                    if embedded is not None:
                        record = embedded
            else:
                embedded = self._record_from_embedded_source(node_id)
                if embedded is not None:
                    record = embedded
                else:
                    raise FileNotFoundError(f"Node not found in standards pack: {node_id}")

        enriched = self._apply_pack_metadata(
            self._enrich_workflow_record(
                self._enrich_equation_record(self._enrich_paragraph_record(record))
            )
        )
        self._node_record_cache[node_id] = enriched
        return self._node_record_cache[node_id]

    def load_subsection(self, node_id: str, subsection_id: str) -> NodeSubsection:
        """Load a structured subsection without treating it as a graph node."""
        wanted = subsection_id.strip().lower().strip("()")
        subsection_node_id = self._subsection_node_id(node_id, wanted)
        if subsection_node_id:
            try:
                record = self.load(subsection_node_id)
            except FileNotFoundError:
                subsection_node_id = None
            else:
                meta = record.metadata
                body = _authority_text_from_record(meta, record.body)
                return NodeSubsection(
                    node_id=record.node_id,
                    subsection_id=wanted,
                    paragraph=str(
                        meta.get("paragraph_number")
                        or meta.get("paragraph")
                        or subsection_node_id
                    ),
                    metadata=meta,
                    body=body,
                )

        record = self.load(node_id)
        for item in record.metadata.get("subsections", []) or []:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip().lower().strip("()")
            label = str(item.get("label", "")).strip().lower().strip("()")
            paragraph = str(item.get("paragraph", "")).strip().lower()
            if wanted not in {item_id, label} and not paragraph.endswith(f"({wanted})"):
                continue
            return NodeSubsection(
                node_id=record.node_id,
                subsection_id=str(item.get("id", wanted)),
                paragraph=str(item.get("paragraph", "")),
                metadata=item,
                body=_extract_subsection_body(record.body, wanted),
            )
        raise KeyError(f"Subsection {subsection_id!r} not found in node: {node_id}")

    @staticmethod
    def _subsection_node_id(node_id: str, subsection_id: str) -> str | None:
        """Map parent + subsection letter to a dedicated paragraph node id."""
        import re

        text = str(node_id).strip()
        wanted = subsection_id.strip().lower().strip("()")
        if not text or not wanted:
            return None
        match = re.match(r"^(.+)-([a-z])$", text)
        if match and match.group(2) == wanted:
            return text
        base = match.group(1) if match else text
        return f"{base}-{wanted}"

    def resolve_asset_path(self, record: NodeRecord, file_ref: str) -> Path | None:
        file_ref = str(file_ref).strip()
        if not file_ref:
            return None
        ref_path = Path(file_ref)
        if ref_path.is_absolute():
            return ref_path if ref_path.is_file() else None
        if file_ref.startswith("nodes/"):
            candidate = self.pack_root / file_ref
            return candidate if candidate.is_file() else None
        candidate = record.path.parent / file_ref
        if candidate.is_file():
            return candidate
        if self.nodes_db_available:
            relative = file_ref.replace("\\", "/").lstrip("/")
            if not relative.startswith(("equations/", "conditions/", "notes/", "references/")):
                relative = f"equations/{relative}"
            asset = self._nodes_db.get_asset_by_relative_path(record.node_id, relative)
            if asset is not None:
                disk_path = record.path.parent / relative
                if disk_path.is_file():
                    return disk_path
        return candidate if candidate.is_file() else None

    def read_asset_text(self, record: NodeRecord, file_ref: str) -> str | None:
        path = self.resolve_asset_path(record, file_ref)
        if path is not None and path.is_file():
            return path.read_text(encoding="utf-8")

        embedded_body = find_embedded_body(record.metadata, file_ref)
        if embedded_body is not None:
            return embedded_body

        relative = str(file_ref).replace("\\", "/").lstrip("/")
        if relative.startswith("nodes/"):
            parts = relative.split("/")
            if len(parts) >= 3:
                other_node_id = parts[1]
                other_path = "/".join(parts[2:])
                if self.nodes_db_available:
                    other_asset = self._nodes_db.get_asset_by_relative_path(other_node_id, other_path)
                    if other_asset is not None:
                        if other_asset.metadata:
                            return compose_frontmatter(other_asset.metadata, other_asset.body)
                        if other_asset.body:
                            return other_asset.body
                try:
                    other_record = self.load(other_node_id)
                except FileNotFoundError:
                    other_record = None
                if other_record is not None:
                    nested = find_embedded_body(other_record.metadata, other_path)
                    if nested is not None:
                        return nested

        if self.nodes_db_available:
            if not relative.startswith(("equations/", "conditions/", "notes/", "references/")):
                if "/" not in relative:
                    relative = f"equations/{relative}"
            asset = self._nodes_db.get_asset_by_relative_path(record.node_id, relative)
            if asset is not None:
                if asset.metadata:
                    return compose_frontmatter(asset.metadata, asset.body)
                if asset.body:
                    return asset.body

        return None

    @staticmethod
    def load_file(path: Path) -> NodeRecord:
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        node_id = str(metadata.get("id") or path.parent.name)
        return NodeRecord(node_id=node_id, path=path, metadata=metadata, body=body)

    def dependency_tree(self, node_id: str, *, _visited: set[str] | None = None) -> dict[str, Any]:
        _visited = _visited or set()
        record = self.load(node_id)
        if record.node_id in _visited:
            return {"id": record.node_id, "cycle": True}
        _visited.add(record.node_id)

        children = []
        for dep in record.depends_on:
            try:
                children.append(self.dependency_tree(dep, _visited=_visited.copy()))
            except FileNotFoundError:
                children.append({"id": dep, "missing": True})

        return {
            "id": record.node_id,
            "type": record.node_type,
            "children": children,
        }

    def validate(self, node_id: str) -> NodeValidationResult:
        issues: list[ValidationIssue] = []
        try:
            record = self.load(node_id)
        except FileNotFoundError as exc:
            return NodeValidationResult(
                node_id=node_id,
                passed=False,
                issues=[ValidationIssue("error", str(exc))],
            )

        if not record.metadata.get("id"):
            issues.append(ValidationIssue("error", "Missing required field: id"))
        if not record.metadata.get("type"):
            issues.append(ValidationIssue("error", "Missing required field: type"))

        equation_refs = record.metadata.get("equations", []) or record.metadata.get("formulas", []) or []
        label = "equation" if record.metadata.get("equations") is not None else "formula"
        for equation in equation_refs:
            if not isinstance(equation, dict):
                continue
            file_name = equation.get("file")
            if file_name and self.resolve_asset_path(record, str(file_name)) is None:
                if self.read_asset_text(record, str(file_name)) is None:
                    issues.append(
                        ValidationIssue("error", f"Missing {label} file: {file_name}")
                    )

        for dep in record.depends_on:
            if self.find_node_path(dep) is None:
                issues.append(
                    ValidationIssue("warning", f"Unresolved dependency reference: {dep}")
                )

        errors = [issue for issue in issues if issue.level == "error"]
        return NodeValidationResult(
            node_id=record.node_id,
            passed=not errors,
            issues=issues,
        )


def _authority_text_from_record(metadata: dict[str, Any], body: str) -> str:
    body_text = body.strip()
    if body_text:
        return body_text
    text_block = metadata.get("text") or {}
    if isinstance(text_block, dict):
        return str(text_block.get("original") or "").strip()
    return ""


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    return split_frontmatter(text)


def _extract_subsection_body(body: str, subsection_id: str) -> str:
    """Best-effort extraction for headings like '**e) ...**'."""
    wanted = subsection_id.strip().lower().strip("()")
    lines = body.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith(f"**{wanted})") or stripped.startswith(f"**{wanted}."):
            start = index
            break
    if start is None:
        return ""

    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip().lower()
        if not stripped.startswith("**") or len(stripped) < 4:
            continue
        marker = stripped[2]
        if marker.isalpha() and stripped[3] in {")", "."}:
            end = index
            break
    return "\n".join(lines[start:end]).strip()
