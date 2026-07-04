"""Build structured formula + parameter prompts for calculation nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.assumption_checker import field_value
from engine.graph.node_interaction import find_interaction, load_node_interactions
from engine.messaging.prompt_format import format_parameter_block, format_reply_hint
from engine.reference.formula_display import load_equation_context
from engine.reference.nomenclature_resolver import (
    NomenclatureEntry,
    enrich_input_spec,
    entry_for_symbol,
    input_applies,
    load_nomenclature_for_node,
    spec_symbol,
)
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact, FactClass, ValidationStatus, fact_is_expansion_ready, fact_scalar_value, fact_unit
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task

_CALCULATION_PHASES = frozenset(
    {
        NavigationPhase.PARAMETER_GATHERING,
        NavigationPhase.COEFFICIENT_RESOLUTION,
        NavigationPhase.EXECUTION_ASSUMPTIONS,
    }
)

_FALLBACK_SYMBOL_MAP: dict[str, str] = {
    "P": "design_pressure",
    "D": "outside_diameter",
    "NPS": "nominal_pipe_size",
    "S": "allowable_stress",
    "E": "weld_joint_efficiency",
    "W": "weld_joint_strength_reduction_factor_W",
    "Y": "temperature_coefficient_Y",
    "c": "corrosion_allowance",
}


@dataclass(frozen=True)
class KnownParam:
    symbol: str
    description: str
    display_value: str


@dataclass(frozen=True)
class MissingParam:
    symbol: str
    description: str
    guidance: str
    options: tuple[str, ...] = ()


def resolve_focus_calculation_node(
    navigation_plan: NavigationPlan | None,
    reader: StandardsReader,
    *,
    task_inputs: dict[str, Fact] | None = None,
) -> str | None:
    """Return the calculation node that should drive the formula prompt."""
    if navigation_plan is None:
        return None

    path_decision = navigation_plan.path_decision or {}
    selected = path_decision.get("selected_node")
    if selected:
        record = reader.load(str(selected))
        if str(record.metadata.get("type", "")) == "calculation":
            return record.node_id

    for node_id in navigation_plan.selected_nodes:
        record = reader.load(node_id)
        if str(record.metadata.get("type", "")) == "calculation":
            return record.node_id

    inputs = task_inputs or {}
    loading = field_value("pressure_loading", inputs)
    if loading == "internal_pressure":
        return "304.1.2-a"
    if loading == "external_pressure":
        return "B313-304.1.3"
    return None


def build_symbol_map(
    reader: StandardsReader,
    node_id: str,
    *,
    parameter_registry: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Map formula symbols to input_id for symbol-labeled user input."""
    symbol_map: dict[str, str] = dict(_FALLBACK_SYMBOL_MAP)
    if parameter_registry:
        for input_id, descriptor in parameter_registry.items():
            symbol = getattr(descriptor, "symbol", None) or (
                descriptor.get("symbol") if isinstance(descriptor, dict) else None
            )
            if symbol:
                symbol_map[str(symbol)] = str(input_id)

    record = reader.load(node_id)
    nomenclature = load_nomenclature_for_node(reader, record.metadata)
    for spec in record.metadata.get("inputs", []) or []:
        if not isinstance(spec, dict):
            continue
        spec = enrich_input_spec(spec, nomenclature if nomenclature else None)
        input_id = str(spec.get("id", ""))
        symbol = spec_symbol(spec, fallback=input_id)
        if input_id and symbol:
            symbol_map[symbol] = input_id
        if input_id == "nominal_pipe_size":
            symbol_map["NPS"] = input_id
    return symbol_map


