"""Build structured formula + parameter prompts for calculation nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.lookup_parameter_resolution import (
    param_node_id_for_fact_key,
    parameter_resolution_for_parameter,
    prerequisite_input_keys,
)
from engine.graph.node_interaction import find_interaction, load_node_interactions, question_for_interaction
from engine.messaging.parameter_prompt_context import (
    composer_option_label,
    parameter_metadata_context,
)
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
from engine.reference.parameter_display_value import (
    format_scalar_display,
    is_known_fact,
    resolve_parameter_display_value,
)
from engine.reference.parameter_keys import canonical_parameter_key, param_node_id_for_input, read_parameter_value
from engine.reference.parameter_value_source import resolve_parameter_value_reference
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
    _ = task_inputs
    if navigation_plan is None:
        return None

    path_decision = navigation_plan.path_decision or {}
    selected = path_decision.get("selected_node")
    if selected:
        record = reader.load(str(selected))
        if str(record.metadata.get("type", "")) in {"calculation", "equation"}:
            return record.node_id

    for node_id in navigation_plan.selected_nodes:
        record = reader.load(node_id)
        if str(record.metadata.get("type", "")) in {"calculation", "equation"}:
            return record.node_id
    return None


def build_symbol_map(
    reader: StandardsReader,
    node_id: str,
    *,
    parameter_registry: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Map formula symbols to input_id for symbol-labeled user input."""
    symbol_map: dict[str, str] = {}
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
        node_id = focus_node_for_parameter(reader, task, dict(task.fact_store.active_facts()))
    if node_id is None:
        return None

    eq_ctx = load_equation_context(
        reader,
        node_id,
        task_facts=dict(task.fact_store.active_facts()),
    )
    display = eq_ctx.get("display")
    if not display:
        return None

    known, missing = classify_formula_parameters(
        reader,
        node_id,
        task_inputs=task.fact_store.active_facts(),
        missing_input_ids=missing_input_ids or [],
        navigation_plan=navigation_plan,
        task=task,
    )
    if not missing:
        return None

    context = summarize_path_context(reader, dict(task.fact_store.active_facts()))
    purpose = _purpose_line(eq_ctx)
    lines: list[str] = []

    if context:
        lines.append(f"Based on your inputs — {context} — {purpose}")
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
    for param in missing[:3]:
        metadata_ctx = parameter_metadata_context(reader, _param_key_for_symbol(param.symbol, reader, node_id))
        example = metadata_ctx.input_examples[0] if metadata_ctx and metadata_ctx.input_examples else None
        if example:
            lines.append(f"  {param.symbol}: {example}")
        else:
            lines.append(f"  {param.symbol}: …")
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
    task: Task | None = None,
) -> tuple[list[KnownParam], list[MissingParam]]:
    """Classify equation variables as known or missing for prompt display."""
    record = reader.load(node_id)
    nomenclature = load_nomenclature_for_node(reader, record.metadata)
    interaction_specs = load_node_interactions(record, reader)
    eq_ctx = load_equation_context(
        reader,
        node_id,
        task_facts=dict(task_inputs),
    )
    variable_order = list(eq_ctx.get("variables") or [])
    if not variable_order:
        return [], []

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
        if input_spec and not input_applies(input_spec, task_inputs):
            continue

        entry = entry_for_symbol(nomenclature, symbol=symbol)
        description = _description_for(reader, symbol, input_spec, entry)
        input_id = _input_id_for(symbol, input_spec, entry)

        known_value = resolve_parameter_display_value(reader, input_id, task_inputs)
        if known_value is not None:
            known.append(KnownParam(symbol=symbol, description=description, display_value=known_value))
            continue

        if not _is_missing(reader, input_id, input_spec, task_inputs, phase_missing):
            continue

        if _lookup_prerequisites_missing(reader, input_id, task_inputs) and input_id not in phase_missing:
            continue

        guidance = _missing_guidance(
            reader,
            task=task,
            symbol=symbol,
            input_id=input_id,
            input_spec=input_spec,
            entry=entry,
            task_inputs=task_inputs,
        )
        options = _options_for_parameter(
            reader=reader,
            input_id=input_id,
            task_inputs=task_inputs,
            input_spec=input_spec,
            interaction_specs=interaction_specs,
            symbol=symbol,
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
    reader: StandardsReader,
    task_inputs: dict[str, Fact],
) -> str:
    """Summarize confirmed inputs using PARAM labels and composer option text."""
    fragments: list[str] = []
    for key, inp in task_inputs.items():
        if not _input_has_value(inp):
            continue
        if inp.requires_confirmation and not fact_is_expansion_ready(inp):
            continue
        canonical = canonical_parameter_key(key)
        metadata_ctx = parameter_metadata_context(reader, canonical)
        label = metadata_ctx.name if metadata_ctx and metadata_ctx.name else canonical.replace("_", " ")
        value = fact_scalar_value(inp)
        if value is None:
            continue
        if isinstance(value, bool) and metadata_ctx:
            fragments.append(composer_option_label(metadata_ctx, str(value).lower()))
            continue
        if metadata_ctx and metadata_ctx.composer_options:
            fragments.append(composer_option_label(metadata_ctx, str(value)))
            continue
        display = resolve_parameter_display_value(reader, canonical, task_inputs)
        if display:
            fragments.append(f"{label} {display}")
        else:
            unit = inp.original_unit or fact_unit(inp)
            if unit and unit != "dimensionless":
                fragments.append(f"{label} {format_scalar_display(value)} {unit}")
            else:
                fragments.append(f"{label} {format_scalar_display(value)}")
    return ", ".join(fragments)


