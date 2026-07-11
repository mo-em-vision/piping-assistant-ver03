"""Metadata tagging and phase-aware dedupe for desktop display output blocks."""

from __future__ import annotations

from typing import Any

from models.display_role import (
    DisplayRole,
    DisplayState,
    EquationContent,
    LIFECYCLE_DURABLE,
    LIFECYCLE_PREVIEW,
    LIFECYCLE_VOLATILE,
    display_state_index,
    infer_display_state,
    is_stable_equation_block_id,
    lifecycle_for_equation_state,
)

DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW = "current_equation_preview"
DISPLAY_CHANNEL_CURRENT_NODE_INTRO = "current_node_intro"

EQUATION_TRACE_KEYS_OUTPUT = "_equation_trace_keys"
EQUATION_SEMANTIC_KEY_SUFFIX = "equation"


def infer_display_channel(block: dict[str, Any]) -> str | None:
    explicit = block.get("display_channel")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    block_id = str(block.get("id") or "")
    if is_stable_equation_display_block_id(block_id):
        return None
    if block_id.startswith("path-preview-equation-") or block_id.startswith(
        "node-activation-equation-"
    ):
        return DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW
    if block_id.startswith("path-preview-intro-"):
        return DISPLAY_CHANNEL_CURRENT_NODE_INTRO
    return None


def is_stable_equation_display_block_id(block_id: str) -> bool:
    return is_stable_equation_block_id(block_id)


def infer_lifecycle(block: dict[str, Any]) -> str:
    explicit = block.get("lifecycle")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    if is_volatile_block(block):
        return LIFECYCLE_VOLATILE

    role = str(block.get("display_role") or "").strip()
    if role == DisplayRole.input_waiting.value:
        return LIFECYCLE_VOLATILE
    if role == DisplayRole.equation.value:
        return lifecycle_for_equation_state(str(block.get("display_state") or ""))

    block_id = str(block.get("id") or "")
    if is_stable_equation_display_block_id(block_id):
        state = str(block.get("display_state") or infer_display_state(block))
        return lifecycle_for_equation_state(state)
    if block_id.startswith("path-preview-equation-") or block_id.startswith(
        "node-activation-equation-"
    ):
        return LIFECYCLE_PREVIEW
    if block_id.startswith("path-preview-intro-"):
        return LIFECYCLE_PREVIEW
    if role == DisplayRole.node_intro.value and block_id.startswith("path-preview-intro-"):
        return LIFECYCLE_PREVIEW

    return LIFECYCLE_DURABLE


def tag_display_block(
    block: dict[str, Any],
    *,
    display_role: str,
    display_state: str | None = None,
    equation_content: str | None = None,
    equation_node_id: str | None = None,
    source_node_id: str | None = None,
    display_channel: str | None = None,
    history_eligible: bool | None = None,
    volatile: bool | None = None,
) -> dict[str, Any]:
    block["display_role"] = display_role
    if display_state is not None:
        block["display_state"] = display_state
    if equation_content is not None:
        block["equation_content"] = equation_content

    lifecycle = infer_lifecycle(block)
    if display_role == DisplayRole.equation.value:
        state = str(block.get("display_state") or infer_display_state(block))
        block["display_state"] = state
        block.setdefault("equation_content", EquationContent.symbolic.value)
        lifecycle = lifecycle_for_equation_state(state)
    elif display_role == DisplayRole.node_intro.value:
        block_id = str(block.get("id") or "")
        lifecycle = (
            LIFECYCLE_PREVIEW
            if block_id.startswith("path-preview-intro-")
            else LIFECYCLE_DURABLE
        )

    block["lifecycle"] = lifecycle

    if history_eligible is None:
        history_eligible = lifecycle == LIFECYCLE_DURABLE
    if volatile is None:
        volatile = lifecycle == LIFECYCLE_VOLATILE

    block["history_eligible"] = history_eligible
    block["volatile"] = volatile

    if equation_node_id:
        block["equation_node_id"] = equation_node_id
    if source_node_id:
        block["source_node_id"] = source_node_id

    resolved_channel = display_channel or infer_display_channel(block)
    if resolved_channel:
        block["display_channel"] = resolved_channel

    return block


def tag_equation_block(
    block: dict[str, Any],
    *,
    display_state: str,
    equation_content: str | None = None,
    equation_node_id: str | None = None,
    source_node_id: str | None = None,
    display_channel: str | None = None,
) -> dict[str, Any]:
    return tag_display_block(
        block,
        display_role=DisplayRole.equation.value,
        display_state=display_state,
        equation_content=equation_content,
        equation_node_id=equation_node_id,
        source_node_id=source_node_id,
        display_channel=display_channel,
    )


