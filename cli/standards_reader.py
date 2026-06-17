"""Read engineering knowledge nodes from standards/ (no engine logic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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
class ValidationIssue:
    level: str  # error | warning
    message: str


@dataclass
class NodeValidationResult:
    node_id: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


class StandardsReader:
    """Load nodes and roots from the on-disk standards pack."""

    def __init__(self, standards_root: Path, *, standard: str = "asme_b31.3") -> None:
        self.pack_root = standards_root / standard
        self.nodes_dir = self.pack_root / "nodes"
        self.roots_dir = self.pack_root / "roots"

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

        direct = self.nodes_dir / node_id / "node.md"
        if direct.exists():
            return direct

        for path in self.nodes_dir.glob("*/node.md"):
            record = self.load_file(path)
            if record.node_id == node_id:
                return path

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
        for formula in record.metadata.get("formulas", []) or []:
            if not isinstance(formula, dict):
                continue
            file_name = formula.get("file")
            if file_name and not (node_dir / file_name).exists():
                issues.append(
                    ValidationIssue("error", f"Missing formula file: {file_name}")
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
