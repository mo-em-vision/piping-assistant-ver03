"""AI presentation layer for reports — presentation only."""

from __future__ import annotations

from dataclasses import replace

from ai.agents.synthesis_agent import SynthesisAgent
from engine.reports.formatters import render_markdown
from models.report import ReportData


def apply_presentation(
    report: ReportData,
    *,
    use_ai: bool = False,
    base_markdown: str | None = None,
) -> str | None:
    """Return AI-enhanced presentation markdown, or None to use deterministic formatting."""
    if not use_ai:
        return None

    base = base_markdown or render_markdown(report)
    agent = SynthesisAgent()
    try:
        enhanced = agent.enhance_engineering_report(report, base)
    except Exception:
        return None

    if not enhanced.presentation:
        return None
    return enhanced.presentation


def enrich_report_with_ai(report: ReportData, *, use_ai: bool = False) -> ReportData:
    """Add section explanations and narrative improvements without changing engineering values."""
    if not use_ai:
        return report

    agent = SynthesisAgent()
    explanations: dict[str, str] = {}
    for section in report.display_sections:
        if not section.needs_explanation:
            continue
        try:
            explanation = agent.explain_section(
                {
                    "section_id": section.section_id,
                    "title": section.title,
                    "body": section.body_markdown,
                    "workflow": report.workflow,
                    "status": report.status,
                }
            )
        except Exception:
            continue
        if explanation.strip():
            explanations[section.section_id] = explanation.strip()

    if not explanations:
        return report
    return replace(report, section_explanations=explanations)
