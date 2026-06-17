"""Format ReportData into markdown, HTML, JSON, and PDF."""

from __future__ import annotations

import json
from dataclasses import asdict
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from models.report import ReportData

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_markdown(report: ReportData, *, template_name: str = "calculation_report.md") -> str:
    template = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")
    context = _template_context(report)
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def render_html(report: ReportData, *, presentation: str | None = None) -> str:
    body_source = presentation or render_markdown(report)
    body_html = _markdown_to_html(body_source)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{escape(report.title)}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem; line-height: 1.5; }}
    h1, h2, h3 {{ color: #1a365d; }}
    pre, code {{ background: #f5f5f5; padding: 0.2rem 0.4rem; }}
    .warning {{ color: #b45309; font-weight: bold; }}
  </style>
</head>
<body>
{body_html}
</body>
</html>
"""


def render_json(report: ReportData) -> str:
    return json.dumps(asdict(report), indent=2, default=str)


def write_pdf(html_content: str, output_path: Path) -> bool:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return False

    with output_path.open("wb") as handle:
        result = pisa.CreatePDF(html_content, dest=handle, encoding="utf-8")
    return not result.err


def _template_context(report: ReportData) -> dict[str, str]:
    version = report.version_info
    return {
        "purpose": report.title,
        "task_id": report.task_id,
        "status": report.status,
        "workflow": report.workflow,
        "executive_notes": _executive_notes(report),
        "user_request": report.user_request,
        "standards_list": "\n".join(f"- {standard}" for standard in report.standards) or "-",
        "input_data_section": _input_section(report),
        "traversal_section": _traversal_section(report),
        "decisions_section": _decisions_section(report),
        "traceability_section": _traceability_section(report),
        "formula_section": _formula_section(report),
        "calculation_section": _calculation_section(report),
        "results_section": _results_section(report),
        "limitations_section": _limitations_section(report),
        "warnings_section": _warnings_section(report),
        "overrides_section": _overrides_section(report),
        "conclusion": report.conclusion,
        "references_section": _references_section(report),
        "report_version": version.report_version if version else "1.0",
        "graph_version": report.graph_version,
        "created_date": version.created_date if version else "",
    }


def _executive_notes(report: ReportData) -> str:
    lines = []
    if report.missing_inputs:
        lines.append(f"- Missing inputs: {', '.join(report.missing_inputs)}")
    if report.report_warnings:
        lines.append(f"- Warnings: {len(report.report_warnings)}")
    return "\n".join(lines) or "- No additional executive notes."


def _input_section(report: ReportData) -> str:
    if not report.input_entries:
        return "_No user inputs recorded._"
    lines = []
    for entry in report.input_entries:
        lines.append(f"### {entry.input_id}")
        lines.append(f"- Original: {entry.original_value} {entry.original_unit}")
        if entry.calculation_value is not None:
            lines.append(
                f"- Calculation: {entry.calculation_value} {entry.calculation_unit or ''}".strip()
            )
    return "\n".join(lines)


def _traversal_section(report: ReportData) -> str:
    if not report.traversal:
        return "_Traversal not recorded._"
    return "\n".join(
        f"{index}. {step.node_id} ({step.title or 'node'})"
        for index, step in enumerate(report.traversal, start=1)
    )


def _decisions_section(report: ReportData) -> str:
    if not report.decisions:
        return "_No conditional decisions recorded._"
    lines = []
    for decision in report.decisions:
        lines.append(f"### {decision.node}")
        lines.append(f"- Reason: {decision.reason}")
        if decision.condition:
            lines.append(f"- Condition: `{decision.condition}`")
        if decision.result:
            lines.append(f"- Result: {decision.result}")
    return "\n".join(lines)


def _traceability_section(report: ReportData) -> str:
    lines = []
    for entry in report.traceability:
        lines.append(f"### {entry.node} — §{entry.paragraph or ''}")
        if entry.source_text:
            lines.append(f"> {entry.source_text}")
    return "\n".join(lines) or "_No traceability entries._"


def _formula_section(report: ReportData) -> str:
    if not report.formula_display:
        return "_No formula recorded._"
    return f"`{report.formula_display}`"


def _calculation_section(report: ReportData) -> str:
    if report.missing_inputs:
        return (
            "_Calculation not executed._\n\n"
            f"Missing inputs: {', '.join(report.missing_inputs)}"
        )
    lines = ["- Validate inputs", "- Convert units to SI", "- Evaluate wall thickness formula"]
    for section in report.sections:
        if section.outputs:
            lines.append(f"- Outputs recorded: {section.outputs}")
    return "\n".join(lines)


def _results_section(report: ReportData) -> str:
    outputs: dict[str, Any] = {}
    for section in report.sections:
        outputs.update(section.outputs)
    if not outputs:
        return f"Status: {report.status}\n\n_No final calculation outputs recorded._"
    lines = [f"Status: {report.status}"]
    for key, value in outputs.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _limitations_section(report: ReportData) -> str:
    if not report.limitations:
        return "_None recorded._"
    return "\n".join(f"- {item}" for item in report.limitations)


def _warnings_section(report: ReportData) -> str:
    if not report.report_warnings:
        return "_None_"
    return "\n".join(f"- **WARNING:** {warning.message}" for warning in report.report_warnings)


def _overrides_section(report: ReportData) -> str:
    if not report.overrides:
        return "_None_"
    lines = []
    for override in report.overrides:
        lines.append(f"### {override.rule}")
        lines.append(f"- Original rule: {override.original_rule}")
        lines.append(f"- User decision: {override.user_decision}")
        lines.append(f"- Effect: {override.effect}")
    return "\n".join(lines)


def _references_section(report: ReportData) -> str:
    refs = list(report.standards)
    for section in report.sections:
        if section.paragraph:
            refs.append(f"§{section.paragraph} ({section.node})")
    return "\n".join(f"- {ref}" for ref in refs)


def _markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown as md

        return md.markdown(markdown_text, extensions=["tables", "fenced_code"])
    except ImportError:
        escaped = escape(markdown_text)
        return "<pre>" + escaped + "</pre>"