def build_formula_parameter_prompt(
    *,
    reader: StandardsReader,
    task: Task,
    navigation_plan: NavigationPlan | None,
    missing_input_ids: list[str] | None = None,
) -> str | None:
    """Return a structured formula parameter prompt, or None if not applicable."""
    if navigation_plan is None or navigation_plan.current_phase not in _CALCULATION_PHASES:
        return None

    node_id = resolve_focus_calculation_node(
        navigation_plan,
        reader,
        task_inputs=task.fact_store.active_facts(),
    )
    if node_id is None:
        return None

    eq_ctx = load_equation_context(reader, node_id)
    display = eq_ctx.get("display")
    if not display:
        return None

    known, missing = classify_formula_parameters(
        reader,
        node_id,
        task_inputs=task.fact_store.active_facts(),
        missing_input_ids=missing_input_ids or [],
        navigation_plan=navigation_plan,
    )
    if not missing:
        return None

    context = summarize_path_context(dict(task.fact_store.active_facts()), navigation_plan)
    purpose = _purpose_line(eq_ctx)
    lines: list[str] = []

    if context:
        lines.append(
            f"Based on your inputs — {context} — {purpose}"
        )
    else:
        lines.append(purpose)

    lines.append("")
    lines.append("Formula:")
    lines.append(f"  {display}")
    lines.append("")
    lines.append("Known parameters:")
    if known:
        for param in known:
            lines.extend(
                format_parameter_block(
                    param.symbol,
                    param.description,
                    value=param.display_value,
                )
            )
    else:
        lines.append("  (none yet)")
        lines.append("")
    lines.append("Missing parameters:")
    if missing:
        for param in missing:
            lines.extend(
                format_parameter_block(
                    param.symbol,
                    param.description,
                    guidance=param.guidance,
                    options=param.options,
                )
            )
    else:
        lines.append("  (none)")
        lines.append("")
    lines.append("Please provide or confirm all missing parameters.")
    lines.append("You may reply with symbol-labeled values, for example:")
    lines.append("  P: 8 bar")
    lines.append("  D: 4 inch")
    lines.append("  NPS: 10")
    if any(param.options for param in missing):
        lines.append(format_reply_hint(2, examples=("1", "confirm")))
    return "\n".join(lines)


def classify_formula_parameters(
    reader: StandardsReader,
    node_id: str,
    *,
    task_inputs: dict[str, Fact],
    missing_input_ids: list[str],
    navigation_plan: NavigationPlan | None = None,
) -> tuple[list[KnownParam], list[MissingParam]]:
    """Classify equation variables as known or missing for prompt display."""
    record = reader.load(node_id)
    nomenclature = load_nomenclature_for_node(reader, record.metadata)
    interaction_specs = load_node_interactions(record, reader)
    eq_ctx = load_equation_context(reader, node_id)
    variable_order = list(eq_ctx.get("variables") or [])
    if not variable_order:
        variable_order = ["P", "D", "S", "E", "W", "Y"]

    phase_missing = set(missing_input_ids)
    if navigation_plan and navigation_plan.phase_missing:
        phase_missing.update(
            navigation_plan.phase_missing.get(navigation_plan.current_phase.value, [])
        )

    known: list[KnownParam] = []
    missing: list[MissingParam] = []
    seen_symbols: set[str] = set()

    for symbol in variable_order:
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        input_spec = _input_spec_for_symbol(record.metadata, symbol)
        if symbol != "D" and symbol != "S" and input_spec and not input_applies(input_spec, task_inputs):
            continue

        entry = entry_for_symbol(nomenclature, symbol=symbol)
        description = _description_for(symbol, input_spec, entry)
        input_id = _input_id_for(symbol, input_spec, entry)

        known_value = _resolve_known_display(
            reader,
            symbol=symbol,
            input_id=input_id,
            task_inputs=task_inputs,
            input_spec=input_spec,
        )
        if known_value is not None:
            known.append(KnownParam(symbol=symbol, description=description, display_value=known_value))
            continue

        if _is_missing(symbol, input_id, input_spec, task_inputs, phase_missing):
            guidance = _missing_guidance(
                reader,
                symbol=symbol,
                input_id=input_id,
                input_spec=input_spec,
                entry=entry,
                task_inputs=task_inputs,
                record_metadata=record.metadata,
            )
            options = _options_for_parameter(
                symbol=symbol,
                input_id=input_id,
                task_inputs=task_inputs,
                input_spec=input_spec,
                interaction_specs=interaction_specs,
            )
            missing.append(
                MissingParam(
                    symbol=symbol,
                    description=description,
                    guidance=guidance,
                    options=options,
                )
            )

    return known, missing


