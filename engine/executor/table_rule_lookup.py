"""Load and execute v2 lookup_rules from standards YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.lookup_rule_schema import (
    B3610_TABLE_REF,
    TableRuleLookupResult,
    load_table_lookup_rules,
    normalize_rule_name,
    require_rule_spec,
)
from engine.executor.lookup_rule_strategies import execute_strategy
from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5_1,
    TABLE_304_1_1_1,
    TABLE_A_1,
    TABLE_A_2,
    TABLE_A_3,
)
from engine.reference.material_catalog_db import standards_root_from_pack_root
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_tables import StandardsTablesDatabase
from engine.validation.lookup_rule_validator import validate_lookup_rule_spec

_GRAPH_NODE_TABLE_IDS: dict[str, str] = {
    "asme-b313-table-A-1": TABLE_A_1,
    "asme-b313-table-A-2": TABLE_A_2,
    "asme-b313-table-A-3": TABLE_A_3,
    "asme-b313-table-304-1-1-1": TABLE_304_1_1_1,
    "asme-b313-table-302-3-5-1": TABLE_302_3_5_1,
}

_PIPE_TABLE_REFS = frozenset(
    {
        B3610_TABLE_REF,
        "table-2-1",
        "asme_b36.10",
        "asme_b36.10m",
    }
)


def _resolve_pack_table_ref(pack_root: Path, table_ref: str) -> str:
    wanted = str(table_ref or "").strip()
    if not wanted:
        return wanted
    db = StandardsTablesDatabase(resolve_pack_tables_db(pack_root))
    resolved = db.resolve_table_id(wanted)
    if resolved:
        return resolved
    return _GRAPH_NODE_TABLE_IDS.get(wanted, wanted)


def _is_pipe_table(table_ref: str, spec_strategy: str) -> bool:
    if table_ref in _PIPE_TABLE_REFS:
        return True
    return spec_strategy in {"pipe_nps", "pipe_nps_schedule"}


def execute_table_rule_lookup(
    *,
    standards_pack_root: Path,
    table_ref: str,
    rule: str,
    inputs: dict[str, Any],
    returns: list[dict[str, Any]] | None = None,
) -> TableRuleLookupResult:
    """Resolve a table lookup using explicit v2 lookup_rules metadata."""
    if not str(rule or "").strip():
        raise ValueError("lookup.rule is required")

    standards_root = standards_root_from_pack_root(standards_pack_root)
    canonical_rule = normalize_rule_name(rule)
    resolved_table = table_ref.strip() or B3610_TABLE_REF

    rules = load_table_lookup_rules(resolved_table, standards_root=standards_root)
    if not rules:
        rules = load_table_lookup_rules(table_ref, standards_root=standards_root)
    spec = require_rule_spec(rules, canonical_rule)

    validation_issues = validate_lookup_rule_spec(canonical_rule, rules[canonical_rule])
    if validation_issues:
        raise ValueError("; ".join(validation_issues))

    table_data: dict[str, Any] | None = None
    if not _is_pipe_table(resolved_table, spec.strategy):
        db = StandardsTablesDatabase(resolve_pack_tables_db(standards_pack_root))
        resolved_id = _resolve_pack_table_ref(standards_pack_root, table_ref or resolved_table)
        table_data = db.get_table(resolved_id)
        if table_data is None:
            raise FileNotFoundError(f"Lookup table not found: {table_ref}")

    outputs, meta = execute_strategy(
        spec=spec,
        inputs=inputs,
        table_data=table_data,
        standards_root=standards_root,
        table_ref=table_ref or resolved_table,
        returns=returns,
    )
    meta.update(
        {
            "rule": canonical_rule,
            "strategy": spec.strategy,
            "table_ref": table_ref or resolved_table,
            "table_id": str((table_data or {}).get("table_id") or resolved_table),
        }
    )
    return TableRuleLookupResult(outputs=outputs, meta=meta)


# Backward-compatible exports for tests importing legacy helpers
def execute_pipe_dimensions_rule(
    *,
    standards_root: Path,
    rule: str,
    inputs: dict[str, Any],
    table_ref: str = B3610_TABLE_REF,
) -> TableRuleLookupResult:
    from engine.reference.standards_paths import resolve_standard_pack

    pack_root = resolve_standard_pack(standards_root, "asme_b36.10")
    return execute_table_rule_lookup(
        standards_pack_root=pack_root,
        table_ref=table_ref,
        rule=rule,
        inputs=inputs,
    )
