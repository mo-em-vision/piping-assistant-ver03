"""Parse and validate v2 lookup_rules schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.executor.table_resolver import OutputColumnPolicy, RowResolutionPolicy
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
STRATEGY_EXAMINATION_COMBINATION = "examination_combination"
STRATEGY_MATERIAL_CATALOG = "material_catalog"

KNOWN_STRATEGIES = frozenset(
    {
        STRATEGY_PIPE_NPS,
        STRATEGY_PIPE_NPS_SCHEDULE,
        STRATEGY_MATERIAL_TEMPERATURE,
        STRATEGY_MATERIAL_GROUP_TEMPERATURE,
        STRATEGY_MATERIAL_CATEGORY,
        STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
        STRATEGY_MATERIAL_ONLY,
        STRATEGY_EXAMINATION_COMBINATION,
        STRATEGY_MATERIAL_CATALOG,
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
    STRATEGY_EXAMINATION_COMBINATION: frozenset({"supplementary_examination"}),
    STRATEGY_MATERIAL_CATALOG: frozenset({"material_grade"}),
}

INPUT_RESOLVERS: dict[str, frozenset[str]] = {
    "nominal_pipe_size": frozenset({"nps_key"}),
    "pipe_schedule": frozenset({"schedule_key"}),
    "material_grade": frozenset({"material_catalog"}),
    "metallurgical_group": frozenset({"metallurgical_group_key"}),
    "pipe_construction_type": frozenset({"joint_category_normalize"}),
    "design_temperature": frozenset({"identity"}),
    "supplementary_examination": frozenset({"identity"}),
}

RULE_NAME_ALIASES = {
    "pipe_dimensions_nps": "by_nps",
    "pipe_dimensions_nps_schedule": "by_nps_schedule",
    "material_and_temperature": "by_material_temperature",
    "material_and_joint_category": "by_material_joint_category",
    "material_and_construction_temperature": "by_material_construction_temperature",
    "material_group_and_temperature": "by_material_group_temperature",
}

TABLE_REF_ALIASES = {
    "A-1": "asme-b313-table-A-1",
    "asme_b31.3_A-1": "asme-b313-table-A-1",
    "A-2": "asme-b313-table-A-2",
    "asme_b31.3_A-2": "asme-b313-table-A-2",
    "A-3": "asme-b313-table-A-3",
    "asme_b31.3_A-3": "asme-b313-table-A-3",
}

RULE_STRATEGY_BY_NAME = {
    "by_nps": STRATEGY_PIPE_NPS,
    "by_nps_schedule": STRATEGY_PIPE_NPS_SCHEDULE,
    "by_material_temperature": STRATEGY_MATERIAL_TEMPERATURE,
    "by_material_group_temperature": STRATEGY_MATERIAL_GROUP_TEMPERATURE,
    "by_material_joint_category": STRATEGY_MATERIAL_CATEGORY,
    "by_material_construction_temperature": STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
    "by_material": STRATEGY_MATERIAL_ONLY,
    "examination_combination": STRATEGY_EXAMINATION_COMBINATION,
    "by_grade": STRATEGY_MATERIAL_CATALOG,
    "grade": STRATEGY_MATERIAL_CATALOG,
}


@dataclass(frozen=True)
class InputSpec:
    logical_key: str
    resolver: str
    column: str | None = None
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
    row_resolution: dict[str, RowResolutionPolicy] = field(default_factory=dict)


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
    """Load lookup_rules from table definition YAML (pack tables/ preferred over node YAML)."""
    ref = TABLE_REF_ALIASES.get(str(table_ref or "").strip(), str(table_ref or "").strip())
    candidates: list[Path] = []

    # Pack table definition files (authoritative)
    b313_pack_tables = standards_root / "asme" / "asme_b31.3" / "tables"
    if ref.startswith("asme-b313-table-") or ref.startswith("asme_b31.3_"):
        stem = ref.replace("asme_b31.3_", "asme-b313-table-").replace("_", "-")
        if not stem.startswith("asme-b313-table-"):
            stem = f"asme-b313-table-{ref}"
        candidates.append(b313_pack_tables / f"{stem}.yaml")
        candidates.append(b313_pack_tables / f"{ref}.yaml")

    astm_pack_tables = standards_root / "astm" / "tables"
    astm_ids = {
        "astm_a106_material_properties": "A106",
        "astm_a105_material_properties": "A105",
        "astm_a53_material_properties": "A53",
        "astm_a312_material_properties": "A312",
    }
    astm_stem = astm_ids.get(ref)
    if astm_stem:
        candidates.append(astm_pack_tables / f"astm-{astm_stem.lower()}-material-properties.yaml")
        candidates.append(astm_pack_tables / f"{astm_stem}.yaml")
    elif ref in {"A106", "A105", "A53", "A312"}:
        candidates.append(astm_pack_tables / f"astm-{ref.lower()}-material-properties.yaml")
        candidates.append(astm_pack_tables / f"{ref}.yaml")

    # Legacy / B36.10 paths via shared candidate resolver
    candidates.extend(_table_yaml_candidates(table_ref, standards_root))

    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        data = _parse_table_yaml(path)
        rules = data.get("lookup_rules")
        if isinstance(rules, dict) and rules:
            return dict(rules)
    return {}


def _parse_row_resolution_policy(raw: Any, *, axis_key: str) -> RowResolutionPolicy | None:
    if not isinstance(raw, dict):
        return None
    interpolate_raw = raw.get("interpolate_columns")
    interpolate_columns: tuple[str, ...] = ()
    if isinstance(interpolate_raw, list):
        interpolate_columns = tuple(str(c).strip() for c in interpolate_raw if str(c).strip())

    output_columns: dict[str, OutputColumnPolicy] = {}
    output_raw = raw.get("output_columns")
    if isinstance(output_raw, dict):
        for col_name, col_item in output_raw.items():
            if not isinstance(col_item, dict):
                continue
            output_columns[str(col_name)] = OutputColumnPolicy(
                method=str(col_item.get("method") or "exact").strip(),
                unit=str(col_item.get("unit") or "").strip() or None,
            )

    min_bound = raw.get("min")
    max_bound = raw.get("max")
    return RowResolutionPolicy(
        breakpoint_column=str(raw.get("breakpoint_column") or axis_key).strip(),
        unit=str(raw.get("unit") or "").strip() or None,
        method=str(raw.get("method") or "exact").strip(),
        outside_range=str(raw.get("outside_range") or "error").strip(),
        duplicate_breakpoints=str(
            raw.get("duplicate_breakpoints") or raw.get("duplicate_rows") or "error"
        ).strip(),
        missing_value=str(raw.get("missing_value") or "error").strip(),
        min_bound=float(min_bound) if min_bound is not None else None,
        max_bound=float(max_bound) if max_bound is not None else None,
        interpolate_columns=interpolate_columns,
        output_columns=output_columns,
    )


def rule_output_column_policies(
    spec: RuleSpec,
    axis_key: str,
) -> dict[str, OutputColumnPolicy]:
    """Derive per-table-column resolution policies for a breakpoint axis."""
    axis_policy = spec.row_resolution.get(axis_key)
    if axis_policy is None:
        return {
            out_spec.column: OutputColumnPolicy(method="exact")
            for out_spec in spec.outputs.values()
        }

    if axis_policy.output_columns:
        return dict(axis_policy.output_columns)

    policies: dict[str, OutputColumnPolicy] = {}
    interpolate_set = set(axis_policy.interpolate_columns)
    for out_spec in spec.outputs.values():
        col = out_spec.column
        if col in interpolate_set:
            policies[col] = OutputColumnPolicy(
                method="linear_interpolation",
                unit=axis_policy.unit,
            )
        else:
            policies[col] = OutputColumnPolicy(method="exact", unit=axis_policy.unit)
    return policies


def load_table_row_resolution(spec: RuleSpec, logical_key: str) -> RowResolutionPolicy | None:
    return spec.row_resolution.get(logical_key)


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

    row_resolution: dict[str, RowResolutionPolicy] = {}
    row_resolution_raw = raw.get("row_resolution")
    if isinstance(row_resolution_raw, dict):
        for axis_key, axis_item in row_resolution_raw.items():
            parsed = _parse_row_resolution_policy(axis_item, axis_key=str(axis_key))
            if parsed is not None:
                row_resolution[str(axis_key)] = parsed

    return RuleSpec(
        name=normalize_rule_name(rule_name),
        strategy=strategy,
        inputs=inputs,
        outputs=outputs,
        on_no_match=no_match_action,
        on_multiple_matches=multiple_action,
        row_resolution=row_resolution,
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
