"""Read-time projection for flow_guidance transcript blocks.

Stored transcript history is immutable. Legacy title/description pairs are
normalized to a synthetic workflow_intro view only during display assembly.
"""

from __future__ import annotations

from typing import Any

from models.display_role import DisplayRole


def _block_id(raw: dict[str, Any]) -> str:
    return str(raw.get("block_id") or "").strip()


def _display_role(raw: dict[str, Any]) -> str:
    payload = raw.get("payload")
    if isinstance(payload, dict):
        role = str(payload.get("display_role") or "").strip()
        if role:
            return role
    block_id = _block_id(raw)
    if block_id.startswith("workflow-title-"):
        return DisplayRole.title.value
    if block_id.startswith("workflow-description-"):
        return DisplayRole.workflow_description.value
    if block_id.startswith("workflow-intro-"):
        return DisplayRole.workflow_intro.value
    return ""


def _slug_from_prefixed_id(block_id: str, prefix: str) -> str | None:
    if block_id.startswith(prefix):
        slug = block_id[len(prefix) :].strip()
        return slug or None
    return None


def combine_workflow_intro_text(title: str, description: str) -> str:
    title_text = str(title or "").strip()
    description_text = str(description or "").strip()
    if title_text and description_text:
        return f"{title_text}\n\n{description_text}"
    return title_text or description_text


def _synthetic_workflow_intro_block(
    workflow_slug: str,
    *,
    title_text: str,
    description_text: str,
) -> dict[str, Any]:
    combined = combine_workflow_intro_text(title_text, description_text)
    payload: dict[str, Any] = {"display_role": DisplayRole.workflow_intro.value}
    if title_text.strip():
        payload["title"] = title_text.strip()
    return {
        "block_id": f"workflow-intro-{workflow_slug}",
        "kind": "text",
        "source": "workflow_node",
        "text": combined,
        "payload": payload,
    }


def project_transcript_blocks_for_display(
    transcript_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project stored transcript blocks for scroll/report display without mutation."""
    if not transcript_blocks:
        return []

    title_by_slug: dict[str, dict[str, Any]] = {}
    description_by_slug: dict[str, dict[str, Any]] = {}
    native_intro_slugs: set[str] = set()

    for raw in transcript_blocks:
        if not isinstance(raw, dict):
            continue
        block_id = _block_id(raw)
        if not block_id:
            continue
        intro_slug = _slug_from_prefixed_id(block_id, "workflow-intro-")
        if intro_slug:
            native_intro_slugs.add(intro_slug)
            continue
        title_slug = _slug_from_prefixed_id(block_id, "workflow-title-")
        if title_slug:
            title_by_slug[title_slug] = raw
            continue
        description_slug = _slug_from_prefixed_id(block_id, "workflow-description-")
        if description_slug:
            description_by_slug[description_slug] = raw

    consumed_ids: set[str] = set()
    synthetic_by_slug: dict[str, dict[str, Any]] = {}

    for slug in native_intro_slugs:
        title_block = title_by_slug.get(slug)
        description_block = description_by_slug.get(slug)
        if title_block:
            consumed_ids.add(_block_id(title_block))
        if description_block:
            consumed_ids.add(_block_id(description_block))

    legacy_slugs = set(title_by_slug) | set(description_by_slug)
    for slug in sorted(legacy_slugs - native_intro_slugs):
        title_block = title_by_slug.get(slug)
        description_block = description_by_slug.get(slug)
        title_text = str(title_block.get("text") or "") if title_block else ""
        description_text = str(description_block.get("text") or "") if description_block else ""
        if not title_text.strip() and not description_text.strip():
            continue
        synthetic_by_slug[slug] = _synthetic_workflow_intro_block(
            slug,
            title_text=title_text,
            description_text=description_text,
        )
        if title_block:
            consumed_ids.add(_block_id(title_block))
        if description_block:
            consumed_ids.add(_block_id(description_block))

    projected: list[dict[str, Any]] = []
    inserted_synthetic: set[str] = set()

    for raw in transcript_blocks:
        if not isinstance(raw, dict):
            continue
        block_id = _block_id(raw)
        if block_id in consumed_ids:
            slug = (
                _slug_from_prefixed_id(block_id, "workflow-title-")
                or _slug_from_prefixed_id(block_id, "workflow-description-")
            )
            if slug and slug in synthetic_by_slug and slug not in inserted_synthetic:
                projected.append(synthetic_by_slug[slug])
                inserted_synthetic.add(slug)
            continue
        projected.append(raw)

    return projected
