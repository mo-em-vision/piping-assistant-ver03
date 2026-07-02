"""Runtime Fact nodes — instances of Parameters with values and provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class FactClass(str, Enum):
    USER_SUPPLIED = "user_supplied"
    CALCULATED = "calculated"
    LOOKED_UP = "looked_up"
    IMPORTED = "imported"
    DEFAULT_CONFIRMED = "default_confirmed"
    ASSUMED = "assumed"
    VALIDATED = "validated"
    DERIVED = "derived"
    SYSTEM_GENERATED = "system_generated"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    CONFLICTING = "conflicting"


class SourceType(str, Enum):
    USER_INPUT = "user_input"
    TABLE_LOOKUP = "table_lookup"
    EQUATION = "equation"
    DEFAULT_CONFIRMED = "default_confirmed"
    SYSTEM = "system"
    IMPORT = "import"


@dataclass
class NumericValue:
    amount: float | int
    unit: str


@dataclass
class CategoricalValue:
    label: str
    normalized_key: str | None = None


@dataclass
class BooleanValue:
    boolean: bool


@dataclass
class FactSource:
    source_type: SourceType
    source_id: str
    description: str | None = None
    lookup_node: str | None = None
    input_facts: list[str] = field(default_factory=list)


@dataclass
class FactProvenance:
    execution_context_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    workflow_id: str | None = None
    goal_id: str | None = None
    created_by: str | None = None
    collected_at_node: str | None = None
    collected_at_phase: str | None = None
    produced_by_node: str | None = None
    timestamp: str | None = None


@dataclass
class FactValidation:
    status: ValidationStatus = ValidationStatus.PENDING
    unit_validated: bool = False
    dimension: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class FactSupersession:
    supersedes: str | None = None
    superseded_by: str | None = None
    active: bool = True
    reason: str | None = None


@dataclass
class Fact:
    """Runtime engineering value instantiating a Parameter."""

    id: str
    parameter: str
    key: str
    fact_class: FactClass
    source: FactSource
    provenance: FactProvenance
    validation: FactValidation = field(default_factory=FactValidation)
    supersession: FactSupersession = field(default_factory=FactSupersession)
    value: Any = None
    canonical_value: NumericValue | None = None
    type: str = "fact"
    metadata: dict[str, Any] = field(default_factory=dict)
    # Legacy compatibility fields carried on facts during migration
    symbol: str | None = None
    description: str | None = None
    default: Any | None = None
    requires_confirmation: bool = False
    default_condition: str | None = None
    introduced_at_node: str | None = None
    resolved_at_node: str | None = None
    original_value: Any | None = None
    original_unit: str | None = None
    uncertainty: str | None = None


def new_fact_id(prefix: str = "FACT") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fact_is_expansion_ready(fact: Fact) -> bool:
    """Return True when a fact may satisfy graph expansion requirements."""
    return fact.validation.status in {
        ValidationStatus.CONFIRMED,
        ValidationStatus.VALIDATED,
    }


def fact_scalar_value(fact: Fact) -> Any:
    """Extract the primary scalar value from a fact."""
    if fact.value is None:
        return None
    if isinstance(fact.value, NumericValue):
        return fact.value.amount
    if isinstance(fact.value, CategoricalValue):
        return fact.value.label
    if isinstance(fact.value, BooleanValue):
        return fact.value.boolean
    if isinstance(fact.value, dict):
        if "amount" in fact.value:
            return fact.value["amount"]
        if "label" in fact.value:
            return fact.value["label"]
        if "boolean" in fact.value:
            return fact.value["boolean"]
        if "object" in fact.value:
            return fact.value["object"]
    return fact.value


def fact_unit(fact: Fact) -> str:
    """Return display unit string for a fact."""
    if isinstance(fact.value, NumericValue):
        from engine.units.unit_ids import symbol_from_unit_id

        unit = fact.value.unit
        if unit.startswith("UNIT-"):
            return symbol_from_unit_id(unit) or unit
        return unit
    if isinstance(fact.value, dict) and "unit" in fact.value:
        unit = str(fact.value["unit"])
        if unit.startswith("UNIT-"):
            from engine.units.unit_ids import symbol_from_unit_id

            return symbol_from_unit_id(unit) or unit
        return unit
    return "dimensionless"


def fact_to_dict(fact: Fact) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(fact)


def fact_from_dict(data: dict[str, Any]) -> Fact:
    """Deserialize a fact from JSON-compatible dict."""
    source_data = data.get("source") or {}
    provenance_data = data.get("provenance") or {}
    validation_data = data.get("validation") or {}
    supersession_data = data.get("supersession") or {}

    value = data.get("value")
    if isinstance(value, dict):
        if "amount" in value and "unit" in value:
            value = NumericValue(amount=value["amount"], unit=str(value["unit"]))
        elif "label" in value:
            value = CategoricalValue(
                label=str(value["label"]),
                normalized_key=value.get("normalized_key"),
            )
        elif "boolean" in value:
            value = BooleanValue(boolean=bool(value["boolean"]))

    canonical = data.get("canonical_value")
    canonical_value = None
    if isinstance(canonical, dict) and "amount" in canonical:
        canonical_value = NumericValue(
            amount=canonical["amount"],
            unit=str(canonical.get("unit", "")),
        )

    source_type = source_data.get("source_type", SourceType.SYSTEM.value)
    if isinstance(source_type, SourceType):
        st = source_type
    else:
        st = SourceType(str(source_type))

    fact_class = data.get("fact_class", FactClass.USER_SUPPLIED.value)
    if isinstance(fact_class, FactClass):
        fc = fact_class
    else:
        fc = FactClass(str(fact_class))

    val_status = validation_data.get("status", ValidationStatus.PENDING.value)
    if isinstance(val_status, ValidationStatus):
        vs = val_status
    else:
        vs = ValidationStatus(str(val_status))

    return Fact(
        id=str(data["id"]),
        type=str(data.get("type", "fact")),
        parameter=str(data.get("parameter", "")),
        key=str(data.get("key", data.get("input_id", ""))),
        fact_class=fc,
        value=value,
        canonical_value=canonical_value,
        source=FactSource(
            source_type=st,
            source_id=str(source_data.get("source_id", "")),
            description=source_data.get("description"),
            lookup_node=source_data.get("lookup_node"),
            input_facts=list(source_data.get("input_facts") or []),
        ),
        provenance=FactProvenance(
            execution_context_id=provenance_data.get("execution_context_id"),
            task_id=provenance_data.get("task_id"),
            project_id=provenance_data.get("project_id"),
            workflow_id=provenance_data.get("workflow_id"),
            goal_id=provenance_data.get("goal_id"),
            created_by=provenance_data.get("created_by"),
            collected_at_node=provenance_data.get("collected_at_node"),
            collected_at_phase=provenance_data.get("collected_at_phase"),
            produced_by_node=provenance_data.get("produced_by_node"),
            timestamp=provenance_data.get("timestamp"),
        ),
        validation=FactValidation(
            status=vs,
            unit_validated=bool(validation_data.get("unit_validated", False)),
            dimension=validation_data.get("dimension"),
            warnings=list(validation_data.get("warnings") or []),
            errors=list(validation_data.get("errors") or []),
        ),
        supersession=FactSupersession(
            supersedes=supersession_data.get("supersedes"),
            superseded_by=supersession_data.get("superseded_by"),
            active=bool(supersession_data.get("active", True)),
            reason=supersession_data.get("reason"),
        ),
        metadata=dict(data.get("metadata") or {}),
        symbol=data.get("symbol"),
        description=data.get("description"),
        default=data.get("default"),
        requires_confirmation=bool(data.get("requires_confirmation", False)),
        default_condition=data.get("default_condition"),
        introduced_at_node=data.get("introduced_at_node"),
        resolved_at_node=data.get("resolved_at_node"),
        original_value=data.get("original_value"),
        original_unit=data.get("original_unit"),
        uncertainty=data.get("uncertainty"),
    )


def build_numeric_fact(
    *,
    key: str,
    parameter: str,
    amount: float | int,
    unit: str,
    fact_class: FactClass,
    source: FactSource,
    provenance: FactProvenance,
    fact_id: str | None = None,
    canonical_amount: float | int | None = None,
    canonical_unit: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.CONFIRMED,
    dimension: str | None = None,
    **extra: Any,
) -> Fact:
    unit_id = unit if unit.startswith("UNIT-") else _legacy_unit_to_id(unit)
    canonical_value = None
    if canonical_amount is not None and canonical_unit:
        canonical_value = NumericValue(amount=canonical_amount, unit=canonical_unit)
    return Fact(
        id=fact_id or new_fact_id(),
        parameter=parameter,
        key=key,
        fact_class=fact_class,
        value=NumericValue(amount=amount, unit=unit_id),
        canonical_value=canonical_value,
        source=source,
        provenance=provenance,
        validation=FactValidation(
            status=validation_status,
            unit_validated=canonical_value is not None,
            dimension=dimension,
        ),
        **extra,
    )


def build_categorical_fact(
    *,
    key: str,
    parameter: str,
    label: str,
    normalized_key: str | None,
    fact_class: FactClass,
    source: FactSource,
    provenance: FactProvenance,
    fact_id: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.CONFIRMED,
    **extra: Any,
) -> Fact:
    return Fact(
        id=fact_id or new_fact_id(),
        parameter=parameter,
        key=key,
        fact_class=fact_class,
        value=CategoricalValue(label=label, normalized_key=normalized_key),
        source=source,
        provenance=provenance,
        validation=FactValidation(status=validation_status),
        **extra,
    )


def build_boolean_fact(
    *,
    key: str,
    parameter: str,
    value: bool,
    fact_class: FactClass,
    source: FactSource,
    provenance: FactProvenance,
    fact_id: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.CONFIRMED,
    **extra: Any,
) -> Fact:
    return Fact(
        id=fact_id or new_fact_id(),
        parameter=parameter,
        key=key,
        fact_class=fact_class,
        value=BooleanValue(boolean=value),
        source=source,
        provenance=provenance,
        validation=FactValidation(status=validation_status),
        **extra,
    )


def fact_from_user_submission(
    *,
    key: str,
    value: Any,
    unit: str = "dimensionless",
    task_id: str,
    parameter: str | None = None,
    workflow_id: str | None = None,
    collected_at_node: str | None = None,
    collected_at_phase: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.CONFIRMED,
) -> Fact:
    from engine.reference.param_resolver import resolve_parameter_id

    param_id = parameter or resolve_parameter_id(key)
    provenance = FactProvenance(
        task_id=task_id,
        workflow_id=workflow_id,
        collected_at_node=collected_at_node,
        collected_at_phase=collected_at_phase,
        created_by="user",
        timestamp=_utc_now_iso(),
    )
    source = FactSource(
        source_type=SourceType.USER_INPUT,
        source_id="USER",
        description="Provided by user during parameter collection.",
    )
    if isinstance(value, bool):
        return build_boolean_fact(
            key=key,
            parameter=param_id,
            value=value,
            fact_class=FactClass.USER_SUPPLIED,
            source=source,
            provenance=provenance,
            validation_status=validation_status,
            symbol=symbol,
            description=description,
        )
    if isinstance(value, (int, float)):
        return build_numeric_fact(
            key=key,
            parameter=param_id,
            amount=value,
            unit=unit,
            fact_class=FactClass.USER_SUPPLIED,
            source=source,
            provenance=provenance,
            validation_status=validation_status,
            symbol=symbol,
            description=description,
        )
    return build_categorical_fact(
        key=key,
        parameter=param_id,
        label=str(value),
        normalized_key=_normalize_key(str(value)),
        fact_class=FactClass.USER_SUPPLIED,
        source=source,
        provenance=provenance,
        validation_status=validation_status,
        symbol=symbol,
        description=description,
    )


def proposed_default_fact(
    key: str,
    value: Any,
    *,
    task_id: str,
    unit: str = "dimensionless",
    parameter: str | None = None,
    default: Any | None = None,
    default_condition: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    introduced_at_node: str | None = None,
) -> Fact:
    from engine.reference.param_resolver import resolve_parameter_id

    param_id = parameter or resolve_parameter_id(key)
    provenance = FactProvenance(
        task_id=task_id,
        collected_at_node=introduced_at_node,
        created_by="system",
        timestamp=_utc_now_iso(),
    )
    source = FactSource(
        source_type=SourceType.DEFAULT_CONFIRMED,
        source_id=introduced_at_node or "SYSTEM",
        description=default_condition or "System-proposed default awaiting confirmation.",
    )
    fact = fact_from_user_submission(
        key=key,
        value=value,
        unit=unit,
        task_id=task_id,
        parameter=param_id,
        collected_at_node=introduced_at_node,
        symbol=symbol,
        description=description,
        validation_status=ValidationStatus.PENDING,
    )
    fact.fact_class = FactClass.DEFAULT_CONFIRMED
    fact.source = source
    fact.default = default if default is not None else value
    fact.requires_confirmation = True
    fact.default_condition = default_condition
    fact.introduced_at_node = introduced_at_node
    return fact


def pending_parameter_fact(
    key: str,
    *,
    task_id: str,
    unit: str = "dimensionless",
    parameter: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    introduced_at_node: str | None = None,
) -> Fact:
    from engine.reference.param_resolver import resolve_parameter_id

    param_id = parameter or resolve_parameter_id(key)
    return Fact(
        id=new_fact_id(),
        parameter=param_id,
        key=key,
        fact_class=FactClass.SYSTEM_GENERATED,
        value=None,
        source=FactSource(source_type=SourceType.SYSTEM, source_id="SYSTEM"),
        provenance=FactProvenance(
            task_id=task_id,
            collected_at_node=introduced_at_node,
            created_by="system",
            timestamp=_utc_now_iso(),
        ),
        validation=FactValidation(status=ValidationStatus.PENDING),
        symbol=symbol,
        description=description,
        introduced_at_node=introduced_at_node,
    )


def _legacy_unit_to_id(unit: str) -> str:
    from engine.units.unit_ids import unit_id_from_legacy_symbol

    return unit_id_from_legacy_symbol(unit) or "UNIT-dimensionless"


def _normalize_key(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    return slug.strip("_")