def infer_display_role(block: dict[str, Any]) -> str | None:
    from models.display_role import infer_display_fields_from_block, resolve_display_block

    resolved = resolve_display_block(block)
    role = str(resolved.get("display_role") or "").strip()
    return role or None


def _equation_block_quality_score(block: dict[str, Any]) -> int:
    score = 0
    if block.get("input_table"):
        score += 100
    state = str(block.get("display_state") or "")
    score += display_state_index(state) * 10
    content = str(block.get("equation_content") or "")
    if content == EquationContent.evaluated.value:
        score += 30
    elif content == EquationContent.substituted.value:
        score += 20
    if block.get("equation_display_trace"):
        score += 50
    return score


def _is_preview_tier_equation_bearing(block: dict[str, Any]) -> bool:
    if str(block.get("display_role") or "") != DisplayRole.equation.value:
        return False
    state = str(block.get("display_state") or "")
    if state == DisplayState.evaluated.value:
        return False
    lifecycle = infer_lifecycle(block)
    if lifecycle != LIFECYCLE_PREVIEW and state not in {
        DisplayState.preview.value,
        DisplayState.active.value,
    }:
        return False
    return bool(str(block.get("equation_node_id") or "").strip())


def dedupe_equation_blocks_by_node_id(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse preview-tier equation duplicates sharing equation_node_id."""
    winners: dict[str, tuple[int, int, dict[str, Any]]] = {}
    drop_indices: set[int] = set()

    for index, block in enumerate(blocks):
        if not _is_preview_tier_equation_bearing(block):
            continue

        equation_node_id = str(block.get("equation_node_id") or "").strip()
        score = _equation_block_quality_score(block)
        existing = winners.get(equation_node_id)
        if existing is None:
            winners[equation_node_id] = (index, score, block)
            continue

        winner_index, winner_score, _winner_block = existing
        if score > winner_score:
            drop_indices.add(winner_index)
            winners[equation_node_id] = (index, score, block)
        else:
            drop_indices.add(index)

    result: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if index in drop_indices:
            continue
        cleaned = dict(block)
        if cleaned.get("input_table") and cleaned.get("variables"):
            cleaned.pop("variables", None)
        result.append(cleaned)
    return result

def equation_display_block_id(equation_node_id: str) -> str:
    return f"equation-{equation_node_id}"


def equation_trace_block_id(source_node_id: str, equation_node_id: str) -> str:
    return f"equation-trace-{source_node_id}-{equation_node_id}"


def equation_trace_semantic_key(
    *,
    workflow_id: str,
    source_node_id: str,
    equation_node_id: str,
) -> str:
    return f"{workflow_id}|{source_node_id}|{equation_node_id}|{EQUATION_SEMANTIC_KEY_SUFFIX}"


def decode_equation_trace_semantic_key(key: str) -> tuple[str, str, str] | None:
    parts = str(key or "").split("|")
    if len(parts) != 4 or parts[3] not in {EQUATION_SEMANTIC_KEY_SUFFIX, "equation_trace"}:
        return None
    workflow_id, source_node_id, equation_node_id = parts[0], parts[1], parts[2]
    if not workflow_id or not source_node_id or not equation_node_id:
        return None
    return workflow_id, source_node_id, equation_node_id


def _preview_equation_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for block in blocks:
        if infer_lifecycle(block) != LIFECYCLE_PREVIEW:
            continue
        if infer_display_channel(block) != DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW:
            continue
        equation_node_id = str(block.get("equation_node_id") or "").strip()
        source_node_id = str(block.get("source_node_id") or "").strip()
        if equation_node_id and source_node_id:
            previews.append(block)
    return previews


def _evaluated_equation_trace_entries(task: Any) -> list[dict[str, str]]:
    from engine.equation.display_trace_serializer import trace_from_dict

    trace_entries = getattr(task, "outputs", {}).get("_execution_trace")
    if not isinstance(trace_entries, list):
        return []

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in trace_entries:
        if not isinstance(entry, dict):
            continue
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        display_trace = trace_from_dict(node_trace.get("equation_display_trace"))
        if display_trace is None or display_trace.status != "evaluated":
            continue
        equation_node_id = str(display_trace.equation_id or entry.get("node_id") or "").strip()
        source_node_id = str(display_trace.node_id or entry.get("node_id") or "").strip()
        if not equation_node_id or equation_node_id in seen:
            continue
        seen.add(equation_node_id)
        results.append(
            {
                "equation_node_id": equation_node_id,
                "source_node_id": source_node_id or equation_node_id,
            }
        )
    return results


def _persisted_equation_trace_entries(task: Any) -> list[dict[str, str]]:
    workflow_id = str(getattr(task, "outputs", {}).get("workflow") or "").strip()
    if not workflow_id:
        return []

    results: list[dict[str, str]] = []
    for key in getattr(task, "outputs", {}).get(EQUATION_TRACE_KEYS_OUTPUT) or []:
        decoded = decode_equation_trace_semantic_key(str(key))
        if decoded is None:
            continue
        key_workflow_id, source_node_id, equation_node_id = decoded
        if key_workflow_id != workflow_id:
            continue
        results.append(
            {
                "equation_node_id": equation_node_id,
                "source_node_id": source_node_id,
            }
        )
    return results


def _all_equation_trace_entries(task: Any) -> list[dict[str, str]]:
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for item in _evaluated_equation_trace_entries(task):
        equation_node_id = item["equation_node_id"]
        if equation_node_id in seen:
            continue
        seen.add(equation_node_id)
        merged.append(item)
    for item in _persisted_equation_trace_entries(task):
        equation_node_id = item["equation_node_id"]
        if equation_node_id in seen:
            continue
        seen.add(equation_node_id)
        merged.append(item)
    return merged


def evaluated_equation_node_ids(task: Any) -> frozenset[str]:
    return frozenset(item["equation_node_id"] for item in _evaluated_equation_trace_entries(task))


def collect_equation_trace_keys(
    task: Any,
    blocks: list[dict[str, Any]],
) -> list[str]:
    del blocks
    workflow_id = str(getattr(task, "outputs", {}).get("workflow") or "").strip()
    if not workflow_id:
        return list(getattr(task, "outputs", {}).get(EQUATION_TRACE_KEYS_OUTPUT) or [])

    key_set = {
        equation_trace_semantic_key(
            workflow_id=workflow_id,
            source_node_id=item["source_node_id"],
            equation_node_id=item["equation_node_id"],
        )
        for item in _all_equation_trace_entries(task)
    }
    return sorted(key_set)


def dedupe_competing_equation_preview_blocks(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop active-state equation blocks when preview exists for same equation_node_id."""
    preview_eq_ids = {
        str(block.get("equation_node_id") or "").strip()
        for block in blocks
        if str(block.get("display_role") or "") == DisplayRole.equation.value
        and str(block.get("display_state") or "") == DisplayState.preview.value
        and str(block.get("equation_node_id") or "").strip()
    }
    if not preview_eq_ids:
        return blocks

    result: list[dict[str, Any]] = []
    for block in blocks:
        equation_node_id = str(block.get("equation_node_id") or "").strip()
        if (
            str(block.get("display_role") or "") == DisplayRole.equation.value
            and str(block.get("display_state") or "") == DisplayState.active.value
            and equation_node_id
            and equation_node_id in preview_eq_ids
        ):
            continue
        result.append(block)
    return result


def append_equation_trace_blocks(
    blocks: list[dict[str, Any]],
    task: Any,
    reader: Any,
) -> list[dict[str, Any]]:
    from api.equation_evaluation_display import equation_display_blocks_from_trace

    if task is None:
        return blocks

    keys = collect_equation_trace_keys(task, blocks)
    task.outputs[EQUATION_TRACE_KEYS_OUTPUT] = keys

    refreshed = [
        block
        for block in blocks
        if str(block.get("type") or "") != "equation"
        or not str(block.get("equation_node_id") or "").strip()
    ]
    trace_blocks = equation_display_blocks_from_trace(task, reader)
    if not trace_blocks:
        return refreshed
    return refreshed + trace_blocks


def dedupe_blocks_by_id_prefer_richer(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    winners: dict[str, tuple[int, dict[str, Any]]] = {}
    order: list[str] = []

    def score(block: dict[str, Any]) -> int:
        value = 0
        if block.get("equation_display_trace"):
            value += 200
            trace = block.get("equation_display_trace") or {}
            if trace.get("status") == "evaluated":
                value += 100
        if block.get("input_table"):
            value += 50
        if block.get("content"):
            value += 10
        if str(block.get("display_state") or "") == DisplayState.evaluated.value:
            value += 25
        return value

    for block in blocks:
        block_id = str(block.get("id") or "").strip()
        if not block_id:
            continue
        existing = winners.get(block_id)
        if existing is None:
            winners[block_id] = (score(block), block)
            order.append(block_id)
            continue
        if score(block) >= existing[0]:
            winners[block_id] = (score(block), block)

    return [winners[block_id][1] for block_id in order if block_id in winners]


def is_volatile_block(block: dict[str, Any]) -> bool:
    if block.get("lifecycle") == LIFECYCLE_VOLATILE:
        return True
    if block.get("volatile") is True:
        return True
    if block.get("history_eligible") is False and infer_lifecycle(block) == LIFECYCLE_VOLATILE:
        return True
    block_id = str(block.get("id") or "")
    if block_id in {"planning-status", "input-waiting"}:
        return True
    return block_id.startswith("archived-prompt-")
