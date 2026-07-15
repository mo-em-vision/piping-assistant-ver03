"""Parse and validate v2 lookup_rules schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.table_options_resolver import _table_yaml_candidates

B3610_TABLE_REF = "B3610-table-2-1"

STRATEGY_PIPE_NPS = "pipe_nps"
STRATEGY_PIPE_NPS_SCHEDULE = "pipe_nps_schedule"
STRATEGY_MATERIAL_TEMPERATURE = "material_temperature"
STRATEGY_MATERIAL_GROUP_TEMPERATURE = "material_group_temperature"
STRATEGY_MATERIAL_CATEGORY = "material_category"
STRATEGY_MATERIAL_CATEGORY_TEMPERATURE = "material_category_temperature"
STRATEGY_MATERIAL_ONLY = "material_only"

KNOWN_STRATEGIES = frozenset(
    {
        STRATEGY_PIPE_NPS,
        STRATEGY_PIPE_NPS_SCHEDULE,
        STRATEGY_MATERIAL_TEMPERATURE,
        STRATEGY_MATERIAL_GROUP_TEMPERATURE,
        STRATEGY_MATERIAL_CATEGORY,
        STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
        STRATEGY_MATERIAL_ONLY,
    }
)

STRATEGY_INPUTS: dict[str, frozenset[str]] = {
    STRATEGY_PIPE_NPS: frozenset({"nominal_pipe_size"}),
    STRATEGY_PIPE_NPS_SCHEDULE: frozenset({"nominal_pipe_size", "pipe_schedule"}),
    STRATEGY_MATERIAL_TEMPERATURE: frozenset({"material_grade", "design_temperature"}),
    STRATEGY_MATERIAL_GROUP_TEMPERATURE: frozenset({"metallurgical_group", "design_temperature"}),
    STRATEGY_MATERIAL_CATEGORY: frozenset({"material_grade", "pipe_construction_type"}),
    STRATEGY_MATERIAL_CATEGORY_TEMPERATURE: frozenset(
        {"material_grade", "pipe_construction_type", "design_temperature"}
    ),
    STRATEGY_MATERIAL_ONLY: frozenset({"material_grade"}),
}

INPUT_RESOLVERS: dict[str, frozenset[str]] = {
    "nominal_pipe_size": frozenset({"nps_key"}),
    "pipe_schedule": frozenset({"schedule_key"}),
    "material_grade": frozenset({"material_catalog"}),
    "metallurgical_group": frozenset({"metallurgical_group_key"}),
    "pipe_construction_type": frozenset({"joint_category_normalize"}),
    "design_temperature": frozenset({"identity"}),
}

RULE_NAME_ALIASES = {
    "pipe_dimensions_nps": "by_nps",
    "pipe_dimensions_nps_schedule": "by_nps_schedule",
    "material_and_temperature": "by_material_temperature",
    "material_and_joint_category": "by_material_joint_category",
    "material_and_construction_temperature": "by_material_construction_temperature",
    "material_group_and_temperature": "by_material_group_temperature",
}

RULE_STRATEGY_BY_NAME = {
    "by_nps": STRATEGY_PIPE_NPS,
    "by_nps_schedule": STRATEGY_PIPE_NPS_SCHEDULE,
    "by_material_temperature": STRATEGY_MATERIAL_TEMPERATURE,
    "by_material_group_temperature": STRATEGY_MATERIAL_GROUP_TEMPERATURE,
    "by_material_joint_category": STRATEGY_MATERIAL_CATEGORY,
    "by_material_construction_temperature": STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
    "by_material": STRATEGY_MATERIAL_ONLY,
}


@dataclass(frozen=True)
class MatchPolicy:
    method: str
    outside_range: str
    duplicate_rows: str
    missing_value: str


@dataclass(frozen=True)
class InputSpec:
    logical_key: str
    resolver: str
    column: str | None = None
    match: MatchPolicy | None = None
    parameter: str | None = None


@dataclass(frozen=True)
class OutputSpec:
    logical_key: str
    column: str
    parameter: str | None = None


@dataclass(frozen=True)
class RuleSpec:
    name: str
    strategy: str
    inputs: dict[str, InputSpec]
    outputs: dict[str, OutputSpec]
    on_no_match: str
    on_multiple_matches: str


@dataclass(frozen=True)
class TableRuleLookupResult:
    outputs: dict[str, float]
    meta: dict[str, Any] = field(default_factory=dict)


def normalize_rule_name(rule: str) -> str:
    text = str(rule or "").strip()
    return RULE_NAME_ALIASES.get(text, text)


def _parse_table_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("---"):
        data, _ = split_frontmatter(text)
        return data if isinstance(data, dict) else {}
    data = yaml.safe_load(text) or {}
    return data if isinstance(data, dict) else {}


def load_table_lookup_rules(table_ref: str, *, standards_root: Path) -> dict[str, Any]:
    for path in _table_yaml_candidates(table_ref, standards_root):
        data = _parse_table_yaml(path)
        rules = data.get("lookup_rules")
        if isinstance(rules, dict) and rules:
            return dict(rules)
    return {}


def _parse_match_policy(raw: Any) -> MatchPolicy | None:
    if not isinstance(raw, dict):
        return None
    return MatchPolicy(
        method=str(raw.get("method") or "exact").strip(),
        outside_range=str(raw.get("outside_range") or "error").strip(),
        duplicate_rows=str(raw.get("duplicate_rows") or "error").strip(),
        missing_value=str(raw.get("missing_value") or "error").strip(),
    )


def parse_rule_spec(rule_name: str, raw: dict[str, Any]) -> RuleSpec:
    strategy = str(raw.get("strategy") or "").strip()
    if not strategy:
        strategy = RULE_STRATEGY_BY_NAME.get(normalize_rule_name(rule_name), "")

    inputs_raw = raw.get("inputs")
    if not isinstance(inputs_raw, dict) or not inputs_raw:
        raise ValueError(f"Lookup rule {rule_name!r} requires an inputs block.")

    inputs: dict[str, InputSpec] = {}
    for logical_key, item in inputs_raw.items():
        if not isinstance(item, dict):
            raise ValueError(f"Input {logical_key!r} must be a mapping.")
        resolver = str(item.get("resolver") or "").strip()
        if not resolver:
            raise ValueError(f"Input {logical_key!r} requires resolver.")
        inputs[str(logical_key)] = InputSpec(
            logical_key=str(logical_key),
            resolver=resolver,
            column=str(item.get("column") or "").strip() or None,
            match=_parse_match_policy(item.get("match")),
            parameter=str(item.get("parameter") or "").strip() or None,
        )

    outputs_raw = raw.get("outputs")
    if not isinstance(outputs_raw, dict) or not outputs_raw:
        raise ValueError(f"Lookup rule {rule_name!r} requires an outputs block.")

    outputs: dict[str, OutputSpec] = {}
    for logical_key, item in outputs_raw.items():
        if isinstance(item, str):
            outputs[str(logical_key)] = OutputSpec(
                logical_key=str(logical_key),
                column=item,
            )
            continue
        if not isinstance(item, dict):
            raise ValueError(f"Output {logical_key!r} must be a mapping or column name.")
        column = str(item.get("column") or "").strip()
        if not column:
            raise ValueError(f"Output {logical_key!r} requires column.")
        outputs[str(logical_key)] = OutputSpec(
            logical_key=str(logical_key),
            column=column,
            parameter=str(item.get("parameter") or "").strip() or None,
        )

    on_no_match = raw.get("on_no_match")
    on_multiple_matches = raw.get("on_multiple_matches")
    no_match_action = "error"
    multiple_action = "error"
    if isinstance(on_no_match, dict):
        no_match_action = str(on_no_match.get("action") or "error").strip()
    if isinstance(on_multiple_matches, dict):
        multiple_action = str(on_multiple_matches.get("action") or "error").strip()

    if not strategy:
        raise ValueError(f"Lookup rule {rule_name!r} requires strategy.")

    return RuleSpec(
        name=normalize_rule_name(rule_name),
        strategy=strategy,
        inputs=inputs,
        outputs=outputs,
        on_no_match=no_match_action,
        on_multiple_matches=multiple_action,
    )


def require_rule_spec(rules: dict[str, Any], rule: str) -> RuleSpec:
    canonical = normalize_rule_name(rule)
    raw = rules.get(canonical)
    if not isinstance(raw, dict):
        raise ValueError(f"Lookup rule {rule!r} is not defined for table.")
    return parse_rule_spec(canonical, raw)


def lookup_bindings(metadata: dict[str, Any]) -> dict[str, str]:
    lookup_cfg = metadata.get("lookup")
    if not isinstance(lookup_cfg, dict):
        return {}
    bindings = lookup_cfg.get("bindings")
    if not isinstance(bindings, dict):
        return {}
    return {str(k): str(v).strip() for k, v in bindings.items() if str(v).strip()}


def build_engine_inputs_from_bindings(
    *,
    bindings: dict[str, str],
    fact_values: dict[str, Any],
    store: Any | None = None,
) -> dict[str, Any]:
    """Map logical rule input keys to runtime values using lookup.bindings."""
    from engine.graph.lookup_parameter_resolution import _resolve_lookup_key

    engine_inputs: dict[str, Any] = {}
    for logical_key, param_ref in bindings.items():
        fact_key = _resolve_lookup_key(store, param_ref) if store is not None else param_ref
        if fact_key in fact_values:
            engine_inputs[logical_key] = fact_values[fact_key]
            if logical_key == "nominal_pipe_size" and f"{fact_key}_unit" in fact_values:
                engine_inputs["nominal_pipe_size_unit"] = fact_values[f"{fact_key}_unit"]
            elif logical_key == "design_temperature" and f"{fact_key}_unit" in fact_values:
                engine_inputs["design_temperature_unit"] = fact_values[f"{fact_key}_unit"]
        elif param_ref in fact_values:
            engine_inputs[logical_key] = fact_values[param_ref]
    return engine_inputs
