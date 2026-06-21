"""Read engineering knowledge nodes from standards/ (reference data only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_paths import list_standard_packs, resolve_standard_pack


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
        for item in self.metadata.get("depends_on", []) or []:
            if isinstance(item, dict):
                node_id = item.get("node_id")
                if node_id:
                    deps.append(str(node_id))
            elif isinstance(item, str):
                deps.append(item)
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


class StandardsReader:
    """Load nodes and roots from the on-disk standards pack."""

    def __init__(self, standards_root: Path, *, standard: str = "asme_b31.3") -> None:
        self.standards_root = standards_root.resolve()
        self.standard = standard
        self.pack_root = resolve_standard_pack(self.standards_root, standard)
        self.nodes_dir = self.pack_root / "nodes"
        self.roots_dir = self.pack_root / "roots"
        self.tables_dir = self.pack_root / "tables"

    def load_table(self, table_rel: str) -> dict[str, Any]:
        """Load a YAML table from the current standards pack."""
        path = self.pack_root / table_rel
        if not path.exists():
            raise FileNotFoundError(f"Table not found: {path}")
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    @staticmethod
    def resolve_pack(standards_root: Path, standard: str) -> Path:
        return resolve_standard_pack(standards_root, standard)

    @staticmethod
    def list_packs(standards_root: Path) -> list[tuple[str, Path]]:
        return list_standard_packs(standards_root)

    def find_node_path(self, node_id: str) -> Path | None:
        if node_id.endswith("/root") or node_id.endswith("root.md"):
            slug = node_id.replace("/root", "").replace("root.md", "").strip("/")
            if slug:
                candidate = self.roots_dir / slug / "root.md"
                if candidate.exists():
                    return candidate
        if node_id.startswith("roots/"):
            candidate = self.pack_root / node_id
            if candidate.suffix != ".md":
                candidate = candidate / "root.md"
            if candidate.exists():
                return candidate

        if self.nodes_dir.is_dir():
            direct = self.nodes_dir / node_id / "node.md"
            if direct.exists():
                return direct

            for path in self.nodes_dir.glob("*/node.md"):
                record = self.load_file(path)
                if record.node_id == node_id:
                    return path

        if self.roots_dir.is_dir():
            for path in self.roots_dir.glob("*/root.md"):
                record = self.load_file(path)
                if record.node_id == node_id or path.parent.name == node_id:
                    return path

        return None

    def load(self, node_id: str) -> NodeRecord:
        path = self.find_node_path(node_id)
        if path is None:
            raise FileNotFoundError(f"Node not found in standards pack: {node_id}")
        return self.load_file(path)

    def load_subsection(self, node_id: str, subsection_id: str) -> NodeSubsection:
        """Load a structured subsection without treating it as a graph node."""
        record = self.load(node_id)
        wanted = subsection_id.strip().lower().strip("()")
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
    def load_file(path: Path) -> NodeRecord:
        text = path.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(text)
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

        node_dir = record.path.parent
        equation_refs = record.metadata.get("equations", []) or record.metadata.get("formulas", []) or []
        label = "equation" if record.metadata.get("equations") is not None else "formula"
        for equation in equation_refs:
            if not isinstance(equation, dict):
                continue
            file_name = equation.get("file")
            if file_name and not (node_dir / file_name).exists():
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


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return metadata, body


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
