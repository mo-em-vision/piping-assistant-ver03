"""Canonical display roles, equation states, and center-panel ordering."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class DisplayRole(StrEnum):
    workflow_intro = "workflow_intro"
    scope_assumption = "scope_assumption"
    branch_narration = "branch_narration"
    ask_archive = "ask_archive"
    answer_archive = "answer_archive"
    engineering_reference = "engineering_reference"
    paragraph_context = "paragraph_context"
    input_context = "input_context"
    node_intro = "node_intro"
    equation = "equation"
    applicability = "applicability"
    warning = "warning"
    result_summary = "result_summary"
    lookup_table_recommendation = "lookup_table_recommendation"
    next_workflows = "next_workflows"


class DisplayState(StrEnum):
    preview = "preview"
    active = "active"
    evaluated = "evaluated"


class EquationContent(StrEnum):
    symbolic = "symbolic"
    substituted = "substituted"
    evaluated = "evaluated"


class ResultKind(StrEnum):
    workflow = "workflow"
    calculation = "calculation"
    recommendation = "recommendation"


DISPLAY_ROLE_ORDER: tuple[DisplayRole, ...] = (
    DisplayRole.workflow_intro,
    DisplayRole.scope_assumption,
    DisplayRole.branch_narration,
    DisplayRole.ask_archive,
    DisplayRole.answer_archive,
    DisplayRole.engineering_reference,
    DisplayRole.paragraph_context,
    DisplayRole.input_context,
    DisplayRole.node_intro,
    DisplayRole.equation,
    DisplayRole.applicability,
    DisplayRole.warning,
    DisplayRole.result_summary,
    DisplayRole.lookup_table_recommendation,
    DisplayRole.next_workflows,
)

DISPLAY_STATE_ORDER: tuple[DisplayState, ...] = (
    DisplayState.active,
    DisplayState.preview,
    DisplayState.evaluated,
)

LIFECYCLE_DURABLE = "durable"
LIFECYCLE_PREVIEW = "preview"
LIFECYCLE_VOLATILE = "volatile"


def is_canonical_display_role(role: str | None) -> bool:
    if not role or not str(role).strip():
        return False
    try:
        DisplayRole(str(role).strip())
        return True
    except ValueError:
        return False


def validate_display_block(block: dict[str, Any]) -> bool:
    role = str(block.get("display_role") or "").strip()
    if role and not is_canonical_display_role(role):
        return False
    if role == DisplayRole.equation.value:
        state = str(block.get("display_state") or "").strip()
        content = str(block.get("equation_content") or "").strip()
        if state:
            try:
                DisplayState(state)
            except ValueError:
                return False
        if content:
            try:
                EquationContent(content)
            except ValueError:
                return False
    return True


def report_role_index(display_role: str | None) -> int:
    role = str(display_role or "").strip()
    if not role:
        return len(DISPLAY_ROLE_ORDER)
    try:
        return DISPLAY_ROLE_ORDER.index(DisplayRole(role))
    except ValueError:
        return len(DISPLAY_ROLE_ORDER)


def display_state_index(display_state: str | None) -> int:
    state = str(display_state or "").strip()
    if not state:
        return len(DISPLAY_STATE_ORDER)
    try:
        return DISPLAY_STATE_ORDER.index(DisplayState(state))
    except ValueError:
        return len(DISPLAY_STATE_ORDER)


def lifecycle_for_equation_state(display_state: str | None) -> str:
    state = str(display_state or "").strip()
    if state == DisplayState.evaluated.value:
        return LIFECYCLE_DURABLE
    if state in {DisplayState.preview.value, DisplayState.active.value}:
        return LIFECYCLE_PREVIEW
    return LIFECYCLE_DURABLE


def is_stable_equation_block_id(block_id: str) -> bool:
    block_id = str(block_id or "").strip()
    if not block_id.startswith("equation-"):
        return False
    if block_id.startswith("equation-trace-"):
        return False
    return True


def infer_equation_content(block: dict[str, Any]) -> str:
    explicit = str(block.get("equation_content") or "").strip()
    if explicit in {item.value for item in EquationContent}:
        return explicit

    trace = block.get("equation_display_trace")
    if isinstance(trace, dict):
        if trace.get("status") == "evaluated" or trace.get("result"):
            return EquationContent.evaluated.value
        if trace.get("substituted_latex"):
            return EquationContent.substituted.value

    if block.get("substituted_latex"):
        return EquationContent.substituted.value

    content = str(block.get("content") or block.get("display") or "")
    if block.get("input_table") and not content.strip():
        return EquationContent.symbolic.value

    if block.get("result") or (isinstance(trace, dict) and trace.get("result")):
        return EquationContent.evaluated.value

    return EquationContent.symbolic.value


def infer_display_state(block: dict[str, Any]) -> str:
    explicit = str(block.get("display_state") or "").strip()
    if explicit in {item.value for item in DisplayState}:
        return explicit

    lifecycle = str(block.get("lifecycle") or "").strip()
    block_id = str(block.get("id") or "")

    if lifecycle == LIFECYCLE_DURABLE and is_stable_equation_block_id(block_id):
        return DisplayState.evaluated.value

    trace = block.get("equation_display_trace")
    if isinstance(trace, dict) and trace.get("status") == "evaluated":
        return DisplayState.evaluated.value

    if block_id.startswith("node-activation-equation-"):
        return DisplayState.active.value

    if block_id.startswith("path-preview-equation-"):
        return DisplayState.preview.value

    if is_stable_equation_block_id(block_id):
        if block.get("input_table") or block.get("result"):
            return DisplayState.evaluated.value
        return DisplayState.preview.value

    if block_id.startswith("equation-trace-"):
        return DisplayState.evaluated.value

    return DisplayState.preview.value


def infer_display_fields_from_block(block: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(block)
    block_id = str(block.get("block_id") or block.get("id") or "")

    payload = block.get("payload")
    if isinstance(payload, dict):
        payload_role = str(payload.get("display_role") or "").strip()
        if payload_role and not resolved.get("display_role"):
            resolved["display_role"] = payload_role

    if block_id.startswith("workflow-intro-"):
        resolved["display_role"] = DisplayRole.workflow_intro.value
    elif block_id.startswith("result-summary-"):
        resolved["display_role"] = DisplayRole.result_summary.value
    elif block_id.startswith("archived-ask-"):
        resolved["display_role"] = DisplayRole.ask_archive.value
    elif block_id.startswith("archived-answer-"):
        resolved["display_role"] = DisplayRole.answer_archive.value
    elif block_id.startswith("next-workflows-"):
        resolved["display_role"] = DisplayRole.next_workflows.value
    elif block_id.startswith("guidance-"):
        resolved["display_role"] = DisplayRole.branch_narration.value
    elif block_id.startswith("path-preview-intro-"):
        resolved["display_role"] = DisplayRole.node_intro.value
    elif block_id.startswith("table-lookup-"):
        resolved["display_role"] = (
            DisplayRole.lookup_table_recommendation.value
            if block.get("highlight_row")
            else DisplayRole.engineering_reference.value
        )
    elif block_id.startswith("paragraph-"):
        role = str(resolved.get("display_role") or "").strip()
        if role != DisplayRole.paragraph_context.value:
            resolved["display_role"] = DisplayRole.engineering_reference.value
    elif block_id.startswith("validation-"):
        resolved["display_role"] = DisplayRole.applicability.value
    elif (
        block_id.startswith("equation-")
        or block_id.startswith("path-preview-equation-")
        or block_id.startswith("node-activation-equation-")
    ):
        resolved["display_role"] = DisplayRole.equation.value
    elif str(block.get("type")) == "warning" or block.get("variant") == "warning":
        resolved["display_role"] = DisplayRole.warning.value

    if resolved.get("display_role") == DisplayRole.equation.value:
        resolved.setdefault("display_state", infer_display_state(resolved))
        resolved.setdefault("equation_content", infer_equation_content(resolved))
        resolved["lifecycle"] = lifecycle_for_equation_state(resolved.get("display_state"))

    return resolved


def resolve_display_block(block: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(block, dict):
        return block

    role = str(block.get("display_role") or "").strip()
    if role and is_canonical_display_role(role):
        resolved = dict(block)
    elif role:
        logger.warning("Unknown display_role on block %s: %s", block.get("id"), role)
        resolved = dict(block)
    else:
        resolved = infer_display_fields_from_block(block)

    if resolved.get("display_role") == DisplayRole.equation.value:
        resolved.setdefault("display_state", infer_display_state(resolved))
        resolved.setdefault("equation_content", infer_equation_content(resolved))
        resolved["lifecycle"] = lifecycle_for_equation_state(resolved.get("display_state"))

    resolved.pop("internal_display_role", None)
    return resolved


def sort_blocks_by_report_role(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int, str]:
        index, block = item
        role_index = report_role_index(str(block.get("display_role") or ""))
        state_index = (
            display_state_index(str(block.get("display_state") or ""))
            if block.get("display_role") == DisplayRole.equation.value
            else 0
        )
        block_id = str(block.get("id") or block.get("block_id") or "")
        return (role_index, state_index, index, block_id)

    indexed = list(enumerate(blocks))
    indexed.sort(key=sort_key)
    return [block for _, block in indexed]