def summarize_path_context(
    task_inputs: dict[str, Fact],
    navigation_plan: NavigationPlan | None,
) -> str:
    """Summarize confirmed decisions and inputs that led to the calculation node."""
    fragments: list[str] = []

    if task_inputs.get("straight_pipe_section") and _input_has_value(
        task_inputs["straight_pipe_section"]
    ):
        val = fact_scalar_value(task_inputs["straight_pipe_section"])
        if val is True:
            fragments.append("straight pipe section")

    loading = field_value("pressure_loading", task_inputs)
    if loading == "internal_pressure":
        fragments.append("internal pressure loading")
    elif loading == "external_pressure":
        fragments.append("external pressure loading")

    for input_id, label in (
        ("design_pressure", None),
        ("material", None),
        ("design_temperature", None),
        ("nominal_pipe_size", "NPS"),
        ("outside_diameter", None),
    ):
        inp = task_inputs.get(input_id)
        if inp is None or not _input_has_value(inp):
            continue
        if inp.requires_confirmation and not fact_is_expansion_ready(inp):
            continue
        if label:
            fragments.append(f"{label} {fact_scalar_value(inp)}")
        elif input_id == "design_pressure":
            unit = inp.original_unit or fact_unit(inp)
            fragments.append(f"design pressure {_format_scalar(fact_scalar_value(inp))} {unit}")
        elif input_id == "design_temperature":
            unit = inp.original_unit or fact_unit(inp)
            fragments.append(f"design temperature {fact_scalar_value(inp)} {unit}")
        elif input_id == "material":
            fragments.append(f"material {fact_scalar_value(inp)}")
        elif input_id == "outside_diameter":
            unit = inp.original_unit or fact_unit(inp)
            fragments.append(f"outside diameter {fact_scalar_value(inp)} {unit}")

    if navigation_plan and navigation_plan.path_decision:
        node = navigation_plan.path_decision.get("selected_node", "")
        if node == "304.1.2-a" and "internal pressure" not in " ".join(fragments):
            fragments.append("§304.1.2 internal pressure design")

    return ", ".join(fragments)


def _purpose_line(eq_ctx: dict[str, Any]) -> str:
    purpose = str(eq_ctx.get("purpose", "")).strip()
    title = str(eq_ctx.get("title", "")).strip()
    combined = f"{purpose} {title}".lower()
    if "wall thickness" in combined and "internal" in combined:
        return (
            "the following formula will be evaluated which will calculate "
            "the minimum pipe wall thickness (internally pressurized)."
        )
    if purpose:
        cleaned = purpose.rstrip(".")
        if cleaned.lower().startswith("calculate "):
            cleaned = cleaned[len("calculate ") :]
        elif cleaned.lower().startswith("calculate"):
            cleaned = cleaned[len("calculate") :].lstrip()
        return f"the following formula will be evaluated which will calculate {cleaned.lower()}."
    if title:
        return f"the following formula will be evaluated for {title.lower()}."
    return "the following formula will be evaluated."


def _input_spec_for_symbol(metadata: dict[str, Any], symbol: str) -> dict[str, Any] | None:
    for spec in metadata.get("inputs", []) or []:
        if not isinstance(spec, dict):
            continue
        if spec_symbol(spec) == symbol:
            return spec
    return None


def _input_id_for(
    symbol: str,
    input_spec: dict[str, Any] | None,
    entry: NomenclatureEntry | None,
) -> str:
    if input_spec and input_spec.get("id"):
        return str(input_spec["id"])
    if entry and entry.input_id:
        return entry.input_id
    return _FALLBACK_SYMBOL_MAP.get(symbol, symbol.lower())


def _description_for(
    symbol: str,
    input_spec: dict[str, Any] | None,
    entry: NomenclatureEntry | None,
) -> str:
    if input_spec and input_spec.get("description"):
        return str(input_spec["description"]).strip().rstrip(".")
    if entry and entry.description:
        return entry.description.strip().rstrip(".")
    return symbol


def _input_has_value(inp: Fact) -> bool:
    if inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return False
    return fact_scalar_value(inp) is not None


def _is_known_input(inp: Fact) -> bool:
    if inp.requires_confirmation and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return False
    if inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return False
    return fact_scalar_value(inp) is not None


