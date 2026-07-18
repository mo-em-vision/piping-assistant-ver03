"""Load and execute table option_queries for composer dropdowns and catalog search."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from engine.reference.material_resolver import resolve_material_table_key
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY, read_fact_value
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.pipe_dimensions_db import PipeDimensionsDatabase
from engine.reference.pipe_dimensions_registry import load_pipe_dimensions_registry
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_paths import resolve_standard_pack
from models.fact import Fact
from models.task import Task

_LABEL_PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_]+)(?::([^}]+))?\}")


def _standards_root_from_reader(reader: Any | None) -> Path | None:
    if reader is None:
        return None
    root = getattr(reader, "standards_root", None)
    if root is None:
        return None
    return Path(root).resolve()


def _table_yaml_candidates(table_ref: str, standards_root: Path) -> list[Path]:
    ref = str(table_ref or "").strip()
    if not ref:
        return []
    candidates: list[Path] = []
    global_materials = standards_root.parent / "global" / "materials" / "nodes"
    if ref in {"MAT-catalog", "material_catalog"}:
        candidates.append(global_materials / "MAT-catalog.yaml")
    b3610 = standards_root / "asme" / "asme_b36.10" / "tables"
    if ref in {"B3610-table-2-1", "table-2-1"}:
        candidates.append(b3610 / "B3610-table-2-1.yaml")
    b313_tables = standards_root / "asme" / "asme_b31.3" / "nodes" / "tables"
    if ref.startswith("asme-b313-table-") or ref.startswith("asme_b31.3_"):
        stem = ref.replace("asme_b31.3_", "asme-b313-table-").replace("_", "-")
        if not stem.startswith("asme-b313-table-"):
            stem = f"asme-b313-table-{ref}"
        candidates.append(b313_tables / f"{stem}.yaml")
        candidates.append(b313_tables / f"{ref}.yaml")
    astm_nodes = standards_root / "astm" / "nodes"
    astm_table_node_ids = {
        "astm_a106_material_properties": "A106",
        "astm_a105_material_properties": "A105",
        "astm_a53_material_properties": "A53",
        "astm_a312_material_properties": "A312",
    }
    node_stem = astm_table_node_ids.get(ref)
    if node_stem:
        candidates.append(astm_nodes / f"{node_stem}.yaml")
    elif ref in {"A106", "A105", "A53", "A312"}:
        candidates.append(astm_nodes / f"{ref}.yaml")
    return [path for path in candidates if path.is_file()]


def load_option_queries(table_ref: str, *, standards_root: Path) -> dict[str, Any]:
    """Return option_queries dict from table/catalog YAML for a graph table id."""
    for path in _table_yaml_candidates(table_ref, standards_root):
        if path.suffix.lower() in {".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8")
            if path.name == "MAT-catalog.yaml" or text.lstrip().startswith("---"):
                meta, _ = split_frontmatter(text)
                queries = meta.get("option_queries") or (meta.get("metadata") or {}).get(
                    "option_queries"
                )
            else:
                data = yaml.safe_load(text) or {}
                queries = data.get("option_queries") if isinstance(data, dict) else None
            if isinstance(queries, dict) and queries:
                return dict(queries)
    return {}


def load_option_query_profile(
    table_ref: str,
    query_name: str,
    *,
    standards_root: Path,
) -> dict[str, Any] | None:
    queries = load_option_queries(table_ref, standards_root=standards_root)
    profile = queries.get(str(query_name or "").strip())
    return profile if isinstance(profile, dict) else None


def _format_label(template: str, row: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        fmt = match.group(2)
        value = row.get(key)
        if value is None:
            return ""
        if fmt:
            try:
                return format(float(value), fmt)
            except (TypeError, ValueError):
                return str(value)
        return str(value)

    return _LABEL_PLACEHOLDER.sub(repl, template).strip()


def _task_facts(task: Task) -> dict[str, Fact]:
    return dict(task.fact_store.active_facts())


def _profile_requires_satisfied(
    profile: dict[str, Any],
    facts: dict[str, Fact],
) -> bool:
    requires = profile.get("requires") or []
    if not isinstance(requires, list):
        return True
    for key in requires:
        field = str(key).strip()
        if not field:
            continue
        if read_fact_value(facts, field) is None:
            return False
    return True


def _profile_has_limits(profile: dict[str, Any]) -> bool:
    requires = profile.get("requires") or []
    filters = profile.get("filter") or {}
    if isinstance(requires, list) and requires:
        return True
    return isinstance(filters, dict) and bool(filters)


def _resolve_pipe_db(standards_root: Path, table_id: str) -> tuple[PipeDimensionsDatabase, str]:
    _, sources = load_pipe_dimensions_registry(standards_root)
    for source in sources:
        if source.table_id == table_id or table_id in {source.table_id, "B3610-table-2-1"}:
            pack_root = resolve_standard_pack(standards_root, source.standard)
            db_path = pack_root / source.db_file
            return PipeDimensionsDatabase(db_path), source.table_id
    pack_root = resolve_standard_pack(standards_root, "asme_b36.10")
    return PipeDimensionsDatabase(pack_root / "pipe_dimensions.db"), table_id


def _execute_pipe_dimensions_query(
    profile: dict[str, Any],
    *,
    standards_root: Path,
    table_id: str,
    facts: dict[str, Fact],
) -> list[dict[str, Any]]:
    db, resolved_table_id = _resolve_pipe_db(standards_root, table_id)
    if not db.exists:
        return []

    value_column = str(profile.get("value_column") or "nps")
    label_template = str(profile.get("label_template") or "{value}")
    order_by = str(profile.get("order_by") or "outside_diameter_mm")
    filters = profile.get("filter") if isinstance(profile.get("filter"), dict) else {}

    if value_column == "schedule":
        if filters:
            fact_key = str(next(iter(filters.keys())))
        else:
            fact_key = "nominal_pipe_size"
        nps = read_fact_value(facts, fact_key)
        if nps is None:
            return []
        try:
            entries = db.list_schedules_for_nps(resolved_table_id, str(nps))
        except (FileNotFoundError, ValueError):
            return []
        rows: list[dict[str, Any]] = []
        for entry in entries:
            row = {
                "schedule": entry.schedule,
                "value": entry.schedule,
                "wall_thickness_in": entry.wall_thickness_in,
                "wall_thickness_mm": entry.wall_thickness_mm,
            }
            rows.append(
                {
                    "value": str(row["value"]),
                    "label": _format_label(label_template, row),
                }
            )
        return rows

    if value_column == "nps":
        nps_list = db.list_nps_sizes(resolved_table_id)
        return [
            {
                "value": nps,
                "label": _format_label(label_template, {"value": nps, "nps": nps}),
            }
            for nps in nps_list
        ]

    if value_column in {"outside_diameter_mm", "outside_diameter_in"}:
        nps_list = db.list_nps_sizes(resolved_table_id)
        by_mm: dict[float, dict[str, Any]] = {}
        for nps in nps_list:
            try:
                row = db.lookup(resolved_table_id, nps)
            except ValueError:
                continue
            od_mm = round(float(row.outside_diameter_mm), 4)
            if od_mm not in by_mm:
                by_mm[od_mm] = {
                    "outside_diameter_mm": row.outside_diameter_mm,
                    "outside_diameter_in": row.outside_diameter_in,
                    "value": str(od_mm),
                }
        ordered = sorted(by_mm.values(), key=lambda item: float(item["outside_diameter_mm"]))
        return [
            {
                "value": str(item["value"]),
                "label": _format_label(label_template, item),
            }
            for item in ordered
        ]

    return []


def _execute_standards_tables_query(
    profile: dict[str, Any],
    *,
    standards_root: Path,
    table_ref: str,
    facts: dict[str, Fact],
) -> list[dict[str, Any]]:
    from engine.reference.material_catalog_db import standards_root_from_pack_root
    from engine.reference.pack_tables_db import resolve_pack_tables_db
    from engine.reference.standards_tables import StandardsTablesDatabase

    pack_root = resolve_standard_pack(standards_root, "asme_b31.3")
    tables_db = StandardsTablesDatabase(resolve_pack_tables_db(pack_root))
    table_data = tables_db.get_table(table_ref)
    if table_data is None:
        table_data = tables_db.get_table(str(profile.get("table_id") or table_ref))
    if table_data is None:
        return []

    value_column = str(profile.get("value_column") or "joint_category")
    label_template = str(profile.get("label_template") or "{value}")
    rows = table_data.get("rows") or []
    filters = profile.get("filter") if isinstance(profile.get("filter"), dict) else {}

    material_key: str | None = None
    if filters:
        fact_key = str(next(iter(filters.keys())) or MATERIAL_GRADE_KEY)
        material = read_fact_value(facts, fact_key)
        if material is None:
            return []
        material_keys = {
            str(row.get("material_id") or row.get("material") or ""): row for row in rows
        }
        material_key = resolve_material_table_key(
            material_keys,
            str(material),
            standards_root=standards_root_from_pack_root(pack_root),
        )
        if material_key is None:
            return []

    seen: set[str] = set()
    options: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if material_key is not None:
            token = str(row.get("material_id") or row.get("material") or "")
            if token != material_key:
                continue
        label = str(row.get(value_column) or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        item = dict(row)
        item["value"] = label
        options.append({"value": label, "label": _format_label(label_template, item)})

    if profile.get("distinct") and options:
        options = sorted(options, key=lambda item: item["label"].lower())
    return options


def _execute_material_catalog_search(
    profile: dict[str, Any],
    *,
    standards_root: Path,
    search_text: str,
    limit: int,
) -> list[dict[str, Any]]:
    from engine.reference.material_catalog_db import GlobalMaterialCatalog

    min_len = int(profile.get("min_query_length") or 3)
    needle = str(search_text or "").strip()
    if len(needle) < min_len:
        return []

    catalog = GlobalMaterialCatalog(standards_root)
    if not catalog.exists:
        return []

    rows = catalog.search(needle, limit=limit)
    value_column = str(profile.get("value_column") or "material_id")
    label_column = str(profile.get("label_column") or "label")
    options: list[dict[str, Any]] = []
    for row in rows:
        options.append(
            {
                "value": str(row.get(value_column) or row.get("value") or ""),
                "label": str(row.get(label_column) or row.get("label") or ""),
                **{k: v for k, v in row.items() if k not in {"value", "label"}},
            }
        )
    return options


def execute_option_query(
    profile: dict[str, Any],
    *,
    standards_root: Path,
    table_ref: str,
    facts: dict[str, Fact] | None = None,
    search_text: str = "",
    limit: int = 12,
) -> list[dict[str, str]]:
    """Run one compiled option_query profile and return UI option dicts."""
    if str(profile.get("mode") or "") == "search":
        return _execute_material_catalog_search(
            profile,
            standards_root=standards_root,
            search_text=search_text,
            limit=limit,
        )

    if _profile_has_limits(profile) and not _profile_requires_satisfied(profile, facts or {}):
        return []

    storage = str(profile.get("storage") or "")
    task_facts = facts or {}
    table_id = str(profile.get("table_id") or table_ref)

    if storage == "pipe_dimensions":
        return _execute_pipe_dimensions_query(
            profile,
            standards_root=standards_root,
            table_id=table_id,
            facts=task_facts,
        )
    if storage == "standards_tables":
        return _execute_standards_tables_query(
            profile,
            standards_root=standards_root,
            table_ref=table_ref,
            facts=task_facts,
        )
    if storage == "material_catalog":
        return _execute_material_catalog_search(
            profile,
            standards_root=standards_root,
            search_text=search_text,
            limit=limit,
        )
    return []


def resolve_table_dropdown_options(
    task: Task,
    parameter_id: str,
    *,
    standards_root: Path,
    param_metadata: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Return dropdown options for a PARAM with metadata.table_options."""
    from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input

    meta = param_metadata
    if meta is None:
        node_id = param_node_id_for_input(parameter_id)
        if node_id:
            meta = load_parameter_node_metadata(node_id)
    if meta is None:
        return []
    meta = prepare_parameter_metadata(meta)

    table_options = meta.get("table_options")
    if not isinstance(table_options, dict):
        return []

    table_ref = str(table_options.get("table") or "").strip()
    query_name = str(table_options.get("query") or "").strip()
    if not table_ref or not query_name:
        return []

    profile = load_option_query_profile(table_ref, query_name, standards_root=standards_root)
    if profile is None:
        return []

    if str(profile.get("mode") or "") == "search":
        return []

    return execute_option_query(
        profile,
        standards_root=standards_root,
        table_ref=table_ref,
        facts=_task_facts(task),
    )


def resolve_table_search_options(
    *,
    standards_root: Path,
    table_ref: str = "MAT-catalog",
    query_name: str = "material_search",
    search_text: str,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return typeahead material (or other search-mode) options."""
    profile = load_option_query_profile(table_ref, query_name, standards_root=standards_root)
    if profile is None:
        return []
    return execute_option_query(
        profile,
        standards_root=standards_root,
        table_ref=table_ref,
        search_text=search_text,
        limit=limit,
    )


def validate_param_table_options_metadata(meta: dict[str, Any]) -> list[str]:
    """Return validation issues when static and table options conflict."""
    prepared = prepare_parameter_metadata(meta)
    has_static = bool(prepared.get("composer_options"))
    table_options = prepared.get("table_options")
    has_table = isinstance(table_options, dict) and bool(table_options.get("query"))
    issues: list[str] = []
    if has_static and has_table:
        issues.append("PARAM must not declare both composer_options and table_options")
    return issues
