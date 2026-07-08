"""Metadata tagging and phase-aware dedupe for desktop display output blocks."""

from __future__ import annotations

from typing import Any

DISPLAY_ROLE_ACTIVATION = "activation"
DISPLAY_ROLE_PREVIEW = "preview"
DISPLAY_ROLE_EQUATION_TRACE = "equation_trace"
DISPLAY_ROLE_SUBSTITUTED = "substituted"
DISPLAY_ROLE_DERIVED = "derived"
DISPLAY_ROLE_INTRO = "intro"
DISPLAY_ROLE_CONCLUSION = "conclusion"
DISPLAY_ROLE_APPLICABILITY = "applicability"
DISPLAY_ROLE_RECOMMENDATION = "recommendation"
DISPLAY_ROLE_RESULT = "result"
DISPLAY_ROLE_WARNING = "warning"

LIFECYCLE_DURABLE = "durable"
LIFECYCLE_PREVIEW = "preview"
LIFECYCLE_VOLATILE = "volatile"

DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW = "current_equation_preview"
DISPLAY_CHANNEL_CURRENT_NODE_INTRO = "current_node_intro"

PREVIEW_TIER_ROLES = frozenset({DISPLAY_ROLE_ACTIVATION, DISPLAY_ROLE_PREVIEW})

DURABLE_DISPLAY_ROLES = frozenset(
    {
        DISPLAY_ROLE_EQUATION_TRACE,
        DISPLAY_ROLE_SUBSTITUTED,
        DISPLAY_ROLE_DERIVED,
        DISPLAY_ROLE_CONCLUSION,
        DISPLAY_ROLE_APPLICABILITY,
        DISPLAY_ROLE_RECOMMENDATION,
        DISPLAY_ROLE_RESULT,
        DISPLAY_ROLE_WARNING,
    }
)

EQUATION_TRACE_KEYS_OUTPUT = "_equation_trace_keys"
EQUATION_TRACE_ROLE_SUFFIX = "equation_trace"


def infer_display_channel(block: dict[str, Any]) -> str | None:
    explicit = block.get("display_channel")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    block_id = str(block.get("id") or "")
    if block_id.startswith("path-preview-equation-") or block_id.startswith(
        "node-activation-equation-"
    ):
        return DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW
    if block_id.startswith("path-preview-intro-"):
        return DISPLAY_CHANNEL_CURRENT_NODE_INTRO
    return None


def infer_lifecycle(block: dict[str, Any]) -> str:
    explicit = block.get("lifecycle")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    if is_volatile_block(block):
        return LIFECYCLE_VOLATILE

    role = infer_display_role(block)
    if role in DURABLE_DISPLAY_ROLES:
        return LIFECYCLE_DURABLE

    block_id = str(block.get("id") or "")
    if block_id.startswith("path-preview-equation-") or block_id.startswith(
        "node-activation-equation-"
    ):
        return LIFECYCLE_PREVIEW
    if block_id.startswith("path-preview-intro-"):
        return LIFECYCLE_PREVIEW

    if role in PREVIEW_TIER_ROLES:
        return LIFECYCLE_PREVIEW
    if role == DISPLAY_ROLE_INTRO and block_id.startswith("path-preview-intro-"):
        return LIFECYCLE_PREVIEW

    return LIFECYCLE_DURABLE


def tag_display_block(
    block: dict[str, Any],
    *,
    display_role: str,
    equation_node_id: str | None = None,
    source_node_id: str | None = None,
    display_channel: str | None = None,
    history_eligible: bool | None = None,
    volatile: bool | None = None,
) -> dict[str, Any]:
    block_id = str(block.get("id") or "")
    lifecycle = infer_lifecycle(
        {
            **block,
            "display_role": display_role,
            "equation_node_id": equation_node_id or block.get("equation_node_id"),
        }
    )
    if display_role in DURABLE_DISPLAY_ROLES:
        lifecycle = LIFECYCLE_DURABLE
    elif display_role in PREVIEW_TIER_ROLES:
        lifecycle = LIFECYCLE_PREVIEW
    elif display_role == DISPLAY_ROLE_INTRO:
        lifecycle = (
            LIFECYCLE_PREVIEW
            if block_id.startswith("path-preview-intro-")
            else LIFECYCLE_DURABLE
        )

    block["display_role"] = display_role
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


def infer_display_role(block: dict[str, Any]) -> str | None:
    explicit = block.get("display_role")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    block_id = str(block.get("id") or "")
    if block_id.startswith("node-activation-equation-"):
        return DISPLAY_ROLE_ACTIVATION
    if block_id.startswith("equation-trace-"):
        return DISPLAY_ROLE_EQUATION_TRACE
    if block_id.startswith("path-preview-equation-"):
        return DISPLAY_ROLE_PREVIEW
    if block_id in {"path-calculation-substituted-equation", "mawp-substituted-equation"}:
        return DISPLAY_ROLE_SUBSTITUTED
    if block_id == "minimum-thickness-equation":
        return DISPLAY_ROLE_DERIVED
    if block_id.startswith("path-preview-intro-"):
        return DISPLAY_ROLE_INTRO
    if block_id == "minimum-thickness-conclusion":
        return DISPLAY_ROLE_CONCLUSION
    if block_id == "thin-wall-applicability-check":
        return DISPLAY_ROLE_APPLICABILITY
    if block_id == "pipe-schedule-recommendation":
        return DISPLAY_ROLE_RECOMMENDATION
    if block_id == "planning-status":
        return None
    if str(block.get("type")) == "result":
        return DISPLAY_ROLE_RESULT
    if str(block.get("type")) == "warning" or block.get("variant") == "warning":
        return DISPLAY_ROLE_WARNING
    return None