def _resolve_known_display(
    reader: StandardsReader,
    *,
    symbol: str,
    input_id: str,
    task_inputs: dict[str, Fact],
    input_spec: dict[str, Any] | None,
) -> str | None:
    if symbol == "D":
        return _resolve_d_display(reader, task_inputs)
    if symbol == "S":
        return _resolve_s_display(task_inputs)

    inp = task_inputs.get(input_id)
    if inp is not None and _is_known_input(inp):
        unit = inp.original_unit or fact_unit(inp)
        if unit and unit != "dimensionless":
            return f"{_format_scalar(fact_scalar_value(inp))} {unit}"
        return _format_scalar(fact_scalar_value(inp))
    return None


def _format_scalar(value: Any) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _resolve_d_display(
    reader: StandardsReader,
    task_inputs: dict[str, Fact],
) -> str | None:
    mode = field_value("d_input_mode", task_inputs) or "nps_lookup"
    od = task_inputs.get("outside_diameter")
    if od is not None and _is_known_input(od):
        unit = od.original_unit or fact_unit(od)
        return f"{_format_scalar(fact_scalar_value(od))} {unit}"

    if mode == "nps_lookup":
        nps = task_inputs.get("nominal_pipe_size")
        if nps is not None and _is_known_input(nps):
            try:
                lookup = PipeDimensionLookup(reader.standards_root)
                result = lookup.lookup(str(fact_scalar_value(nps)))
                return f"{result.outside_diameter_mm} mm (NPS {fact_scalar_value(nps)}, ASME B36.10)"
            except (ValueError, FileNotFoundError):
                return f"NPS {fact_scalar_value(nps)} (lookup pending)"
    return None


def _resolve_s_display(task_inputs: dict[str, Fact]) -> str | None:
    s_inp = task_inputs.get("allowable_stress")
    if s_inp is not None and _is_known_input(s_inp):
        unit = s_inp.original_unit or fact_unit(s_inp)
        return f"{_format_scalar(fact_scalar_value(s_inp))} {unit}"
    return None


def _is_missing(
    symbol: str,
    input_id: str,
    input_spec: dict[str, Any] | None,
    task_inputs: dict[str, Fact],
    phase_missing: set[str],
) -> bool:
    if symbol == "D":
        mode = field_value("d_input_mode", task_inputs)
        if mode == "direct_od":
            return "outside_diameter" in phase_missing or "outside_diameter" not in task_inputs
        if task_inputs.get("outside_diameter") and _is_known_input(task_inputs["outside_diameter"]):
            return False
        return (
            "nominal_pipe_size" in phase_missing
            or "outside_diameter" in phase_missing
            or (
                "nominal_pipe_size" not in task_inputs
                and "outside_diameter" not in task_inputs
            )
            or (
                task_inputs.get("nominal_pipe_size")
                and not _is_known_input(task_inputs["nominal_pipe_size"])
            )
        )

    if symbol == "S":
        if _resolve_s_display(task_inputs) is not None:
            return False
        return (
            "material" in phase_missing
            or "design_temperature" in phase_missing
            or "material" not in task_inputs
            or "design_temperature" not in task_inputs
            or input_id in phase_missing
        )

    inp = task_inputs.get(input_id)
    if inp is not None and _is_known_input(inp):
        return False
    if inp is not None and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return True
    return input_id in phase_missing or inp is None


