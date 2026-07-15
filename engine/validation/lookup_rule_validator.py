"""Validate v2 lookup_rules and lookup node bindings."""

from __future__ import annotations

from typing import Any

from engine.executor.lookup_rule_resolvers import KNOWN_RESOLVERS
from engine.executor.lookup_rule_schema import (
    INPUT_RESOLVERS,
    KNOWN_STRATEGIES,
    STRATEGY_INPUTS,
    load_table_lookup_rules,
    parse_rule_spec,
)
from engine.reference.standards_paths import resolve_standard_pack


def validate_lookup_rule_spec(rule_name: str, raw: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    try:
        spec = parse_rule_spec(rule_name, raw)
    except ValueError as exc:
        return [str(exc)]

    if spec.strategy not in KNOWN_STRATEGIES:
        issues.append(f"unknown strategy: {spec.strategy!r}")

    required_inputs = STRATEGY_INPUTS.get(spec.strategy, frozenset())
    actual_inputs = frozenset(spec.inputs.keys())
    missing = required_inputs - actual_inputs
    extra = actual_inputs - required_inputs
    if missing:
        issues.append(f"strategy {spec.strategy!r} missing inputs: {sorted(missing)}")
    if extra:
        issues.append(f"strategy {spec.strategy!r} forbids extra inputs: {sorted(extra)}")

    for logical_key, input_spec in spec.inputs.items():
        allowed = INPUT_RESOLVERS.get(logical_key, KNOWN_RESOLVERS)
        if input_spec.resolver not in allowed:
            issues.append(
                f"input {logical_key!r} resolver {input_spec.resolver!r} "
                f"not allowed (expected one of {sorted(allowed)})"
            )
        if logical_key == "design_temperature" and input_spec.match is None:
            issues.append(f"input {logical_key!r} requires match block")

    if not spec.outputs:
        issues.append("outputs block is required")

    for out_key, out_spec in spec.outputs.items():
        if not out_spec.column:
            issues.append(f"output {out_key!r} requires column")

    if spec.on_no_match != "error":
        issues.append(f"on_no_match action must be error (got {spec.on_no_match!r})")
    if spec.on_multiple_matches != "error":
        issues.append(f"on_multiple_matches action must be error (got {spec.on_multiple_matches!r})")

    return issues


def validate_lookup_bindings(rule_spec_raw: dict[str, Any], bindings: dict[str, str]) -> list[str]:
    issues: list[str] = []
    strategy = str(rule_spec_raw.get("strategy") or "").strip()
    if not strategy:
        issues.append("rule spec missing strategy for binding validation")
        return issues

    required = STRATEGY_INPUTS.get(strategy, frozenset())
    bound = frozenset(bindings.keys())
    missing = required - bound
    extra = bound - required
    if missing:
        issues.append(f"lookup.bindings missing keys: {sorted(missing)}")
    if extra:
        issues.append(f"lookup.bindings has extra keys: {sorted(extra)}")
    for key, param in bindings.items():
        if not str(param).startswith("PARAM-"):
            issues.append(f"binding {key!r} must target a PARAM-* node (got {param!r})")
    return issues


def validate_lookup_config(meta: dict[str, Any], *, standards_root: Any | None = None) -> list[str]:
    issues: list[str] = []
    lookup_cfg = meta.get("lookup")
    if not isinstance(lookup_cfg, dict):
        issues.append("lookup block is required")
        return issues

    if lookup_cfg.get("keys"):
        issues.append("lookup.keys is deprecated; use lookup.bindings")

    rule = str(lookup_cfg.get("rule") or lookup_cfg.get("lookup_rule") or "").strip()
    if not rule:
        issues.append("lookup.rule is required")

    bindings = lookup_cfg.get("bindings")
    if not isinstance(bindings, dict) or not bindings:
        issues.append("lookup.bindings is required")
        return issues

    table_ref = str(lookup_cfg.get("table") or lookup_cfg.get("table_id") or "").strip()
    if not table_ref:
        issues.append("lookup.table is required")

    if standards_root is None or not rule:
        return issues

    from pathlib import Path

    root = Path(standards_root).resolve()
    rules = load_table_lookup_rules(table_ref, standards_root=root)
    canonical = rule
    from engine.executor.lookup_rule_schema import normalize_rule_name

    canonical = normalize_rule_name(rule)
    if canonical not in rules:
        issues.append(f"lookup.rule {rule!r} not found in lookup_rules for table {table_ref!r}")
        return issues

    raw_rule = rules[canonical]
    issues.extend(validate_lookup_rule_spec(canonical, raw_rule))
    if isinstance(raw_rule, dict):
        issues.extend(validate_lookup_bindings(raw_rule, {str(k): str(v) for k, v in bindings.items()}))
    return issues
