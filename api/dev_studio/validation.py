"""Pre-save validation for dev studio node edits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from api.dev_studio.serializers import NODE_TYPE_SCHEMAS
from engine.equation.sympy_evaluator import _parse_assignment


@dataclass
class ValidationMessage:
    field: str
    message: str
    severity: str  # error | warning


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationMessage] = field(default_factory=list)
    warnings: list[ValidationMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [self._msg(item) for item in self.errors],
            "warnings": [self._msg(item) for item in self.warnings],
        }

    @staticmethod
    def _msg(item: ValidationMessage) -> dict[str, str]:
        return {"field": item.field, "message": item.message, "severity": item.severity}


def _collect_edge_targets(metadata: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    edge_keys = (
        "requires",
        "calculates",
        "defines",
        "explains",
        "outputs",
        "contains",
        "anchors_to",
        "uses_table",
        "next_step",
        "located_in",
        "depends_on",
        "edges",
    )
    for key in edge_keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            targets.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    targets.append(item.strip())
                elif isinstance(item, dict):
                    ref = str(
                        item.get("node_id") or item.get("to") or item.get("id") or ""
                    ).strip()
                    if ref:
                        targets.append(ref)
    anchors = metadata.get("anchors_to")
    if isinstance(anchors, str) and anchors.strip():
        targets.append(anchors.strip())
    goal = metadata.get("goal_output")
    if isinstance(goal, str) and goal.strip():
        targets.append(goal.strip())
    return targets


def _detect_cycle(
    node_id: str,
    metadata: dict[str, Any],
    *,
    node_exists: Callable[[str], bool],
    load_metadata: Callable[[str], dict[str, Any]],
    max_depth: int = 50,
) -> str | None:
    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(current_id: str, meta: dict[str, Any], depth: int) -> str | None:
        if depth > max_depth:
            return current_id
        if current_id in stack:
            return current_id
        if current_id in visited:
            return None
        visited.add(current_id)
        stack.add(current_id)
        for target in _collect_edge_targets(meta):
            if target == node_id and current_id == node_id:
                return target
            if not node_exists(target):
                continue
            child_meta = load_metadata(target)
            cycle = dfs(target, child_meta, depth + 1)
            if cycle:
                return cycle
        stack.remove(current_id)
        return None

    return dfs(node_id, metadata, 0)


def validate_node_payload(
    *,
    pack: str,
    metadata: dict[str, Any],
    body: str,
    node_exists: Callable[[str], bool],
    load_metadata: Callable[[str], dict[str, Any]],
    existing_id: str | None = None,
    all_ids: set[str] | None = None,
    all_titles: dict[str, str] | None = None,
) -> ValidationResult:
    result = ValidationResult(valid=True)
    node_id = str(metadata.get("id", "")).strip()
    node_type = str(metadata.get("type", "")).strip()

    if not node_id:
        result.errors.append(ValidationMessage("id", "ID is required", "error"))
    if not node_type:
        result.errors.append(ValidationMessage("type", "Type is required", "error"))

    schema = NODE_TYPE_SCHEMAS.get(node_type, {})
    for req in schema.get("required", []):
        value = metadata.get(req)
        if value is None or value == "" or value == []:
            result.errors.append(
                ValidationMessage(req, f"Required field missing: {req}", "error")
            )

    if all_ids is not None and node_id:
        if node_id in all_ids and node_id != existing_id:
            result.errors.append(
                ValidationMessage("id", f"Duplicate node ID: {node_id}", "error")
            )

    title = str(metadata.get("title") or "").strip()
    if all_titles and title:
        for other_id, other_title in all_titles.items():
            if other_id != node_id and other_title.lower() == title.lower():
                result.warnings.append(
                    ValidationMessage(
                        "title",
                        f"Duplicate title with node {other_id}",
                        "warning",
                    )
                )

    if node_type == "equation":
        sympy_expr = str(metadata.get("sympy") or "").strip()
        if sympy_expr:
            try:
                _parse_assignment(sympy_expr)
            except (ValueError, SyntaxError) as exc:
                result.errors.append(
                    ValidationMessage("sympy", f"Invalid SymPy expression: {exc}", "error")
                )

    for target in _collect_edge_targets(metadata):
        if target == node_id:
            continue
        if not node_exists(target):
            result.errors.append(
                ValidationMessage(
                    "references",
                    f"Broken reference: {target}",
                    "error",
                )
            )

    if node_id and node_type:
        cycle = _detect_cycle(
            node_id,
            metadata,
            node_exists=node_exists,
            load_metadata=load_metadata,
        )
        if cycle:
            result.errors.append(
                ValidationMessage(
                    "graph",
                    f"Circular reference detected involving {cycle}",
                    "error",
                )
            )

    unit = metadata.get("unit")
    if unit is not None and not isinstance(unit, str):
        result.warnings.append(
            ValidationMessage("unit", "Unit should be a string", "warning")
        )

    result.valid = not result.errors
    return result