def _preview_tier_quality_score(block: dict[str, Any]) -> int:
    role = infer_display_role(block) or ""
    score = 0
    if block.get("input_table"):
        score += 100
    if role == DISPLAY_ROLE_PREVIEW:
        score += 50
    elif role == DISPLAY_ROLE_ACTIVATION:
        score += 10
    elif str(block.get("id", "")).startswith("path-preview-equation-"):
        score += 50
    elif str(block.get("id", "")).startswith("node-activation-equation-"):
        score += 10
    return score


def _is_preview_tier_equation_bearing(block: dict[str, Any]) -> bool:
    role = infer_display_role(block)
    if role in DURABLE_DISPLAY_ROLES:
        return False
    lifecycle = infer_lifecycle(block)
    if lifecycle != LIFECYCLE_PREVIEW and role not in PREVIEW_TIER_ROLES:
        return False
    equation_node_id = str(block.get("equation_node_id") or "").strip()
    return bool(equation_node_id)


def dedupe_preview_tier_equations(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse preview/activation duplicates sharing equation_node_id; keep durable results."""
    winners: dict[str, tuple[int, int, dict[str, Any]]] = {}
    drop_indices: set[int] = set()

    for index, block in enumerate(blocks):
        if not _is_preview_tier_equation_bearing(block):
            continue

        equation_node_id = str(block.get("equation_node_id") or "").strip()
        score = _preview_tier_quality_score(block)
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


def equation_trace_block_id(source_node_id: str, equation_node_id: str) -> str:
    return f"equation-trace-{source_node_id}-{equation_node_id}"


def equation_trace_semantic_key(
    *,
    workflow_id: str,
    source_node_id: str,
    equation_node_id: str,
) -> str:
    return (
        f"{workflow_id}|{source_node_id}|{equation_node_id}|{EQUATION_TRACE_ROLE_SUFFIX}"
    )


def decode_equation_trace_semantic_key(key: str) -> tuple[str, str, str] | None:
    parts = str(key or "").split("|")
    if len(parts) != 4 or parts[3] != EQUATION_TRACE_ROLE_SUFFIX:
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


def collect_equation_trace_keys(
    task: Any,
    blocks: list[dict[str, Any]],
) -> list[str]:
    workflow_id = str(getattr(task, "outputs", {}).get("workflow") or "").strip()
    if not workflow_id:
        return list(getattr(task, "outputs", {}).get(EQUATION_TRACE_KEYS_OUTPUT) or [])

    key_set = {
        str(key).strip()
        for key in (getattr(task, "outputs", {}).get(EQUATION_TRACE_KEYS_OUTPUT) or [])
        if str(key).strip()
    }
    for block in _preview_equation_blocks(blocks):
        key_set.add(
            equation_trace_semantic_key(
                workflow_id=workflow_id,
                source_node_id=str(block["source_node_id"]),
                equation_node_id=str(block["equation_node_id"]),
            )
        )
    return sorted(key_set)


def append_equation_trace_blocks(
    blocks: list[dict[str, Any]],
    task: Any,
    reader: Any,
) -> list[dict[str, Any]]:
    """Rebuild durable equation traces from stored keys and current task state."""
    from api.equation_evaluation_display import build_equation_trace_block

    if task is None:
        return blocks

    keys = collect_equation_trace_keys(task, blocks)
    task.outputs[EQUATION_TRACE_KEYS_OUTPUT] = keys

    refreshed = [
        block
        for block in blocks
        if infer_display_role(block) != DISPLAY_ROLE_EQUATION_TRACE
    ]

    trace_blocks: list[dict[str, Any]] = []
    for key in keys:
        decoded = decode_equation_trace_semantic_key(key)
        if decoded is None:
            continue
        _workflow_id, source_node_id, _equation_node_id = decoded
        trace = build_equation_trace_block(task, reader, source_node_id)
        if trace is not None:
            trace_blocks.append(trace)

    if not trace_blocks:
        return refreshed
    return refreshed + trace_blocks


def is_volatile_block(block: dict[str, Any]) -> bool:
    if block.get("lifecycle") == LIFECYCLE_VOLATILE:
        return True
    if block.get("volatile") is True:
        return True
    if block.get("history_eligible") is False and infer_lifecycle(block) == LIFECYCLE_VOLATILE:
        return True
    block_id = str(block.get("id") or "")
    return block_id == "planning-status" or block_id.startswith("archived-prompt-")
