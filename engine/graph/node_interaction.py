"""Generic node-level user interaction requirements.

Nodes declare how values must be selected, confirmed, looked up, or defaulted.
The graph executor enforces these rules; the input extractor only parses user text
against pending interaction specs (no domain-specific decision logic).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from engine.graph.assumption_checker import field_value, normalize_assumption_value
from engine.reference.node_types import is_section_node, parameter_input_id
from engine.reference.nomenclature_resolver import (
    default_question,
    input_applies,
    load_nomenclature,
    load_nomenclature_for_node,
    resolve_input_spec,
)
from engine.reference.standards_reader import NodeRecord, StandardsReader
from models.input import (
    EngineeringInput,
    InputSource,
    InputStatus,
    input_is_expansion_ready,
    proposed_default_input,
)


class InteractionMode(str, Enum):
    DECISION = "decision"
    VALUE_RESOLUTION = "value_resolution"


@dataclass(frozen=True)
class NodeInteractionSpec:
    """A single variable the workflow may require from the user."""

    variable: str
    mode: InteractionMode
    node_id: str
    required: bool = True
    options: tuple[str, ...] = ()
    aliases: tuple[tuple[str, str], ...] = ()
    sources: tuple[str, ...] = ("user",)
    default: Any | None = None
    confirmation_required: bool = False
    question: str | None = None
    lookup_source: str | None = None
    unit: str = "dimensionless"
    symbol: str | None = None
    default_condition: str | None = None

    def alias_map(self) -> dict[str, str]:
        return {key: value for key, value in self.aliases}


@dataclass
class InteractionEvaluation:
    missing_fields: list[str] = field(default_factory=list)
    field_nodes: dict[str, str] = field(default_factory=dict)
    field_questions: dict[str, str] = field(default_factory=dict)
    pending_confirmations: dict[str, Any] = field(default_factory=dict)

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_fields)


def parse_interactions(metadata: dict[str, Any], node_id: str) -> list[NodeInteractionSpec]:
    """Parse explicit ``interactions`` entries from node frontmatter."""
    specs: list[NodeInteractionSpec] = []
    for item in metadata.get("interactions", []) or []:
        if not isinstance(item, dict):
            continue
        spec = _interaction_from_dict(item, node_id)
        if spec is not None:
            specs.append(spec)
    return specs


def _interaction_from_dict(item: dict[str, Any], node_id: str) -> NodeInteractionSpec | None:
    variable = str(item.get("variable") or item.get("field") or "")
    if not variable:
        return None

    mode_raw = str(item.get("mode", "decision"))
    try:
        mode = InteractionMode(mode_raw)
    except ValueError:
        mode = InteractionMode.DECISION

    options = tuple(str(v) for v in (item.get("options") or []))
    aliases_raw = item.get("aliases") or {}
    aliases: list[tuple[str, str]] = []
    if isinstance(aliases_raw, dict):
        for key, value in aliases_raw.items():
            aliases.append((str(key), str(value)))

    sources_raw = item.get("sources") or item.get("source")
    if isinstance(sources_raw, str):
        sources = (sources_raw,)
    elif isinstance(sources_raw, list):
        sources = tuple(str(s) for s in sources_raw)
    else:
        sources = ("user",)

    value_resolution = item.get("value_resolution")
    if isinstance(value_resolution, dict):
        mode = InteractionMode.VALUE_RESOLUTION
        sources_raw = value_resolution.get("source") or value_resolution.get("sources")
        if isinstance(sources_raw, str):
            sources = (sources_raw,)
        elif isinstance(sources_raw, list):
            sources = tuple(str(s) for s in sources_raw)
        if "confirmation_required" in value_resolution:
            confirmation_required = bool(value_resolution["confirmation_required"])
        else:
            confirmation_required = bool(item.get("confirmation_required", False))
    else:
        confirmation_required = bool(item.get("confirmation_required", False))

    return NodeInteractionSpec(
        variable=variable,
        mode=mode,
        node_id=node_id,
        required=bool(item.get("required", True)),
        options=options,
        aliases=tuple(aliases),
        sources=sources,
        default=item.get("default") or item.get("default_value"),
        confirmation_required=confirmation_required,
        question=str(item["question"]) if item.get("question") else None,
        lookup_source=str(item["lookup_source"]) if item.get("lookup_source") else None,
        unit=str(item.get("unit", "dimensionless")),
        symbol=str(item["symbol"]) if item.get("symbol") else None,
        default_condition=str(item["default_condition"]) if item.get("default_condition") else None,
    )


def parse_value_requirements(metadata: dict[str, Any], node_id: str) -> list[NodeInteractionSpec]:
    """Parse ``value_requirements`` entries (alias schema for value resolution)."""
    specs: list[NodeInteractionSpec] = []
    for item in metadata.get("value_requirements", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("variable") or "")
        if not name:
            continue
        mapped = {
            "variable": name,
            "mode": "value_resolution",
            "source": item.get("source"),
            "default": item.get("default_value", item.get("default")),
            "confirmation_required": item.get("confirmation_required", True),
            "question": item.get("question"),
            "unit": item.get("unit", "dimensionless"),
            "symbol": item.get("symbol"),
            "required": item.get("required", True),
        }
        spec = _interaction_from_dict(mapped, node_id)
        if spec is not None:
            specs.append(spec)
    return specs


def interaction_from_assumption(item: dict[str, Any], node_id: str) -> NodeInteractionSpec | None:
    """Bridge legacy ``assumptions`` with a ``field`` into decision interactions."""
    field_name = str(item.get("field", ""))
    if not field_name:
        return None
    if not bool(item.get("required_for_expansion", False)) and not bool(
        item.get("required_for_execution", False)
    ):
        return None

    allowed = tuple(normalize_assumption_value(v) for v in (item.get("allowed_values") or []))
    mode = (
        InteractionMode.DECISION
        if allowed or bool(item.get("required_for_expansion", False))
        else InteractionMode.VALUE_RESOLUTION
    )
    return NodeInteractionSpec(
        variable=field_name,
        mode=mode,
        node_id=node_id,
        required=True,
        options=allowed,
        default=item.get("default"),
        confirmation_required=bool(item.get("requires_confirmation", False)),
        question=str(item.get("description", "")) or None,
    )


def interaction_from_input(item: dict[str, Any], node_id: str) -> NodeInteractionSpec | None:
    """Bridge node ``inputs`` with confirmation or default resolution."""
    input_id = str(item.get("id", ""))
    if not input_id:
        return None

    source = str(item.get("source", "user_input"))
    requires_confirmation = bool(item.get("requires_confirmation", False))
    has_default = item.get("default") is not None

    if not requires_confirmation and source != "default":
        return None
    if source == "default" and not requires_confirmation:
        return None

    sources: list[str] = []
    if source in ("user_input", "user"):
        sources.append("user")
    if source in ("default", "resolved") or has_default:
        sources.append("default")
    if source in ("table", "lookup", "node_output", "resolved"):
        sources.append("lookup")

    mode = InteractionMode.VALUE_RESOLUTION
    return NodeInteractionSpec(
        variable=input_id,
        mode=mode,
        node_id=node_id,
        required=bool(item.get("required", True)),
        sources=tuple(sources or ("user", "default")),
        default=item.get("default"),
        confirmation_required=requires_confirmation or source in ("default", "resolved"),
        question=str(item.get("description", "")) or None,
        lookup_source=source if source in ("table", "lookup") else None,
        unit=str(item.get("unit", "dimensionless")),
        symbol=str(item.get("name", "")) or None,
        default_condition=str(item["default_condition"]) if item.get("default_condition") else None,
    )


def nomenclature_interactions(
    reader: StandardsReader,
    nomenclature_node_id: str,
    *,
    calc_node_id: str,
) -> list[NodeInteractionSpec]:
    """Build value-resolution interactions from nomenclature conditional defaults."""
    specs: list[NodeInteractionSpec] = []
    nomenclature = load_nomenclature(reader, nomenclature_node_id)
    for entry in nomenclature.values():
        if not entry.defaults or not entry.input_id:
            continue
        for default in entry.defaults:
            specs.append(
                NodeInteractionSpec(
                    variable=entry.input_id,
                    mode=InteractionMode.VALUE_RESOLUTION,
                    node_id=calc_node_id,
                    required=False,
                    sources=("default",),
                    default=default.value,
                    confirmation_required=default.requires_confirmation,
                    question=default_question(entry, default),
                    unit=default.unit or entry.unit,
                    symbol=entry.symbol,
                    default_condition=default.condition,
                )
            )
            break
    return specs


def load_node_interactions(record: NodeRecord, reader: StandardsReader | None = None) -> list[NodeInteractionSpec]:
    """Collect all interaction specs declared on a single node."""
    specs: list[NodeInteractionSpec] = []
    specs.extend(parse_interactions(record.metadata, record.node_id))
    specs.extend(parse_value_requirements(record.metadata, record.node_id))

    for item in record.metadata.get("assumptions", []) or []:
        if isinstance(item, dict):
            bridged = interaction_from_assumption(item, record.node_id)
            if bridged is not None:
                specs.append(bridged)

    nomenclature: dict = {}
    if reader is not None:
        nomenclature = load_nomenclature_for_node(reader, record.metadata)
        for dep in record.metadata.get("depends_on", []) or []:
            if isinstance(dep, dict) and dep.get("node_id"):
                dep_id = str(dep["node_id"])
                try:
                    dep_type = str(reader.load(dep_id).metadata.get("type", ""))
                    if dep_type in {"definition", "standard_section"}:
                        specs.extend(
                            nomenclature_interactions(
                                reader,
                                dep_id,
                                calc_node_id=record.node_id,
                            )
                        )
                except FileNotFoundError:
                    continue

    for item in record.metadata.get("inputs", []) or []:
        if isinstance(item, dict):
            merged = resolve_input_spec(item, nomenclature) if nomenclature else item
            bridged = interaction_from_input(merged, record.node_id)
            if bridged is not None:
                specs.append(bridged)

    if is_section_node(record.metadata) and reader is not None:
        specs.extend(_micro_graph_interactions(record, reader))

    return _dedupe_by_variable(specs)


def propose_decision_defaults(
    specs: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput | Any],
) -> dict[str, EngineeringInput]:
    """Auto-apply decision defaults that do not require confirmation."""
    from models.input import InputStatus, proposed_default_input

    proposed: dict[str, EngineeringInput] = {}
    for spec in specs:
        if spec.mode != InteractionMode.DECISION:
            continue
        if spec.default is None:
            continue
        if spec.variable in existing_inputs:
            continue
        if spec.confirmation_required:
            proposed[spec.variable] = proposed_default_input(
                spec.variable,
                spec.default,
                unit=spec.unit,
                default=spec.default,
                default_condition=spec.default_condition,
            )
            continue
        proposed[spec.variable] = EngineeringInput(
            input_id=spec.variable,
            value=spec.default,
            unit=spec.unit,
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=spec.default,
        )
    return proposed


def collect_path_interactions(
    reader: StandardsReader,
    node_ids: Sequence[str],
) -> list[NodeInteractionSpec]:
    """Merge interaction specs along a workflow path (first declaration wins)."""
    merged: list[NodeInteractionSpec] = []
    seen: set[str] = set()
    for node_id in node_ids:
        record = reader.load(node_id)
    for spec in load_node_interactions(record, reader):
        if spec.variable in seen:
            continue
        seen.add(spec.variable)
        merged.append(spec)
    return merged


def interaction_from_micro_assumption(
    metadata: dict[str, Any],
    node_id: str,
) -> NodeInteractionSpec | None:
    field_name = parameter_input_id(metadata)
    if not field_name:
        return None
    allowed = tuple(str(v) for v in (metadata.get("allowed_values") or []))
    return NodeInteractionSpec(
        variable=field_name,
        mode=InteractionMode.DECISION if allowed else InteractionMode.VALUE_RESOLUTION,
        node_id=node_id,
        required=bool(metadata.get("required_for_expansion", True)),
        options=allowed,
        confirmation_required=bool(metadata.get("requires_confirmation", False)),
        question=str(metadata.get("question") or metadata.get("description") or "") or None,
    )


def interaction_from_parameter(
    metadata: dict[str, Any],
    node_id: str,
) -> NodeInteractionSpec | None:
    input_id = str(metadata.get("input_id") or "")
    if not input_id:
        return None
    resolution = metadata.get("resolution") or {}
    method = str(resolution.get("method", ""))
    if method == "table_lookup":
        return NodeInteractionSpec(
            variable=input_id,
            mode=InteractionMode.VALUE_RESOLUTION,
            node_id=node_id,
            required=True,
            sources=("lookup", "user"),
            confirmation_required=True,
            question=str(metadata.get("question") or metadata.get("description") or "") or None,
            lookup_source="lookup",
            unit=str(metadata.get("unit", "dimensionless")),
            symbol=str(metadata.get("symbol") or "") or None,
        )
    if method == "user_input":
        default = resolution.get("default")
        if isinstance(default, dict) and default.get("requires_confirmation"):
            return NodeInteractionSpec(
                variable=input_id,
                mode=InteractionMode.VALUE_RESOLUTION,
                node_id=node_id,
                required=True,
                sources=("default", "user"),
                default=default.get("value"),
                confirmation_required=True,
                question=str(metadata.get("question") or "") or None,
                unit=str(default.get("unit") or metadata.get("unit", "dimensionless")),
                symbol=str(metadata.get("symbol") or "") or None,
            )
    return None


def _micro_graph_interactions(
    record: NodeRecord,
    reader: StandardsReader,
) -> list[NodeInteractionSpec]:
    specs: list[NodeInteractionSpec] = []
    refs: list[str] = []
    for ref in record.metadata.get("contains", []) or []:
        refs.append(str(ref))
    seen_refs: set[str] = set()
    for ref_id in refs:
        if ref_id in seen_refs:
            continue
        seen_refs.add(ref_id)
        try:
            child = reader.load(ref_id)
        except FileNotFoundError:
            continue
        child_type = str(child.metadata.get("type", ""))
        child_kind = str(child.metadata.get("kind", ""))
        if child_type == "parameter" and child_kind == "interaction":
            mapped = dict(child.metadata)
            mapped.setdefault("variable", parameter_input_id(child.metadata))
            bridged = _interaction_from_dict(mapped, record.node_id)
            if bridged is not None:
                specs.append(bridged)
        elif child_type == "parameter" and child_kind == "assumption":
            bridged = interaction_from_micro_assumption(child.metadata, record.node_id)
            if bridged is not None:
                specs.append(bridged)
        elif child_type == "interaction":
            mapped = dict(child.metadata)
            mapped.setdefault("variable", child.metadata.get("field"))
            bridged = _interaction_from_dict(mapped, record.node_id)
            if bridged is not None:
                specs.append(bridged)
        elif child_type == "assumption":
            bridged = interaction_from_micro_assumption(child.metadata, record.node_id)
            if bridged is not None:
                specs.append(bridged)
    return specs


def collect_root_interactions(
    reader: StandardsReader,
    root_id: str,
) -> list[NodeInteractionSpec]:
    record = reader.load(root_id)
    return load_node_interactions(record, reader)


def find_interaction(
    specs: Sequence[NodeInteractionSpec],
    variable: str,
) -> NodeInteractionSpec | None:
    for spec in specs:
        if spec.variable == variable:
            return spec
    return None


def question_for_interaction(
    spec: NodeInteractionSpec,
    existing_inputs: Mapping[str, EngineeringInput | Any] | None = None,
) -> str:
    label = spec.symbol or spec.variable
    condition_text = spec.default_condition or (
        getattr(existing_inputs.get(spec.variable), "default_condition", None)
        if existing_inputs and spec.variable in existing_inputs
        else None
    )

    if existing_inputs and spec.variable in existing_inputs:
        raw = existing_inputs[spec.variable]
        if isinstance(raw, EngineeringInput) and raw.status == InputStatus.PROPOSED_DEFAULT:
            condition = raw.default_condition or spec.default_condition
            if condition:
                return (
                    f"For {label}: the default is {raw.value} {raw.unit} when "
                    f"{condition}. Confirm or enter another value."
                )
            return (
                f"The default value for {label} is {raw.value} {raw.unit}. "
                f"Confirm or provide another value."
            )
    if spec.question:
        if spec.default is not None and condition_text:
            return spec.question
        return spec.question
    if spec.mode == InteractionMode.DECISION and spec.options:
        return (
            f"Please select a value for {spec.variable}. "
            f"Options: {', '.join(spec.options)}."
        )
    if spec.default is not None:
        if condition_text:
            return (
                f"For {label}: the default is {spec.default} {spec.unit} when "
                f"{condition_text}. Confirm or enter another value."
            )
        return (
            f"The default value for {label} is {spec.default} {spec.unit}. "
            f"Confirm or provide another value."
        )
    return f"Please provide a value for {spec.variable}."


def is_interaction_satisfied(
    spec: NodeInteractionSpec,
    existing_inputs: Mapping[str, EngineeringInput | Any],
) -> bool:
    if spec.variable not in existing_inputs:
        return not spec.required

    raw = existing_inputs[spec.variable]
    if isinstance(raw, EngineeringInput):
        if spec.confirmation_required and not input_is_expansion_ready(raw):
            if raw.status == InputStatus.PROPOSED_DEFAULT:
                return False
            if raw.status not in {InputStatus.CONFIRMED, InputStatus.USER_OVERRIDE}:
                return False
        if raw.requires_confirmation and not input_is_expansion_ready(raw):
            return False
        value = normalize_assumption_value(raw.value)
    else:
        value = normalize_assumption_value(raw)

    if spec.mode == InteractionMode.DECISION and spec.options:
        normalized_options = {normalize_assumption_value(v) for v in spec.options}
        return value in normalized_options
    return value is not None and str(value).strip() != ""


def resolve_interaction_value(spec: NodeInteractionSpec, raw_text: str) -> str | None:
    """Normalize and validate a user response against an interaction spec."""
    text = raw_text.strip()
    if not text:
        return None

    alias_map = spec.alias_map()
    normalized_key = text.lower().replace(" ", "_").replace("-", "_")
    if normalized_key in alias_map:
        candidate = normalize_assumption_value(alias_map[normalized_key])
    elif text.lower() in alias_map:
        candidate = normalize_assumption_value(alias_map[text.lower()])
    else:
        candidate = normalize_assumption_value(text)

    if spec.mode == InteractionMode.DECISION and spec.options:
        normalized_options = {normalize_assumption_value(v) for v in spec.options}
        if candidate in normalized_options:
            return candidate
        return None

    return candidate


def match_decision_in_message(message: str, spec: NodeInteractionSpec) -> str | None:
    """Return a canonical option value when the message matches a decision spec."""
    if spec.mode != InteractionMode.DECISION:
        return None

    numbered = _match_numbered_option(message, spec)
    if numbered is not None:
        return numbered

    patterns = _decision_patterns(spec)
    matches: set[str] = set()
    for pattern, canonical in patterns:
        if pattern.search(message):
            matches.add(canonical)

    if len(matches) != 1:
        return None
    return next(iter(matches))


def extract_decision_responses(
    message: str,
    pending: Sequence[NodeInteractionSpec],
) -> dict[str, str]:
    """Parse decision values from a user message for pending interactions."""
    responses: dict[str, str] = {}
    for spec in pending:
        if spec.variable in responses:
            continue
        if spec.mode != InteractionMode.DECISION:
            continue
        matched = match_decision_in_message(message, spec)
        if matched is not None:
            responses[spec.variable] = matched
    return responses


def evaluate_pending_interactions(
    specs: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput | Any],
    *,
    phase: str = "expansion",
) -> InteractionEvaluation:
    """Determine which interactions are still unsatisfied."""
    result = InteractionEvaluation()
    for spec in specs:
        if phase == "expansion":
            if spec.mode == InteractionMode.VALUE_RESOLUTION:
                if not spec.confirmation_required:
                    continue
                if "default" not in spec.sources and spec.lookup_source is None:
                    continue
            elif spec.mode == InteractionMode.DECISION:
                if not spec.options and not spec.confirmation_required:
                    continue
            else:
                continue
        if phase == "execution" and spec.mode == InteractionMode.DECISION:
            if not spec.confirmation_required:
                continue

        if is_interaction_satisfied(spec, existing_inputs):
            continue
        if not spec.required:
            continue

        if spec.variable not in result.missing_fields:
            result.missing_fields.append(spec.variable)
            result.field_nodes[spec.variable] = spec.node_id
            result.field_questions[spec.variable] = question_for_interaction(
                spec,
                existing_inputs,
            )

        stored = existing_inputs.get(spec.variable)
        if (
            isinstance(stored, EngineeringInput)
            and stored.status == InputStatus.PROPOSED_DEFAULT
        ):
            result.pending_confirmations[spec.variable] = stored.value
        elif spec.default is not None and spec.variable not in existing_inputs:
            result.pending_confirmations[spec.variable] = spec.default

    return result


def propose_default_values(
    specs: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput | Any],
) -> dict[str, EngineeringInput]:
    """Auto-propose node defaults for value-resolution specs awaiting confirmation."""
    proposed: dict[str, EngineeringInput] = {}
    for spec in specs:
        if spec.mode != InteractionMode.VALUE_RESOLUTION:
            continue
        if not spec.required:
            continue
        if not spec.confirmation_required:
            continue
        if "default" not in spec.sources or spec.default is None:
            continue
        if spec.variable in existing_inputs:
            continue
        proposed[spec.variable] = proposed_default_input(
            spec.variable,
            spec.default,
            unit=spec.unit,
            default=spec.default,
            default_condition=spec.default_condition,
        )
    return proposed


def pending_value_confirmations(
    specs: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput | Any],
) -> list[NodeInteractionSpec]:
    """Return value-resolution specs awaiting user confirmation."""
    pending: list[NodeInteractionSpec] = []
    for spec in specs:
        if spec.mode != InteractionMode.VALUE_RESOLUTION:
            continue
        if not spec.confirmation_required:
            continue
        if is_interaction_satisfied(spec, existing_inputs):
            continue
        pending.append(spec)
    return pending


def node_expansion_ready(
    record: NodeRecord,
    existing_inputs: Mapping[str, EngineeringInput | Any],
    *,
    reader: StandardsReader | None = None,
) -> bool:
    """Return True when all expansion value requirements on a node are confirmed."""
    specs = load_node_interactions(record, reader)
    for spec in specs:
        if spec.mode != InteractionMode.VALUE_RESOLUTION:
            continue
        if not spec.confirmation_required:
            continue
        if not is_interaction_satisfied(spec, existing_inputs):
            return False
    return True


def evaluate_node_interactions(
    record: NodeRecord,
    existing_inputs: Mapping[str, EngineeringInput | Any],
    *,
    phase: str = "execution",
    reader: StandardsReader | None = None,
) -> InteractionEvaluation:
    specs = load_node_interactions(record, reader)
    return evaluate_pending_interactions(specs, existing_inputs, phase=phase)


def interaction_input_from_response(
    spec: NodeInteractionSpec,
    value: Any,
    *,
    original_value: str | None = None,
    status: InputStatus = InputStatus.CONFIRMED,
    source: InputSource = InputSource.USER,
) -> EngineeringInput:
    """Build a stored EngineeringInput after the executor validates a response."""
    return EngineeringInput(
        input_id=spec.variable,
        value=value,
        unit=spec.unit,
        source=source,
        status=status,
        original_value=original_value or value,
        requires_confirmation=spec.confirmation_required,
    )


def _dedupe_by_variable(specs: list[NodeInteractionSpec]) -> list[NodeInteractionSpec]:
    seen: set[str] = set()
    merged: list[NodeInteractionSpec] = []
    for spec in specs:
        if spec.variable in seen:
            continue
        seen.add(spec.variable)
        merged.append(spec)
    return merged


def _match_numbered_option(message: str, spec: NodeInteractionSpec) -> str | None:
    """Map replies such as ``1``, ``option 2``, or ``#2`` to a canonical option."""
    if not spec.options:
        return None

    text = message.strip().lower()
    option_count = len(spec.options)
    for index in range(1, option_count + 1):
        pattern = re.compile(rf"^(?:option|choice|#)?\s*({index})\b[\s.:,-]*$")
        if pattern.match(text):
            return normalize_assumption_value(spec.options[index - 1])
    return None


def _decision_patterns(spec: NodeInteractionSpec) -> list[tuple[re.Pattern[str], str]]:
    phrases: dict[str, str] = {}
    for option in spec.options:
        canonical = normalize_assumption_value(option)
        phrases[option.lower()] = canonical
        phrases[option.lower().replace("_", " ")] = canonical

    for alias, target in spec.aliases:
        key = alias.lower().strip()
        phrases[key] = normalize_assumption_value(target)
        phrases[key.replace("_", " ")] = normalize_assumption_value(target)

    ordered = sorted(phrases.keys(), key=len, reverse=True)
    patterns: list[tuple[re.Pattern[str], str]] = []
    for phrase in ordered:
        escaped = re.escape(phrase).replace(r"\ ", r"\s+")
        pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        patterns.append((pattern, phrases[phrase]))
    return patterns


def pending_decision_interactions(
    specs: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput | Any],
) -> list[NodeInteractionSpec]:
    """Return decision interactions that still need a user selection."""
    pending: list[NodeInteractionSpec] = []
    for spec in specs:
        if spec.mode != InteractionMode.DECISION:
            continue
        if is_interaction_satisfied(spec, existing_inputs):
            continue
        pending.append(spec)
    return pending
