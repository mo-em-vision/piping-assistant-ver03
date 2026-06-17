"""AI presentation layer for reports — presentation only."""

from __future__ import annotations

from ai.agents.synthesis_agent import SynthesisAgent
from models.report import ReportData


def apply_presentation(report: ReportData, *, use_ai: bool = False) -> str | None:
    """Return AI-enhanced presentation text, or None to use deterministic formatting."""
    if not use_ai:
        return None

    agent = SynthesisAgent()
    try:
        result = agent.synthesize(report)
    except Exception:
        return None
    return result.presentation
