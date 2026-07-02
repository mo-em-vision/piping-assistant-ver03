"""Runtime Authority Context — active governing sources for one execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AuthorityContextStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INCOMPLETE = "incomplete"
    CONFLICT_DETECTED = "conflict_detected"
    OVERRIDE_REQUIRED = "override_required"
    VALIDATED = "validated"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


@dataclass
class ActiveAuthority:
    authority_id: str
    edition: str | None = None
    role: str = "primary_design_code"
    status: str = "active"


@dataclass
class AuthorityHierarchyLevel:
    level: int
    authority_type: str
    precedence: str | None = None


@dataclass
class AuthorityConflictResolution:
    status: str = "unresolved"
    selected_authority: str | None = None
    reason: str | None = None


@dataclass
class AuthorityConflict:
    id: str
    conflict_type: str
    authorities: list[str] = field(default_factory=list)
    description: str = ""
    resolution: AuthorityConflictResolution = field(default_factory=AuthorityConflictResolution)


@dataclass
class AuthorityOverride:
    id: str
    authority: str
    affected_requirement: str
    original_requirement: str
    overridden_value: str
    approved_by: str
    reason: str
    report_required: bool = True


@dataclass
class AuthorityValidation:
    status: str = "active"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class AuthorityMetadata:
    created: str | None = None
    modified: str | None = None
    version: int = 1


@dataclass
class AuthorityContext:
    id: str
    task_id: str
    execution_context_id: str
    type: str = "authority_context"
    status: AuthorityContextStatus = AuthorityContextStatus.DRAFT
    active_authorities: list[ActiveAuthority] = field(default_factory=list)
    authority_hierarchy: list[AuthorityHierarchyLevel] = field(default_factory=list)
    applicable_paragraphs: list[str] = field(default_factory=list)
    applicable_tables: list[str] = field(default_factory=list)
    conflicts: list[AuthorityConflict] = field(default_factory=list)
    overrides: list[AuthorityOverride] = field(default_factory=list)
    validation: AuthorityValidation = field(default_factory=AuthorityValidation)
    metadata: AuthorityMetadata = field(default_factory=AuthorityMetadata)


def new_authority_context_id(*, standard_slug: str | None = None) -> str:
    if standard_slug:
        return f"AUTHCTX-{standard_slug}"
    return f"AUTHCTX-{uuid4().hex[:12]}"


def default_authority_hierarchy() -> list[AuthorityHierarchyLevel]:
    return [
        AuthorityHierarchyLevel(level=1, authority_type="regulation", precedence="highest"),
        AuthorityHierarchyLevel(level=2, authority_type="project_specification"),
        AuthorityHierarchyLevel(level=3, authority_type="company_standard"),
        AuthorityHierarchyLevel(level=4, authority_type="design_code"),
        AuthorityHierarchyLevel(level=5, authority_type="material_standard"),
        AuthorityHierarchyLevel(level=6, authority_type="reference_standard"),
    ]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def authority_context_for_execution(
    task_id: str,
    execution_context_id: str,
    *,
    context_id: str | None = None,
    status: AuthorityContextStatus = AuthorityContextStatus.DRAFT,
) -> AuthorityContext:
    now = _utc_now_iso()
    return AuthorityContext(
        id=context_id or new_authority_context_id(),
        task_id=task_id,
        execution_context_id=execution_context_id,
        status=status,
        authority_hierarchy=default_authority_hierarchy(),
        metadata=AuthorityMetadata(created=now, modified=now, version=1),
    )


def authority_context_to_dict(ctx: AuthorityContext) -> dict[str, Any]:
    from dataclasses import asdict

    payload = asdict(ctx)
    payload["status"] = ctx.status.value
    return payload


def _active_authority_from_dict(data: dict[str, Any]) -> ActiveAuthority:
    return ActiveAuthority(
        authority_id=str(data["authority_id"]),
        edition=data.get("edition"),
        role=str(data.get("role", "primary_design_code")),
        status=str(data.get("status", "active")),
    )


def _hierarchy_from_dict(data: dict[str, Any]) -> AuthorityHierarchyLevel:
    return AuthorityHierarchyLevel(
        level=int(data["level"]),
        authority_type=str(data["authority_type"]),
        precedence=data.get("precedence"),
    )


def _conflict_from_dict(data: dict[str, Any]) -> AuthorityConflict:
    resolution_data = data.get("resolution") or {}
    return AuthorityConflict(
        id=str(data["id"]),
        conflict_type=str(data.get("conflict_type", "requirement_conflict")),
        authorities=list(data.get("authorities") or []),
        description=str(data.get("description", "")),
        resolution=AuthorityConflictResolution(
            status=str(resolution_data.get("status", "unresolved")),
            selected_authority=resolution_data.get("selected_authority"),
            reason=resolution_data.get("reason"),
        ),
    )


def _override_from_dict(data: dict[str, Any]) -> AuthorityOverride:
    return AuthorityOverride(
        id=str(data["id"]),
        authority=str(data["authority"]),
        affected_requirement=str(data["affected_requirement"]),
        original_requirement=str(data["original_requirement"]),
        overridden_value=str(data["overridden_value"]),
        approved_by=str(data.get("approved_by", "user")),
        reason=str(data.get("reason", "")),
        report_required=bool(data.get("report_required", True)),
    )


def authority_context_from_dict(data: dict[str, Any]) -> AuthorityContext:
    status_raw = data.get("status", AuthorityContextStatus.DRAFT.value)
    if isinstance(status_raw, AuthorityContextStatus):
        status = status_raw
    else:
        status = AuthorityContextStatus(str(status_raw))

    validation_data = data.get("validation") or {}
    meta_data = data.get("metadata") or {}

    return AuthorityContext(
        id=str(data.get("id") or new_authority_context_id()),
        type=str(data.get("type", "authority_context")),
        task_id=str(data["task_id"]),
        execution_context_id=str(data["execution_context_id"]),
        status=status,
        active_authorities=[
            _active_authority_from_dict(item) for item in (data.get("active_authorities") or [])
        ],
        authority_hierarchy=[
            _hierarchy_from_dict(item) for item in (data.get("authority_hierarchy") or [])
        ],
        applicable_paragraphs=list(data.get("applicable_paragraphs") or []),
        applicable_tables=list(data.get("applicable_tables") or []),
        conflicts=[_conflict_from_dict(item) for item in (data.get("conflicts") or [])],
        overrides=[_override_from_dict(item) for item in (data.get("overrides") or [])],
        validation=AuthorityValidation(
            status=str(validation_data.get("status", "active")),
            warnings=list(validation_data.get("warnings") or []),
            errors=list(validation_data.get("errors") or []),
        ),
        metadata=AuthorityMetadata(
            created=meta_data.get("created"),
            modified=meta_data.get("modified"),
            version=int(meta_data.get("version", 1)),
        ),
    )
