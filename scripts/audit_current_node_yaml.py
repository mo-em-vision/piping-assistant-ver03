#!/usr/bin/env python3
"""Audit authored knowledge/workflow YAML against existing validators and loader checks.

Does NOT parse Markdown contracts. Enforcement: validators + shared generic checks only.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from engine.reference.graph_compile import validate_edge_item
from engine.reference.node_sources import _SIDECAR_FILENAMES, iter_node_source_paths
from engine.reference.node_types import CANONICAL_NODE_TYPES, normalize_node_metadata
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.authority_node_validator import validate_authority_node
from engine.validation.equation_node_validator import validate_equation_node
from engine.validation.lookup_node_validator import validate_lookup_node
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.validation.parameter_node_validator import validate_parameter_node
from engine.validation.paragraph_node_validator import validate_paragraph_node
from engine.validation.unit_node_validator import validate_unit_node
from engine.validation.validation_rule_node_validator import validate_validation_rule_node
from engine.validation.workflow_node_validator import validate_workflow_node

from engine.reference.paragraph_authoring_policy import (
    EXECUTION_SIDECAR_KEYS,
    check_paragraph_frontmatter_migration,
    check_paragraph_sidecar_surface,
    classify_edge_target,
)
from engine.reference.equation_sidecar import _EXECUTION_KEYS as EQUATION_EXEC_KEYS
from engine.reference.workflow_sidecar import _RUNTIME_KEYS as WORKFLOW_RUNTIME_KEYS

REPORT_PATH = PROJECT_ROOT / "audits" / "reports" / "nodes" / "current-node-yaml-audit.md"
PARAGRAPH_REPORT_PATH = PROJECT_ROOT / "audits" / "reports" / "nodes" / "paragraph-node-audit.md"

NODE_DISCOVERY_ROOTS = [
    PROJECT_ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes",
    PROJECT_ROOT / "knowledge" / "standards" / "astm" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "parameters" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "units" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "dimensions" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "concepts" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "authorities" / "nodes",
    PROJECT_ROOT / "knowledge" / "global" / "materials" / "nodes",
]

PACK_CATALOG_PATHS = [
    PROJECT_ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "pack.yaml",
    PROJECT_ROOT / "knowledge" / "global" / "materials" / "registry.yaml",
    PROJECT_ROOT / "knowledge" / "global" / "materials" / "supplemental.yaml",
    PROJECT_ROOT / "knowledge" / "global" / "dimensions" / "registry.yaml",
    PROJECT_ROOT / "knowledge" / "standards" / "asme" / "asme_b36.10" / "tables" / "B3610-table-2-1.yaml",
]

RUNTIME_FIELD_BANS = frozenset(
    {
        "value",
        "user_input",
        "runtime_unit",
        "runtime_units",
        "runtime_value",
        "fact_value",
        "execution_id",
        "task_id",
        "calculation_result",
    }
)

_CONCEPT_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material",
        "fluid",
        "component",
        "condition",
        "coefficient",
        "factor",
        "selection",
        "failure_mode",
        "inspection_method",
        "authority_concept",
    }
)


@dataclass
class AuditFinding:
    severity: str
    code: str = ""
    message: str = ""
    key: str = ""


@dataclass
class AuditRow:
    rel_path: str
    node_id: str = ""
    canonical_type: str = ""
    validator: str = ""
    contract: str = ""
    parent: str = ""
    role: str = ""
    result: str = "PASS"
    problems: list[str] = field(default_factory=list)
    findings: list[AuditFinding] = field(default_factory=list)

    def add(self, level: str, msg: str, *, code: str = "", key: str = "") -> None:
        self.problems.append(msg)
        self.findings.append(
            AuditFinding(severity=level, code=code, message=msg, key=key)
        )
        if level == "FAIL":
            self.result = "FAIL"
        elif level == "WARN" and self.result != "FAIL":
            self.result = "WARN"


def _repo_rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_meta(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    if isinstance(meta, dict) and meta:
        return meta, body
    loaded = yaml.safe_load(text)
    if isinstance(loaded, dict):
        return loaded, ""
    return {}, text


def _is_flat_execution_sidecar(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".execution.yaml") or name.endswith(".execution.yml")


def _is_sidecar_path(path: Path) -> bool:
    if path.name.lower() in _SIDECAR_FILENAMES:
        return True
    if _is_flat_execution_sidecar(path):
        return True
    if path.name.lower().endswith(".nomenclature.yaml"):
        return True
    return False


def _discover_section_a() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for nodes_dir in NODE_DISCOVERY_ROOTS:
        if not nodes_dir.is_dir():
            continue
        for path in iter_node_source_paths(nodes_dir):
            if path in seen:
                continue
            if _is_sidecar_path(path):
                continue
            seen.add(path)
            paths.append(path)
    for wf in sorted((PROJECT_ROOT / "workflows").glob("*.yaml")):
        meta, _ = _load_meta(wf)
        if str(meta.get("type") or "") == "workflow":
            paths.append(wf)
    return sorted(paths, key=_repo_rel)


def _discover_section_b() -> list[Path]:
    paths: list[Path] = []
    nodes_roots = [
        PROJECT_ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes",
    ]
    for root in nodes_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if lower in _SIDECAR_FILENAMES or _is_flat_execution_sidecar(path):
                paths.append(path)
    return sorted(set(paths), key=_repo_rel)


def _discover_section_c() -> list[Path]:
    paths: list[Path] = []
    workflows = PROJECT_ROOT / "workflows"
    if workflows.is_dir():
        for path in sorted(workflows.rglob("runtime.yaml")):
            paths.append(path)
        for path in sorted(workflows.rglob("navigation.yaml")):
            paths.append(path)
    return paths


def _discover_section_d() -> list[Path]:
    return [p for p in PACK_CATALOG_PATHS if p.is_file()]


def _build_node_index(section_a_paths: list[Path]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in section_a_paths:
        try:
            meta, _ = _load_meta(path)
        except Exception:
            continue
        node_id = str(meta.get("id") or path.stem).strip()
        if node_id:
            index[node_id] = meta
    return index


def _build_repo_wide_node_index(section_a_paths: list[Path]) -> set[str]:
    return set(_build_node_index(section_a_paths).keys())


def _load_paragraph_execution_sidecar(paragraph_path: Path, node_id: str) -> dict[str, Any]:
    flat = paragraph_path.parent / f"{node_id}.execution.yaml"
    nested = paragraph_path.parent / node_id / "execution.yaml"
    for path in (flat, nested):
        if path.is_file():
            data, _ = _load_meta(path)
            return data if isinstance(data, dict) else {}
    return {}


def _paragraph_placement_checks(
    meta: dict[str, Any],
    path: Path,
    row: AuditRow,
) -> None:
    node_id = str(meta.get("id") or path.stem)
    for level, msg in check_paragraph_frontmatter_migration(meta, node_id=node_id):
        row.add(level, msg, code="paragraph_frontmatter_migration")

    sidecar_data = _load_paragraph_execution_sidecar(path, node_id)
    if sidecar_data:
        for level, msg in check_paragraph_sidecar_surface(
            meta, sidecar_data, node_id=node_id
        ):
            row.add(level, msg, code="paragraph_sidecar_surface")


def _validator_for_type(node_type: str) -> tuple[str, Callable[[dict[str, Any]], list[str]] | None]:
    mapping: dict[str, tuple[str, Callable[[dict[str, Any]], list[str]] | None]] = {
        "paragraph": ("validate_paragraph_node", validate_paragraph_node),
        "parameter": ("validate_parameter_node", validate_parameter_node),
        "equation": ("validate_equation_node", validate_equation_node),
        "lookup": ("validate_lookup_node", validate_lookup_node),
        "validation_rule": ("validate_validation_rule_node", validate_validation_rule_node),
        "workflow": ("validate_workflow_node", validate_workflow_node),
        "unit": ("validate_unit_node", validate_unit_node),
        "authority": ("validate_authority_node", validate_authority_node),
    }
    return mapping.get(node_type, ("none", None))


def _generic_node_checks(
    meta: dict[str, Any],
    path: Path,
    repo_index: set[str],
) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    node_id = str(meta.get("id") or path.stem).strip()
    if not node_id:
        issues.append(("FAIL", "missing node id"))
    stem = path.stem
    if stem and node_id and stem != node_id and not path.name.startswith("asme-b313-"):
        if path.suffix.lower() in {".yaml", ".yml"} and path.parent.name in {
            "paragraph",
            "parameters",
            "nodes",
        } or "PARAM-" in node_id or node_id.replace(".", "-") == stem:
            pass
        elif node_id.startswith(("PARAM-", "UNIT-", "DIM-", "CONCEPT-", "AUTH-", "WF-")) and stem != node_id:
            issues.append(("WARN", f"filename stem {stem!r} differs from id {node_id!r}"))
    for field in RUNTIME_FIELD_BANS:
        if field in meta:
            issues.append(("FAIL", f"forbidden runtime field: {field}"))
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            target = str(item.get("target") or "").strip()
            edge_type = str(item.get("type") or "").strip()
            edge_issues = validate_edge_item(
                item, source_node_type=str(meta.get("type") or ""), allow_legacy=False
            )
            for msg in edge_issues:
                issues.append(("FAIL", msg))
            for level, msg in classify_edge_target(
                target, edge_type, repo_index=repo_index
            ):
                issues.append((level, msg))
    return issues


def _audit_concept(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "concept":
        issues.append("type must be 'concept'")
    if not str(meta.get("id") or "").startswith("CONCEPT-"):
        issues.append("id must start with CONCEPT-")
    cc = str(meta.get("concept_class") or "")
    if cc and cc not in _CONCEPT_CLASSES:
        issues.append(f"unknown concept_class: {cc}")
    for key in ("key", "name", "description"):
        if not meta.get(key):
            issues.append(f"missing {key}")
    issues.extend(validate_revision_metadata(meta))
    return issues


def _audit_dimension(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "dimension":
        issues.append("type must be 'dimension'")
    if not str(meta.get("id") or "").startswith("DIM-"):
        issues.append("id must start with DIM-")
    for key in ("key", "name", "dimension_kind", "description"):
        if not meta.get(key):
            issues.append(f"missing {key}")
    issues.extend(validate_revision_metadata(meta))
    return issues


def _audit_section_a(paths: list[Path], repo_index: set[str]) -> list[AuditRow]:
    node_index = _build_node_index(paths)
    unit_nodes = {k: v for k, v in node_index.items() if str(v.get("type")) == "unit"}
    rows: list[AuditRow] = []
    concept_ids: dict[str, str] = {}

    for path in paths:
        rel = _repo_rel(path)
        row = AuditRow(rel_path=rel)
        try:
            meta, _ = _load_meta(path)
        except Exception as exc:
            row.add("FAIL", f"YAML parse error: {exc}")
            rows.append(row)
            continue

        raw_type = str(meta.get("type") or "unknown")
        canonical, normalized = normalize_node_metadata(meta, raw_type)
        row.node_id = str(meta.get("id") or path.stem)
        row.canonical_type = canonical

        if raw_type == "material_catalog":
            row.validator = "none"
            row.add("WARN", "non-canonical type material_catalog")
        elif canonical not in CANONICAL_NODE_TYPES and raw_type not in CANONICAL_NODE_TYPES:
            row.add("WARN", f"type {raw_type!r} not in CANONICAL_NODE_TYPES")

        val_name, validator = _validator_for_type(canonical)
        row.validator = val_name

        if validator:
            validate_input = meta if canonical == "paragraph" else normalized
            if canonical == "unit":
                for msg in validator(validate_input, known_nodes=unit_nodes):
                    row.add("FAIL", msg)
            else:
                for msg in validator(validate_input):
                    row.add("FAIL", msg)
        elif canonical == "concept":
            row.validator = "ontology_concept_checks"
            for msg in _audit_concept(normalized):
                row.add("FAIL", msg)
        elif canonical == "dimension":
            row.validator = "ontology_dimension_checks"
            for msg in _audit_dimension(normalized):
                row.add("FAIL", msg)
        elif canonical in {"text", "quantity", "designation", "table"}:
            row.validator = "revision_only"
            row.add("WARN", f"no dedicated validator for type {canonical}")
            for msg in validate_revision_metadata(normalized):
                row.add("FAIL", msg)
        else:
            row.add("WARN", "no validator mapped")

        if canonical == "paragraph":
            _paragraph_placement_checks(meta, path, row)

        for level, msg in _generic_node_checks(normalized, path, repo_index):
            row.add(level, msg)

        if canonical == "concept":
            cid = row.node_id
            if cid in concept_ids:
                row.add("FAIL", f"duplicate concept id: {cid}")
            concept_ids[cid] = rel

        rows.append(row)
    return rows


def _sidecar_contract(path: Path) -> str:
    lower = path.name.lower()
    parent = path.parent.name
    if "nomenclature" in lower:
        return "paragraph-nomenclature.md"
    if lower == "execution.yaml" or lower.endswith(".execution.yaml"):
        if parent == "validation_rule" or "valrule" in str(path):
            return "equation-execution.md"
        return "paragraph-execution.md"
    return "paragraph-execution.md"


def _parent_node_id(path: Path) -> str:
    if path.name.lower() == "execution.yaml":
        return path.parent.name
    if _is_flat_execution_sidecar(path):
        return path.name.replace(".execution.yaml", "").replace(".execution.yml", "")
    return ""


def _audit_section_b(paths: list[Path], node_index: dict[str, dict[str, Any]]) -> list[AuditRow]:
    rows: list[AuditRow] = []
    allowed_para = set(EXECUTION_SIDECAR_KEYS)
    allowed_eq = set(EQUATION_EXEC_KEYS)

    for path in paths:
        rel = _repo_rel(path)
        contract = _sidecar_contract(path)
        row = AuditRow(rel_path=rel, contract=contract, validator="sidecar_loader_keys")
        parent_id = _parent_node_id(path)
        row.parent = parent_id
        if contract.startswith("paragraph"):
            row.role = "paragraph-sidecar"

        try:
            data, _ = _load_meta(path)
        except Exception as exc:
            row.add("FAIL", f"YAML parse error: {exc}")
            rows.append(row)
            continue

        if not data:
            row.add("WARN", "empty sidecar document")

        if parent_id and parent_id not in node_index:
            row.add("WARN", f"parent node {parent_id!r} not found in section A index")

        if "nomenclature" in path.name.lower():
            if "nomenclature" not in data:
                row.add("WARN", "expected nomenclature key")
        elif contract == "equation-execution.md":
            unknown = set(data.keys()) - allowed_eq - {"metadata"}
            if unknown:
                row.add("WARN", f"unrecognized keys for equation sidecar: {sorted(unknown)}")
        else:
            unknown = set(data.keys()) - allowed_para - {"metadata"}
            if unknown:
                row.add("WARN", f"unrecognized keys for paragraph sidecar: {sorted(unknown)}")

        for field in RUNTIME_FIELD_BANS:
            if field in data and field not in {"value"}:
                pass  # sidecars may use different semantics

        rows.append(row)
    return rows


def _audit_section_c(paths: list[Path], workflow_index: dict[str, dict[str, Any]]) -> list[AuditRow]:
    allowed = set(WORKFLOW_RUNTIME_KEYS)
    rows: list[AuditRow] = []
    for path in paths:
        rel = _repo_rel(path)
        row = AuditRow(rel_path=rel, contract="workflow-runtime.md", validator="workflow_sidecar_loader_keys")
        wf_dir = path.parent.name
        row.parent = wf_dir
        if wf_dir not in workflow_index and wf_dir.replace("-", "_") not in workflow_index:
            row.add("WARN", f"parent workflow folder {wf_dir!r} not matched to section A workflow id")

        try:
            data, _ = _load_meta(path)
        except Exception as exc:
            row.add("FAIL", f"YAML parse error: {exc}")
            rows.append(row)
            continue

        if not data:
            row.add("WARN", "empty workflow config")

        if path.name.lower().startswith("navigation"):
            if "navigation" not in data and "phases" not in data:
                row.add("WARN", "navigation sidecar missing navigation or phases")
        else:
            unknown = set(data.keys()) - allowed
            if unknown:
                row.add("WARN", f"unrecognized workflow runtime keys: {sorted(unknown)}")

        rows.append(row)
    return rows


def _audit_section_d(paths: list[Path]) -> list[AuditRow]:
    rows: list[AuditRow] = []
    for path in paths:
        rel = _repo_rel(path)
        row = AuditRow(rel_path=rel, contract="pack-metadata.md", validator="pack_metadata_loader")
        if "pack.yaml" in path.name:
            row.role = "pack metadata"
            try:
                meta, _ = _load_meta(path)
            except Exception as exc:
                row.add("FAIL", f"YAML parse error: {exc}")
            else:
                if not meta.get("id") and not meta.get("title"):
                    row.add("WARN", "pack.yaml missing id or title")
        elif "registry.yaml" in path.name:
            row.role = "catalog registry"
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                row.add("FAIL", f"YAML parse error: {exc}")
            else:
                if not isinstance(data, dict):
                    row.add("FAIL", "registry must be a mapping")
        elif "supplemental.yaml" in path.name:
            row.role = "supplemental catalog"
        elif "B3610-table" in path.name:
            row.role = "raw table data"
            row.add("WARN", "raw table data without node frontmatter")
        rows.append(row)
    return rows


def _overall_status(rows: list[AuditRow]) -> str:
    if any(r.result == "FAIL" for r in rows):
        return "FAIL"
    if any(r.result == "WARN" for r in rows):
        return "WARN"
    return "PASS"


def _type_counts(section_a: list[AuditRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in section_a:
        counts[row.canonical_type] = counts.get(row.canonical_type, 0) + 1
    return dict(sorted(counts.items()))


def render_report(
    section_a: list[AuditRow],
    section_b: list[AuditRow],
    section_c: list[AuditRow],
    section_d: list[AuditRow],
) -> str:
    all_rows = section_a + section_b + section_c + section_d
    overall = _overall_status(all_rows)
    pass_n = sum(1 for r in all_rows if r.result == "PASS")
    warn_n = sum(1 for r in all_rows if r.result == "WARN")
    fail_n = sum(1 for r in all_rows if r.result == "FAIL")

    lines: list[str] = [
        "# Current Node YAML Audit",
        "",
        f"**Overall status:** {overall}",
        "",
        "## Summary",
        "",
        f"- Total files inspected: {len(all_rows)}",
        f"- Passing: {pass_n}",
        f"- Warnings: {warn_n}",
        f"- Failing: {fail_n}",
        "",
        "### Section totals",
        "",
        f"- A. Node YAML: {len(section_a)} files ({_overall_status(section_a)})",
        f"- B. Node sidecar YAML: {len(section_b)} files ({_overall_status(section_b)})",
        f"- C. Workflow configuration YAML: {len(section_c)} files ({_overall_status(section_c)})",
        f"- D. Pack/catalog YAML: {len(section_d)} files ({_overall_status(section_d)})",
        "",
        "### Node counts by canonical type (Section A)",
        "",
    ]
    for t, n in _type_counts(section_a).items():
        lines.append(f"- `{t}`: {n}")
    lines.extend(["", "---", "", "## A. Node YAML inventory", ""])
    lines.append("| YAML file | Node ID | Canonical type | Validator | Result | Problems |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in section_a:
        prob = "; ".join(row.problems) if row.problems else "—"
        lines.append(
            f"| `{row.rel_path}` | `{row.node_id}` | `{row.canonical_type}` | `{row.validator}` | **{row.result}** | {prob} |"
        )

    lines.extend(["", "## B. Node sidecar YAML inventory", ""])
    lines.append("| YAML file | Parent node | Contract | Result | Problems |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in section_b:
        prob = "; ".join(row.problems) if row.problems else "—"
        lines.append(
            f"| `{row.rel_path}` | `{row.parent}` | `{row.contract}` | **{row.result}** | {prob} |"
        )

    lines.extend(["", "## C. Workflow configuration YAML inventory", ""])
    lines.append("| YAML file | Parent workflow | Contract | Result | Problems |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in section_c:
        prob = "; ".join(row.problems) if row.problems else "—"
        lines.append(
            f"| `{row.rel_path}` | `{row.parent}` | `{row.contract}` | **{row.result}** | {prob} |"
        )

    lines.extend(["", "## D. Pack/catalog YAML inventory", ""])
    lines.append("| YAML file | Role | Contract | Result | Problems |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in section_d:
        prob = "; ".join(row.problems) if row.problems else "—"
        lines.append(
            f"| `{row.rel_path}` | {row.role} | `{row.contract}` | **{row.result}** | {prob} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Implementation inconsistencies affecting YAML authoring",
            "",
            "- Production table nodes use `type: lookup`, not `table`.",
            "- `material_catalog` (`MAT-catalog.yaml`) is not in `CANONICAL_NODE_TYPES`.",
            "- Flat `{id}.execution.yaml` files are loaded as sidecars but may also match node discovery if given frontmatter.",
            "- Paragraph field placement policy: `engine/reference/paragraph_authoring_policy.py`.",
            "- Paragraph frontmatter validators forbid fields that paragraph execution sidecars merge at compile time.",
            "- Types `text`, `quantity`, `designation`, `table` have no dedicated validators — audit uses revision + generic checks only.",
            "- Human-readable contract documents are not parsed by this audit script; validators remain enforcement authority.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _is_paragraph_row(row: AuditRow) -> bool:
    if row.canonical_type == "paragraph":
        return True
    if row.role == "paragraph-sidecar":
        return True
    if "/nodes/paragraph/" in row.rel_path and row.contract.startswith("paragraph"):
        return True
    return False


def _filter_rows_by_pack(rows: list[AuditRow], pack: str) -> list[AuditRow]:
    if not pack:
        return rows
    slug = pack.replace(".", "_").replace("-", "_")
    return [
        r
        for r in rows
        if pack in r.rel_path or slug in r.rel_path.replace("-", "_").replace(".", "_")
    ]


def render_paragraph_report(rows: list[AuditRow]) -> str:
    overall = _overall_status(rows)
    pass_n = sum(1 for r in rows if r.result == "PASS")
    warn_n = sum(1 for r in rows if r.result == "WARN")
    fail_n = sum(1 for r in rows if r.result == "FAIL")
    info_n = sum(
        1 for r in rows for f in r.findings if f.severity == "INFO"
    )

    lines: list[str] = [
        "# Paragraph Node YAML Audit",
        "",
        f"**Overall status:** {overall}",
        "",
        "_Filtered projection of the full node YAML audit — same findings, paragraph scope only._",
        "",
        "## Summary",
        "",
        f"- Paragraph files inspected: {len(rows)}",
        f"- Passing: {pass_n}",
        f"- Warnings: {warn_n}",
        f"- Failing: {fail_n}",
        f"- Informational findings: {info_n}",
        "",
        "## Enforcement policy",
        "",
        "- Phase 1: `SIDECAR_ONLY_KEYS` in frontmatter → WARN (migration required).",
        "- `FORBIDDEN_PARAGRAPH_FRONTMATTER` keys (e.g. `applicability`) → FAIL immediately.",
        "- Registered external/unmodeled `related_to` targets → INFO.",
        "- Policy module: `engine/reference/paragraph_authoring_policy.py`.",
        "",
        "---",
        "",
        "## Paragraph frontmatter inventory",
        "",
        "| YAML file | Node ID | Validator | Result | Problems |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row.canonical_type == "paragraph":
            prob = "; ".join(row.problems) if row.problems else "—"
            lines.append(
                f"| `{row.rel_path}` | `{row.node_id}` | `{row.validator}` | **{row.result}** | {prob} |"
            )

    sidecar_rows = [r for r in rows if r.role == "paragraph-sidecar"]
    if sidecar_rows:
        lines.extend(
            [
                "",
                "## Paragraph sidecar inventory",
                "",
                "| YAML file | Parent node | Contract | Result | Problems |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in sidecar_rows:
            prob = "; ".join(row.problems) if row.problems else "—"
            lines.append(
                f"| `{row.rel_path}` | `{row.parent}` | `{row.contract}` | **{row.result}** | {prob} |"
            )

    return "\n".join(lines) + "\n"


def run_audit() -> tuple[list[AuditRow], list[AuditRow], list[AuditRow], list[AuditRow]]:
    section_a_paths = _discover_section_a()
    section_b_paths = _discover_section_b()
    section_c_paths = _discover_section_c()
    section_d_paths = _discover_section_d()

    repo_index = _build_repo_wide_node_index(section_a_paths)
    node_index = _build_node_index(section_a_paths)
    wf_index = {k: v for k, v in node_index.items() if str(v.get("type")) == "workflow"}

    section_a = _audit_section_a(section_a_paths, repo_index)
    section_b = _audit_section_b(section_b_paths, node_index)
    section_c = _audit_section_c(section_c_paths, wf_index)
    section_d = _audit_section_d(section_d_paths)
    return section_a, section_b, section_c, section_d


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit knowledge/workflow YAML files.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPORT_PATH,
        help="Full audit report output path",
    )
    parser.add_argument(
        "--paragraph-report",
        type=Path,
        default=PARAGRAPH_REPORT_PATH,
        help="Paragraph-filtered audit report output path",
    )
    parser.add_argument(
        "--filter",
        choices=("all", "paragraph"),
        default="all",
        help="When 'paragraph', also write paragraph projection (audit runs once)",
    )
    parser.add_argument(
        "--pack",
        default="",
        help="Optional pack slug filter for paragraph projection (e.g. asme_b31.3)",
    )
    args = parser.parse_args()

    section_a, section_b, section_c, section_d = run_audit()
    all_rows = section_a + section_b + section_c + section_d

    report = render_report(section_a, section_b, section_c, section_d)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output} ({len(all_rows)} files)")

    para_rows = [r for r in section_a + section_b if _is_paragraph_row(r)]
    para_rows = _filter_rows_by_pack(para_rows, args.pack)
    para_report = render_paragraph_report(para_rows)
    args.paragraph_report.parent.mkdir(parents=True, exist_ok=True)
    args.paragraph_report.write_text(para_report, encoding="utf-8")
    print(f"Wrote {args.paragraph_report} ({len(para_rows)} paragraph files)")

    return 0 if _overall_status(all_rows) != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