def _missing_guidance(
    reader: StandardsReader,
    *,
    symbol: str,
    input_id: str,
    input_spec: dict[str, Any] | None,
    entry: NomenclatureEntry | None,
    task_inputs: dict[str, Fact],
    record_metadata: dict[str, Any],
) -> str:
    if symbol == "D":
        mode = field_value("d_input_mode", task_inputs)
        if mode == "direct_od":
            return (
                "enter the outside diameter of the pipe directly (mm or in), "
                "e.g. D: 4 inch"
            )
        return (
            "requires NPS for lookup value from dimensions in ASME B36.10 "
            "or specify the outside diameter directly (e.g. D: 4 inch or NPS: 10)"
        )

    if symbol == "S":
        parts = ["looked up from Table A-1 at design metal temperature"]
        if "material" not in task_inputs:
            parts.append("requires material specification")
        if "design_temperature" not in task_inputs:
            parts.append("requires design temperature")
        return ". ".join(parts) + "."

    if inp := task_inputs.get(input_id):
        if inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
            default_val = inp.default if inp.default is not None else fact_scalar_value(inp)
            condition = inp.default_condition or ""
            base = f"default is {default_val}"
            if condition:
                base += f" when {condition}"
            return f"{base}. Confirm or enter another value (e.g. {symbol}: {default_val})."

    if input_spec:
        source = str(input_spec.get("source", ""))
        default = input_spec.get("default")
        requires_conf = bool(input_spec.get("requires_confirmation", False))
        refs = _reference_hint(entry)
        if source == "default" and default is not None and requires_conf:
            text = f"default {symbol} = {default}"
            if refs:
                text += f" ({refs})"
            text += f". Confirm or enter a value directly (e.g. {symbol}: {default})."
            return text
        if source == "resolved":
            text = refs or str(input_spec.get("description", ""))
            if default is not None:
                text += f"; default {symbol} = {default}"
            if symbol == "Y" and "design_temperature" not in task_inputs:
                text += "; provide design temperature for Table 304.1.1-1 lookup"
            if requires_conf:
                text += f". Confirm or enter a value (e.g. {symbol}: {default})."
            return text.rstrip(".") + "."

    if symbol == "E":
        return (
            "looked up from Tables A-2 and A-3. "
            "Input pipe/joint category for lookup, or enter E directly. "
            "Default E = 1.0 for seamless pipe."
        )
    if symbol == "W":
        return (
            "weld strength reduction factor per §302.3.5-e; "
            "default W = 1.0 — confirm or enter a value directly."
        )
    if symbol == "Y":
        return (
            "coefficient from Table 304.1.1-1 (interpolate for intermediate temperatures); "
            "default Y = 0.4 for thin-wall — confirm or provide design temperature for lookup."
        )

    return f"provide {symbol} or confirm the proposed default."


def _options_for_parameter(
    *,
    symbol: str,
    input_id: str,
    task_inputs: dict[str, Fact],
    input_spec: dict[str, Any] | None,
    interaction_specs: list,
) -> tuple[str, ...]:
    """Return numbered choices when the missing input has a finite option set."""
    spec = find_interaction(interaction_specs, input_id)
    if spec is not None and spec.mode.value == "decision" and spec.options:
        return tuple(_decision_option_label(value) for value in spec.options)

    if symbol == "D":
        mode = field_value("d_input_mode", task_inputs)
        if mode is None:
            return (
                "Nominal pipe size (NPS) — look up outside diameter per ASME B36.10",
                "Outside diameter — enter D directly (mm or in)",
            )

    inp = task_inputs.get(input_id)
    default_val: Any | None = None
    if inp is not None and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        default_val = inp.default if inp.default is not None else fact_scalar_value(inp)
    elif input_spec and input_spec.get("default") is not None:
        default_val = input_spec.get("default")

    requires_confirm = bool(
        (inp is not None and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING)
        or (input_spec and input_spec.get("requires_confirmation"))
    )
    if requires_confirm and default_val is not None:
        return (
            f"Confirm default ({symbol} = {default_val})",
            f"Enter a different value (e.g. {symbol}: {default_val})",
        )

    return ()


def _decision_option_label(value: str) -> str:
    if value == "nps_lookup":
        return "Nominal pipe size (NPS) — look up outside diameter per ASME B36.10"
    if value == "direct_od":
        return "Outside diameter — enter D directly (mm or in)"
    if value == "seamless":
        return "Seamless pipe (default)"
    if value == "erw":
        return "Electric-resistance welded (ERW)"
    if value == "furnace_butt_welded":
        return "Furnace butt-welded"
    if value == "forging":
        return "Forging"
    return str(value).replace("_", " ").title()


def _reference_hint(entry: NomenclatureEntry | None) -> str:
    if entry is None:
        return ""
    refs: list[str] = []
    for ref in entry.references:
        if ref.get("table"):
            refs.append(str(ref["table"]))
        elif ref.get("paragraph"):
            refs.append(f"§{ref['paragraph']}")
    if refs:
        return "from " + ", ".join(refs)
    return entry.description.strip().rstrip(".")
