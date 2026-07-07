"""Presentation-layer types for Flow Guidance and composed UI output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GuidanceContext:
    """Inputs for GuidanceResolver lookup — context facts only, not presentation copy."""

    workflow_id: str
    current_phase: str | None = None
    active_node_id: str | None = None
    node_role: str | None = None
    traversal_event: str | None = None
    edge_reason: str | None = None
    task_facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != {}}


@dataclass(frozen=True)
class GuidanceBlock:
    """Traversal narration block from guidance YAML — not engineering truth."""

    block_id: str
    text: str
    kind: str = "guidance"
    source: str = "guidance"
    refs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "block_id": self.block_id,
            "kind": self.kind,
            "source": self.source,
            "text": self.text,
        }
        if self.refs:
            payload["refs"] = dict(self.refs)
        return payload


@dataclass(frozen=True)
class PresentationBlock:
    """UI-neutral structured block for CLI, API, and Desktop."""

    block_id: str
    kind: str
    source: str
    text: str | None = None
    refs: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "block_id": self.block_id,
            "kind": self.kind,
            "source": self.source,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.refs:
            result["refs"] = dict(self.refs)
        if self.payload:
            result["payload"] = dict(self.payload)
        return result


@dataclass(frozen=True)
class PresentationResponse:
    """Composed presentation output from ResponseComposer."""

    presentation_blocks: tuple[PresentationBlock, ...] = ()
    transcript_blocks: tuple[PresentationBlock, ...] = ()
    active_prompt: PresentationBlock | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "presentation_blocks": [block.to_dict() for block in self.presentation_blocks],
            "transcript_blocks": [block.to_dict() for block in self.transcript_blocks],
        }
        if self.active_prompt is not None:
            payload["active_prompt"] = self.active_prompt.to_dict()
        return payload


def append_transcript_blocks(
    prior: tuple[PresentationBlock, ...],
    new_blocks: tuple[PresentationBlock, ...],
) -> tuple[PresentationBlock, ...]:
    """Append new blocks to transcript history without mutating prior entries."""
    if not new_blocks:
        return prior
    return prior + new_blocks


def rebuild_presentation_snapshot(
    blocks: tuple[PresentationBlock, ...],
) -> tuple[PresentationBlock, ...]:
    """Return a fresh snapshot tuple from current-state block inputs."""
    return tuple(blocks)


def presentation_block_from_dict(data: dict[str, Any]) -> PresentationBlock:
    """Deserialize a presentation block from session/API JSON."""
    return PresentationBlock(
        block_id=str(data["block_id"]),
        kind=str(data["kind"]),
        source=str(data["source"]),
        text=data.get("text"),
        refs=dict(data.get("refs") or {}),
        payload=dict(data.get("payload") or {}),
    )