def focus_node_for_parameter(
    reader: StandardsReader,
    task: Task,
    facts: dict[str, Fact],
) -> str | None:
    active_definition = task.outputs.get("active_definition_node")
    if active_definition:
        return str(active_definition)

    selected = task.outputs.get("selected_nodes")
    if isinstance(selected, list):
        for node_id in selected:
            try:
                if str(reader.load(str(node_id)).metadata.get("type", "")) == "calculation":
                    return str(node_id)
            except FileNotFoundError:
                continue

    planning = task.outputs.get("engineering_plan") or task.outputs.get("navigation_plan")
    if isinstance(planning, dict):
        path = planning.get("path_decision") or {}
        if isinstance(path, dict) and path.get("selected_node"):
            return str(path["selected_node"])
        selected_nodes = planning.get("selected_nodes") or []
        for node_id in selected_nodes:
            try:
                if str(reader.load(str(node_id)).metadata.get("type", "")) == "calculation":
                    return str(node_id)
            except FileNotFoundError:
                continue

    _ = facts
    return None


def guidance_for_parameter_input(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
) -> str | None:
    """Return equation/lookup guidance for a missing calculation parameter."""
    facts = dict(task.fact_store.active_facts())
    node_id = focus_node_for_parameter(reader, task, facts)
    if node_id is None:
        return None

    record = reader.load(node_id)
    nomenclature = load_nomenclature_for_node(reader, record.metadata)
    interaction_specs = load_node_interactions(record, reader)
    eq_ctx = load_equation_context(
        reader,
        node_id,
        task_facts=facts,
    )
    variable_order = list(eq_ctx.get("variables") or [])

    for symbol in variable_order:
        input_spec = _input_spec_for_symbol(record.metadata, symbol)
        if input_spec and not input_applies(input_spec, facts):
            continue
        entry = entry_for_symbol(nomenclature, symbol=symbol)
        input_id = _input_id_for(symbol, input_spec, entry)
        if canonical_parameter_key(input_id) != canonical_parameter_key(parameter_id):
            continue
        guidance = _missing_guidance(
            reader,
            task=task,
            symbol=symbol,
            input_id=input_id,
            input_spec=input_spec,
            entry=entry,
            task_inputs=facts,
        )
        display = eq_ctx.get("display")
        if isinstance(display, str) and display.strip():
            return f"Used in the governing equation: {display.strip()}\n\n{guidance}"
        return guidance

    spec = find_interaction(interaction_specs, parameter_id)
    if spec is not None:
        return question_for_interaction(spec, facts)
    return None


def _purpose_line(eq_ctx: dict[str, Any]) -> str:
    purpose = str(eq_ctx.get("purpose", "")).strip()
    title = str(eq_ctx.get("title", "")).strip()
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
    return symbol.lower()


def _param_key_for_symbol(symbol: str, reader: StandardsReader, node_id: str) -> str:
    record = reader.load(node_id)
    input_spec = _input_spec_for_symbol(record.metadata, symbol)
    entry = entry_for_symbol(load_nomenclature_for_node(reader, record.metadata), symbol=symbol)
    return _input_id_for(symbol, input_spec, entry)


