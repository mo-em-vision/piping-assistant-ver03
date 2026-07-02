"""Tests for runtime AuthorityContext model per template."""

from __future__ import annotations

from engine.validation.authority_context_validator import (
    validate_authority_context,
    validate_authority_context_dict,
)
from models.authority_context import (
    ActiveAuthority,
    AuthorityContextStatus,
    authority_context_for_execution,
    authority_context_from_dict,
    authority_context_to_dict,
    new_authority_context_id,
)


def test_authority_context_factory() -> None:
    ctx = authority_context_for_execution("TASK-test", "EXEC-test")
    assert ctx.id.startswith("AUTHCTX-")
    assert ctx.type == "authority_context"
    assert ctx.task_id == "TASK-test"
    assert ctx.execution_context_id == "EXEC-test"
    assert len(ctx.authority_hierarchy) == 6


def test_valid_active_context_passes() -> None:
    ctx = authority_context_for_execution("TASK-test", "EXEC-test")
    ctx.status = AuthorityContextStatus.ACTIVE
    ctx.active_authorities.append(
        ActiveAuthority(authority_id="AUTH-ASME-B31.3", edition="2024", role="primary_design_code")
    )
    assert validate_authority_context(ctx) == []


def test_active_without_authorities_fails() -> None:
    ctx = authority_context_for_execution("TASK-test", "EXEC-test")
    ctx.status = AuthorityContextStatus.ACTIVE
    issues = validate_authority_context(ctx)
    assert any("active_authority" in issue for issue in issues)


def test_json_round_trip() -> None:
    ctx = authority_context_for_execution("TASK-test", "EXEC-test", context_id=new_authority_context_id())
    ctx.status = AuthorityContextStatus.ACTIVE
    ctx.active_authorities.append(
        ActiveAuthority(authority_id="AUTH-ASME-B31.3", edition="2024")
    )
    restored = authority_context_from_dict(authority_context_to_dict(ctx))
    assert restored.id == ctx.id
    assert restored.execution_context_id == "EXEC-test"
    assert len(restored.active_authorities) == 1


def test_validate_dict_round_trip() -> None:
    ctx = authority_context_for_execution("TASK-test", "EXEC-test")
    ctx.status = AuthorityContextStatus.DRAFT
    assert validate_authority_context_dict(authority_context_to_dict(ctx)) == []
