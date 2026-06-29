"""Structured deterministic documentation for graph nodes (Phase 7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeDocumentation:
    """Resolved documentation for one graph node."""

    node_id: str
    title: str = ""
    summary: str = ""
    description: str = ""
    before_enter: str = ""
    after_exit: str = ""
    instructions: str = ""
    warnings: tuple[str, ...] = ()
    tips: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    report_summary: str = ""