def _description_for(
    reader: StandardsReader,
    symbol: str,
    input_spec: dict[str, Any] | None,
    entry: NomenclatureEntry | None,
) -> str:
    input_id = _input_id_for(symbol, input_spec, entry)
    metadata_ctx = parameter_metadata_context(reader, input_id)
    if metadata_ctx and metadata_ctx.description:
        return metadata_ctx.description.strip().rstrip(".")
    if input_spec and input_spec.get("description"):
        return str(input_spec["description"]).strip().rstrip(".")
    if entry and entry.description:
        return entry.description.strip().rstrip(".")
    return symbol


def _input_has_value(inp: Fact) -> bool:
    if inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return False
    return fact_scalar_value(inp) is not None


def _lookup_prerequisites_missing(
    reader: StandardsReader,
    input_id: str,
    task_inputs: dict[str, Fact],
) -> bool:
    store = reader.graph_store
    if not store.available:
        return False
    param_node_id = param_node_id_for_fact_key(store, input_id)
    if param_node_id is None:
        return False
    resolution = parameter_resolution_for_parameter(store, param_node_id)
    if not isinstance(resolution, dict) or resolution.get("method") != "table_lookup":
        return False
    for key in prerequisite_input_keys(store, input_id):
        if read_parameter_value(task_inputs, key) is None:
            return True
    return False


def _is_missing(
    reader: StandardsReader,
    input_id: str,
    input_spec: dict[str, Any] | None,
    task_inputs: dict[str, Fact],
    phase_missing: set[str],
) -> bool:
    if resolve_parameter_display_value(reader, input_id, task_inputs) is not None:
        return False

    inp = read_parameter_value(task_inputs, input_id)
    if inp is not None and is_known_fact(inp):
        return False
    if inp is not None and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return True
    if canonical_parameter_key(input_id) in {canonical_parameter_key(item) for item in phase_missing}:
        return True
    if input_id in phase_missing:
        return True
    if inp is None:
        return True
    return False


def _missing_guidance(
    reader: StandardsReader,
    *,
    task: Task | None,
    symbol: str,
    input_id: str,
    input_spec: dict[str, Any] | None,
    entry: NomenclatureEntry | None,
    task_inputs: dict[str, Fact],
) -> str:
    metadata_ctx = parameter_metadata_context(reader, input_id)

    inp = read_parameter_value(task_inputs, input_id)
    if inp is not None and inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
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
            if requires_conf:
                text += f". Confirm or enter a value (e.g. {symbol}: {default})."
            return text.rstrip(".") + "."

    missing_keys = []
    store = reader.graph_store
    if store.available:
        for key in prerequisite_input_keys(store, input_id):
            if read_parameter_value(task_inputs, key) is None:
                key_ctx = parameter_metadata_context(reader, key)
                missing_keys.append(key_ctx.name if key_ctx and key_ctx.name else key.replace("_", " "))

    if task is not None:
        param_node_id = param_node_id_for_input(canonical_parameter_key(input_id))
        value_ref = resolve_parameter_value_reference(reader, param_node_id, task)
        if value_ref and value_ref.get("label"):
            text = f"Resolved from {value_ref['label']}"
            if missing_keys:
                text += f"; requires {', '.join(missing_keys)}"
            return text + "."

    if metadata_ctx and metadata_ctx.description:
        text = metadata_ctx.description.strip().rstrip(".")
        if missing_keys:
            text += f"; requires {', '.join(missing_keys)}"
        return text + "."

    if missing_keys:
        return f"provide {', '.join(missing_keys)} to resolve {symbol}."

    return f"provide {symbol} or confirm the proposed default."


def _options_for_parameter(
    *,
    reader: StandardsReader,
    input_id: str,
    task_inputs: dict[str, Fact],
    input_spec: dict[str, Any] | None,
    interaction_specs: list,
    symbol: str,
) -> tuple[str, ...]:
    metadata_ctx = parameter_metadata_context(reader, input_id)
    spec = find_interaction(interaction_specs, input_id)
    if spec is not None and spec.mode.value == "decision" and spec.options:
        return tuple(composer_option_label(metadata_ctx, value) for value in spec.options)

    inp = read_parameter_value(task_inputs, input_id)
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


# Backward-compatible alias used by parameter_input_prompt
_focus_node_for_parameter = focus_node_for_parameter
