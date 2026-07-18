"""Evaluate node assumptions before graph path expansion and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from engine.reference.paragraph_sidecar import (
    merge_paragraph_sidecar_metadata,
    parse_applicability_as_assumptions,
)
from engine.reference.workflow_sidecar import merge_workflow_sidecar_metadata
from engine.reference.standards_reader import NodeRecord, StandardsReader
from models.fact import Fact, FactClass, ValidationStatus, fact_is_expansion_ready, fact_scalar_value


@dataclass(frozen=True)
class NodeAssumptionSpec:
    """Structured assumption from node frontmatter or derived inputs."""

    id: str
    description: str
    field: str | None = None
    required_for_expansion: bool = False
    required_for_execution: bool = False
    default: Any | None = None
    requires_confirmation: bool = False
    allowed_values: tuple[str, ...] = ()
    blocks_expansion_on: tuple[str, ...] = ()
    expansion_block_message: str | None = None


@dataclass
class PathBlock:
    """A node path cannot expand because an assumption is violated."""

    node_id: str
    assumption_id: str
    field: str
    value: str
    message: str


@dataclass
class AssumptionEvaluation:
    """Result of checking assumptions along a workflow path."""

    missing_fields: list[str] = field(default_factory=list)
    field_nodes: dict[str, str] = field(default_factory=dict)
    field_questions: dict[str, str] = field(default_factory=dict)
    blocked: list[PathBlock] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked)

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_fields)


def _assumption_from_dict(item: dict[str, Any]) -> NodeAssumptionSpec | None:
    assumption_id = str(item.get("id", ""))
    if not assumption_id:
        return None
    allowed = item.get("allowed_values") or []
    blocks = item.get("blocks_expansion_on") or []
    return NodeAssumptionSpec(
        id=assumption_id,
        description=str(item.get("description", "")),
        field=str(item["field"]) if item.get("field") else None,
        required_for_expansion=bool(item.get("required_for_expansion", False)),
        required_for_execution=bool(item.get("required_for_execution", False)),
        default=item.get("default"),
        requires_confirmation=bool(item.get("requires_confirmation", False)),
        allowed_values=tuple(str(v) for v in allowed),
        blocks_expansion_on=tuple(str(v) for v in blocks),
        expansion_block_message=(
            str(item["expansion_block_message"])
            if item.get("expansion_block_message")
            else None
        ),
    )


def parse_assumptions(metadata: dict[str, Any]) -> list[NodeAssumptionSpec]:
    """Parse structured assumptions from node metadata."""
    specs: list[NodeAssumptionSpec] = []
    for item in metadata.get("assumptions", []) or []:
        if not isinstance(item, dict):
            continue
        spec = _assumption_from_dict(item)
        if spec is not None:
            specs.append(spec)
    if not specs:
        for item in parse_applicability_as_assumptions(metadata):
            spec = _assumption_from_dict(item)
            if spec is not None:
                specs.append(spec)
    return specs


def derive_execution_assumptions(record: NodeRecord) -> list[NodeAssumptionSpec]:
    """Derive execution assumptions from inputs requiring user confirmation."""
    metadata = _record_metadata(record)
    specs: list[NodeAssumptionSpec] = []
    for item in metadata.get("inputs", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("source", "")) not in ("default", "resolved"):
            continue
        if not bool(item.get("requires_confirmation", False)):
            continue
        if not bool(item.get("required", True)):
            continue
        input_id = str(item.get("id", ""))
        if not input_id:
            continue
        specs.append(
            NodeAssumptionSpec(
                id=f"confirmed_{input_id}",
                description=str(
                    item.get("description", f"Confirm default value for {input_id}")
                ),
                field=input_id,
                required_for_execution=True,
                default=item.get("default"),
                requires_confirmation=True,
            )
        )
    return specs


def _record_metadata(record: NodeRecord) -> dict[str, Any]:
    node_type = str(record.metadata.get("type", ""))
    if node_type == "workflow":
        return merge_workflow_sidecar_metadata(
            record.metadata,
            record_path=record.path,
            node_id=record.node_id,
        )
    return merge_paragraph_sidecar_metadata(
        record.metadata,
        record_path=record.path,
        node_id=record.node_id,
    )


def expansion_assumption_specs_from_metadata(metadata: dict[str, Any]) -> list[NodeAssumptionSpec]:
    """Return expansion assumption specs from compiled or merged node metadata."""
    specs = [s for s in parse_assumptions(metadata) if s.required_for_expansion]
    for item in metadata.get("interactions", []) or []:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("required_for_expansion", False)):
            continue
        field = str(item.get("variable") or item.get("field") or "").strip()
        if not field:
            continue
        specs.append(
            NodeAssumptionSpec(
                id=field,
                description=str(item.get("question") or f"Confirm {field}"),
                field=field,
                required_for_expansion=True,
            )
        )
    return specs


def expansion_assumption_fields_from_metadata(metadata: dict[str, Any]) -> list[str]:
    """Return task input fields required before a node may expand."""
    fields: list[str] = []
    for spec in expansion_assumption_specs_from_metadata(metadata):
        if spec.field and spec.field not in fields:
            fields.append(spec.field)
    return fields


def expansion_assumption_specs(record: NodeRecord) -> list[NodeAssumptionSpec]:
    return expansion_assumption_specs_from_metadata(_record_metadata(record))


class _MetadataAssumptionRecord:
    """Minimal record adapter for metadata-only assumption evaluation."""

    def __init__(self, node_id: str, metadata: dict[str, Any]) -> None:
        self.node_id = node_id
        self.metadata = metadata
        self.path = None


def evaluate_metadata_expansion_assumptions(
    metadata: dict[str, Any],
    *,
    node_id: str,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    """Check expansion assumptions declared on node metadata."""
    return _evaluate_specs(
        _MetadataAssumptionRecord(node_id, metadata),
        expansion_assumption_specs_from_metadata(metadata),
        existing_inputs or {},
        check_blocks=True,
    )


def _field_from_param_ref(param_id: str) -> str:
    pid = str(param_id or "").strip()
    if pid.startswith("PARAM-"):
        slug = pid.replace("PARAM-", "").replace("-", "_")
        aliases = {
            "weld_strength_reduction_factor_w": "weld_joint_strength_reduction_factor_W",
            "temperature_coefficient_y": "temperature_coefficient_Y",
            "material_specification": "material_grade",
            "material": "material_grade",
        }
        return aliases.get(slug, slug)
    return pid


def applicability_expansion_status(
    metadata: dict[str, Any],
    inputs: dict[str, Fact | Any],
) -> Literal["satisfied", "pending", "failed"]:
    """Classify whether node applicability matches, is undecided, or is ruled out."""
    applicability = metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return "satisfied"
    clauses = applicability.get("applies_when") or []
    if not clauses:
        return "satisfied"
    saw_pending = False
    for item in clauses:
        if not isinstance(item, dict):
            continue
        field_name = _field_from_param_ref(str(item.get("parameter") or ""))
        if not field_name:
            continue
        operator = str(item.get("operator") or "equals")
        expected = item.get("value")
        actual = field_value(field_name, inputs)
        if operator == "present":
            if actual is None:
                return "failed"
            continue
        if operator == "absent":
            if actual is not None:
                return "failed"
            continue
        if operator == "equals":
            if actual is None:
                saw_pending = True
                continue
            if normalize_assumption_value(expected) != actual:
                return "failed"
    if saw_pending:
        return "pending"
    return "satisfied"


def applicability_expansion_satisfied(
    metadata: dict[str, Any],
    inputs: dict[str, Fact | Any],
) -> bool:
    """Return True when all ``applicability.applies_when`` clauses match task inputs."""
    return applicability_expansion_status(metadata, inputs) == "satisfied"


def metadata_expansion_ready(
    metadata: dict[str, Any],
    inputs: dict[str, Fact | Any],
    *,
    node_id: str = "",
) -> bool:
    """Return True when metadata expansion assumptions are satisfied."""
    if applicability_expansion_status(metadata, inputs) == "failed":
        return False
    evaluation = evaluate_metadata_expansion_assumptions(
        metadata,
        node_id=node_id,
        existing_inputs=inputs,
    )
    return not evaluation.is_blocked and not evaluation.has_missing


def execution_assumption_specs(record: NodeRecord) -> list[NodeAssumptionSpec]:
    metadata = _record_metadata(record)
    explicit = [s for s in parse_assumptions(metadata) if s.required_for_execution]
    derived = derive_execution_assumptions(record)
    seen: set[str] = set()
    merged: list[NodeAssumptionSpec] = []
    for spec in explicit + derived:
        if spec.field and spec.field in seen:
            continue
        if spec.field:
            seen.add(spec.field)
        merged.append(spec)
    return merged


def normalize_assumption_value(value: Any) -> str:
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "internal": "internal_pressure",
        "externally_pressurized": "external_pressure",
        "external": "external_pressure",
        "internally_pressurized": "internal_pressure",
    }
    return aliases.get(text, text)


def field_value(
    field_id: str,
    existing_inputs: dict[str, Fact | Any],
) -> str | None:
    from engine.reference.parameter_keys import canonical_parameter_key, read_fact_value

    canonical = canonical_parameter_key(field_id)
    raw = existing_inputs.get(field_id)
    if raw is None and canonical != field_id:
        raw = existing_inputs.get(canonical)
    if raw is None:
        raw = read_fact_value(existing_inputs, canonical)
    if raw is None:
        return None
    if isinstance(raw, Fact):
        if raw.requires_confirmation and not fact_is_expansion_ready(raw):
            return None
        if raw.fact_class == FactClass.DEFAULT_CONFIRMED and raw.validation.status == ValidationStatus.PENDING:
            return None
        return normalize_assumption_value(fact_scalar_value(raw))
    return normalize_assumption_value(raw)


def is_field_satisfied(
    spec: NodeAssumptionSpec,
    existing_inputs: dict[str, Fact | Any],
) -> bool:
    if not spec.field:
        return True
    if spec.field not in existing_inputs:
        return False
    raw = existing_inputs[spec.field]
    if isinstance(raw, Fact):
        if raw.requires_confirmation and raw.validation.status != ValidationStatus.CONFIRMED:
            return False
        if spec.requires_confirmation and raw.fact_class == FactClass.DEFAULT_CONFIRMED:
            return raw.validation.status == ValidationStatus.CONFIRMED
    return True


def _evaluate_specs(
    record: NodeRecord,
    specs: list[NodeAssumptionSpec],
    existing_inputs: dict[str, Fact | Any],
    *,
    check_blocks: bool,
) -> AssumptionEvaluation:
    result = AssumptionEvaluation()

    for spec in specs:
        if not spec.field:
            continue

        value = field_value(spec.field, existing_inputs)
        if value is None:
            if not is_field_satisfied(spec, existing_inputs):
                if spec.field not in result.missing_fields:
                    result.missing_fields.append(spec.field)
                    result.field_nodes[spec.field] = record.node_id
                    result.field_questions[spec.field] = question_for(spec)
            continue

        if spec.allowed_values:
            normalized_allowed = {normalize_assumption_value(v) for v in spec.allowed_values}
            if value not in normalized_allowed and value not in spec.blocks_expansion_on:
                if spec.field not in result.missing_fields:
                    result.missing_fields.append(spec.field)
                    result.field_nodes[spec.field] = record.node_id
                    result.field_questions[spec.field] = (
                        f"{question_for(spec)} "
                        f"Allowed values: {', '.join(spec.allowed_values)}."
                    )
                continue

        if check_blocks:
            normalized_blocks = {normalize_assumption_value(v) for v in spec.blocks_expansion_on}
            if value in normalized_blocks:
                message = spec.expansion_block_message or (
                    f"Assumption '{spec.id}' is not satisfied for {record.node_id}: "
                    f"{spec.description}"
                )
                result.blocked.append(
                    PathBlock(
                        node_id=record.node_id,
                        assumption_id=spec.id,
                        field=spec.field,
                        value=value,
                        message=message,
                    )
                )

    return result


def evaluate_node_expansion_assumptions(
    record: NodeRecord,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    """Check expansion assumptions for a single node."""
    return _evaluate_specs(
        record,
        expansion_assumption_specs(record),
        existing_inputs or {},
        check_blocks=True,
    )


def evaluate_node_execution_assumptions(
    record: NodeRecord,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    """Check execution assumptions for a single node."""
    return _evaluate_specs(
        record,
        execution_assumption_specs(record),
        existing_inputs or {},
        check_blocks=False,
    )


def evaluate_node_assumptions(
    record: NodeRecord,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    """Check expansion assumptions for a single node (backward compatible)."""
    return evaluate_node_expansion_assumptions(record, existing_inputs=existing_inputs)


def _merge_evaluations(*evaluations: AssumptionEvaluation) -> AssumptionEvaluation:
    merged = AssumptionEvaluation()
    for evaluation in evaluations:
        for field_id in evaluation.missing_fields:
            if field_id not in merged.missing_fields:
                merged.missing_fields.append(field_id)
                merged.field_nodes[field_id] = evaluation.field_nodes[field_id]
                merged.field_questions[field_id] = evaluation.field_questions[field_id]
        merged.blocked.extend(evaluation.blocked)
    return merged


def evaluate_path_assumptions(
    node_ids: tuple[str, ...] | list[str],
    reader: StandardsReader,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
    mode: Literal["expansion", "execution"] = "expansion",
) -> AssumptionEvaluation:
    """Check assumptions for all nodes on a planned path."""
    existing = existing_inputs or {}
    evaluate = (
        evaluate_node_expansion_assumptions
        if mode == "expansion"
        else evaluate_node_execution_assumptions
    )
    parts: list[AssumptionEvaluation] = []
    for node_id in node_ids:
        record = reader.load(node_id)
        if str(record.metadata.get("type", "")) == "root":
            continue
        parts.append(evaluate(record, existing_inputs=existing))
    return _merge_evaluations(*parts)


def evaluate_path_expansion_assumptions(
    node_ids: tuple[str, ...] | list[str],
    reader: StandardsReader,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    return evaluate_path_assumptions(
        node_ids, reader, existing_inputs=existing_inputs, mode="expansion"
    )


def evaluate_path_execution_assumptions(
    node_ids: tuple[str, ...] | list[str],
    reader: StandardsReader,
    *,
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> AssumptionEvaluation:
    evaluation = evaluate_path_assumptions(
        node_ids, reader, existing_inputs=existing_inputs, mode="execution"
    )
    inputs = existing_inputs or {}
    for input_id, raw in inputs.items():
        if not isinstance(raw, Fact):
            continue
        if raw.fact_class != FactClass.DEFAULT_CONFIRMED or raw.validation.status != ValidationStatus.PENDING:
            continue
        if input_id in evaluation.missing_fields:
            continue
        evaluation.missing_fields.append(input_id)
        evaluation.field_nodes.setdefault(input_id, "")
        evaluation.field_questions.setdefault(
            input_id,
            question_for(
                NodeAssumptionSpec(
                    id=f"confirmed_{input_id}",
                    description=f"Confirm default value for {input_id}",
                    field=input_id,
                    requires_confirmation=True,
                )
            ),
        )
    return evaluation


def question_for(spec: NodeAssumptionSpec) -> str:
    if spec.id == "straight_pipe_section":
        return (
            "Is the pipe wall thickness you would like to calculate for a straight section of pipe? "
            "Non-straight sections (fittings, bends) are not yet supported."
        )
    if spec.id in {"internal_pressure_only", "pressure_design_case_case", "external_pressure_only"}:
        return (
            "Is the pipe subjected to internal or external pressure? "
            "Internal pressure design uses §304.1.2; external pressure design uses §304.1.3. "
            "Coefficients E, S, W, and Y are defined in §304.1.1-b."
        )
    if spec.description:
        return f"Please confirm: {spec.description}"
    return f"Please provide a value for {spec.field}."
