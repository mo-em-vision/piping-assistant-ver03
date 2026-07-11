"""Load-path canonicalization via legacy migration helper (tests only)."""

from __future__ import annotations

from models.display_role import DisplayRole, DisplayState, EquationContent, resolve_display_block
from tests.helpers.legacy_display_role_migration import (
    migrate_display_block_roles,
    migrate_transcript_payload,
)


def test_legacy_equation_trace_migrates_to_equation_evaluated() -> None:
    migrated = migrate_display_block_roles(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": "equation_trace",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
        }
    )
    assert migrated["display_role"] == DisplayRole.equation.value
    assert migrated["display_state"] == DisplayState.evaluated.value


def test_legacy_substituted_always_preview_substituted_content() -> None:
    migrated = migrate_display_block_roles(
        {
            "id": "path-calculation-substituted-equation",
            "type": "equation",
            "display_role": "substituted",
            "display": "t = 1.23 mm",
        }
    )
    assert migrated["display_role"] == DisplayRole.equation.value
    assert migrated["display_state"] == DisplayState.preview.value
    assert migrated["equation_content"] == EquationContent.substituted.value


def test_internal_display_role_fallback_when_display_role_absent() -> None:
    migrated = migrate_display_block_roles(
        {
            "id": "path-preview-intro-304.1.2-a",
            "type": "text",
            "internal_display_role": "intro",
            "content": "Minimum required wall thickness based on",
        }
    )
    assert migrated["display_role"] == DisplayRole.node_intro.value
    assert "internal_display_role" not in migrated


def test_canonical_display_role_not_overridden_by_internal() -> None:
    migrated = migrate_display_block_roles(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "internal_display_role": "equation_trace",
        }
    )
    assert migrated["display_role"] == DisplayRole.equation.value
    assert migrated["display_state"] == DisplayState.evaluated.value


def test_migrate_transcript_payload_legacy_role() -> None:
    payload = {"display_role": "calculation_trace", "block_id": "equation-1"}
    migrated = migrate_transcript_payload(payload)
    assert migrated["display_role"] == DisplayRole.equation.value
    assert migrated["display_state"] == DisplayState.evaluated.value


def test_resolve_display_block_production_path() -> None:
    resolved = resolve_display_block(
        {
            "id": "equation-asme-b313-304-1-2-eq-3a",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "equation_content": EquationContent.evaluated.value,
            "equation_display_trace": {"status": "evaluated"},
        }
    )
    assert resolved["lifecycle"] == "durable"
    assert resolved["display_state"] == DisplayState.evaluated.value
