"""Format ReportData into markdown, HTML, JSON, and PDF."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

from engine.reports.block_renderer import human_input_label, render_section_explanations
from engine.reports.equation_format import display_to_latex, equation_markdown
from engine.reports.number_format import format_report_cell, format_report_number, round_numbers_in_text
from models.report import ReportData, ReportDisplaySection

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_REPORT_CSS = """
    body { font-family: "Segoe UI", Calibri, Arial, sans-serif; margin: 2.5rem auto; max-width: 52rem; line-height: 1.6; color: #1f2937; }
    h1 { font-size: 1.75rem; color: #0f2744; border-bottom: 2px solid #cbd5e1; padding-bottom: 0.5rem; }
    h2 { font-size: 1.25rem; color: #1e3a5f; margin-top: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }
    h3 { font-size: 1.05rem; color: #334155; margin-top: 1.25rem; }
    h4 { font-size: 0.95rem; color: #475569; margin-top: 1rem; }
    p, li { font-size: 0.95rem; }
    .report-table-wrap { overflow-x: auto; margin: 1.25rem 0; border-radius: 8px; border: 1px solid #dbe3ee; box-shadow: 0 1px 2px rgba(15, 39, 68, 0.06); }
    table.report-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; background: #ffffff; }
    table.report-table th, table.report-table td { border-bottom: 1px solid #e8edf4; padding: 0.65rem 0.85rem; text-align: left; vertical-align: top; }
    table.report-table th { background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); color: #1e3a5f; font-weight: 600; }
    table.report-table tbody tr:nth-child(even) { background: #f9fbfd; }
    table.report-table tbody tr:hover { background: #f1f5fb; }
    table.report-table td:first-child { font-weight: 600; color: #334155; white-space: nowrap; }
    .equation-display { text-align: center; margin: 1.5rem 0; padding: 1.1rem 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; overflow-x: auto; }
    .equation-display .katex { font-size: 1.15rem; }
    blockquote { border-left: 4px solid #f59e0b; margin: 1rem 0; padding: 0.5rem 1rem; background: #fffbeb; color: #92400e; }
    code, pre { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; }
    code { padding: 0.1rem 0.35rem; font-family: Consolas, monospace; font-size: 0.88rem; }
    pre { padding: 0.75rem; overflow-x: auto; }
    hr { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }
    .meta { color: #64748b; font-size: 0.9rem; }
    .status-pass { color: #166534; font-weight: 600; }
    .status-incomplete { color: #b45309; font-weight: 600; }
    .status-invalid { color: #b91c1c; font-weight: 600; }
"""

_KATEX_HEAD = """
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"/>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
"""

_KATEX_BOOTSTRAP = """
<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof renderMathInElement === 'function') {
    renderMathInElement(document.body, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '\\\\[', right: '\\\\]', display: true},
        {left: '\\\\(', right: '\\\\)', display: false}
      ],
      throwOnError: false
    });
  }
});
</script>
"""


def render_markdown(report: ReportData, *, template_name: str | None = None) -> str:
    template_file = template_name or report.template_name or "generic_task_report.md"
    template = (TEMPLATES_DIR / template_file).read_text(encoding="utf-8")
    context = _template_context(report)
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def render_html(report: ReportData, *, presentation: str | None = None) -> str:
    body_source = presentation or render_markdown(report)
    body_html = _markdown_to_html(body_source)
    status_class = _status_css_class(report.status)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{escape(report.title)}</title>
  {_KATEX_HEAD}
  <style>{_REPORT_CSS}</style>
</head>
<body>
  <p class="meta"><span class="{status_class}">Status: {escape(report.status)}</span></p>
{body_html}
{_KATEX_BOOTSTRAP}
</body>
</html>
"""


def render_json(report: ReportData) -> str:
    return json.dumps(asdict(report), indent=2, default=str)


def is_valid_pdf_file(file_path: Path) -> bool:
    try:
        with file_path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def write_pdf(html_content: str, output_path: Path) -> bool:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return False

    with output_path.open("wb") as handle:
        result = pisa.CreatePDF(html_content, dest=handle, encoding="utf-8")
    if result.err or not output_path.exists():
        if output_path.exists():
            output_path.unlink()
        return False
    return is_valid_pdf_file(output_path)


def _template_context(report: ReportData) -> dict[str, str]:
    version = report.version_info
    return {
        "purpose": report.purpose or report.user_request or report.title,
        "status": report.status,
        "workflow": report.workflow or report.graph_version,
        "executive_summary": _executive_summary(report),
        "user_request": report.user_request,
        "standards_list": _standards_section(report),
        "input_data_section": _input_section(report),
        "engineering_analysis_section": _engineering_analysis_section(report),
        "section_explanations_section": _section_explanations_section(report),
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
        "report_version": version.report_version if version else "2.0",
        "graph_version": report.graph_version,
        "created_date": _format_date(version.created_date if version else ""),
    }


def _executive_summary(report: ReportData) -> str:
    workflow_label = (report.workflow or report.graph_version or "engineering").replace("_", " ")
    lines = [
        f"This report documents a **{workflow_label}** calculation.",
        f"**Overall result:** {report.status}.",
    ]
    if report.user_request:
        lines.append(f"**Design intent:** {report.user_request}")
    if report.missing_inputs:
        labels = ", ".join(human_input_label(key) for key in report.missing_inputs)
        lines.append(f"**Outstanding inputs:** {labels}.")
    if report.report_warnings:
        lines.append(
            f"**Warnings recorded:** {len(report.report_warnings)} — see the Warnings section."
        )
    key_results = _key_result_lines(report)
    if key_results:
        lines.append("**Key results:**")
        lines.extend(f"- {line}" for line in key_results)
    return "\n\n".join(lines)


def _standards_section(report: ReportData) -> str:
    if not report.standards:
        return "_No standards recorded._"
    return "\n".join(f"- {standard}" for standard in report.standards)


def _input_section(report: ReportData) -> str:
    if not report.input_entries:
        return "_No design inputs recorded._"

    lines = [
        "| Parameter | Value | Unit | Calculation value |",
        "| --- | --- | --- | --- |",
    ]
    for entry in report.input_entries:
        calc_value = entry.calculation_value
        calc_display = (
            f"{format_report_cell(calc_value)} {entry.calculation_unit or ''}".strip()
            if calc_value is not None
            else "—"
        )
        original = format_report_cell(entry.original_value)
        lines.append(
            "| "
            + " | ".join(
                [
                    human_input_label(entry.input_id),
                    original,
                    str(entry.original_unit or "—"),
                    calc_display,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _engineering_analysis_section(report: ReportData) -> str:
    if report.display_sections:
        return _render_display_sections(report.display_sections)
    if report.formula_display:
        return equation_markdown(display_to_latex(report.formula_display))
    return "_Engineering analysis pending — complete the calculation workflow._"


def _render_display_sections(sections: list[ReportDisplaySection]) -> str:
    parts: list[str] = []
    for section in sections:
        if section.title:
            parts.append(f"### {section.title}")
        parts.append(section.body_markdown)
        parts.append("")
    body = "\n\n".join(part for part in parts if part).strip()
    return body or "_No engineering analysis recorded._"


def _section_explanations_section(report: ReportData) -> str:
    if not report.section_explanations:
        return ""
    body = render_section_explanations(report.display_sections, report.section_explanations)
    if not body:
        return ""
    return f"### Engineering Notes\n\n{body}"


def _traversal_section(report: ReportData) -> str:
    if not report.traversal:
        return "_Traversal not recorded._"
    lines = ["| Step | Activity | Node |", "| --- | --- | --- |"]
    for index, step in enumerate(report.traversal, start=1):
        activity = step.title or "Executed"
        lines.append(f"| {index} | {activity} | {step.node_id} |")
    return "\n".join(lines)


def _decisions_section(report: ReportData) -> str:
    if not report.decisions:
        return "_No conditional decisions recorded._"
    lines = []
    for decision in report.decisions:
        lines.append(f"**{decision.node}** — {decision.reason}")
        if decision.condition:
            lines.append(f"- Applicability condition: `{decision.condition}`")
        if decision.result:
            lines.append(f"- Recorded result: {decision.result}")
        lines.append("")
    return "\n".join(lines).strip()


def _traceability_section(report: ReportData) -> str:
    lines = []
    for entry in report.traceability:
        paragraph = f"§{entry.paragraph}" if entry.paragraph else entry.node
        lines.append(f"**{entry.node}** ({paragraph})")
        if entry.source_text:
            lines.append(f"> {entry.source_text}")
        if entry.formula:
            latex = display_to_latex(entry.formula)
            lines.append(f"- Governing equation:\n\n{equation_markdown(latex)}")
        lines.append("")
    return "\n".join(lines).strip() or "_No traceability entries._"


def _formula_section(report: ReportData) -> str:
    if not report.formula_display:
        return "_No formula recorded._"
    return equation_markdown(display_to_latex(report.formula_display))


def _calculation_section(report: ReportData) -> str:
    if report.missing_inputs:
        labels = ", ".join(human_input_label(key) for key in report.missing_inputs)
        return f"_Calculation not executed._ Missing inputs: {labels}."
    if report.display_sections:
        return "_See Engineering Analysis section for substituted calculation and checks._"
    lines = ["- Validate design inputs", "- Convert units to SI", "- Evaluate governing equation"]
    for section in report.sections:
        if section.outputs:
            for key, value in section.outputs.items():
                lines.append(f"- {human_input_label(key)}: {value}")
    return "\n".join(lines)


def _results_section(report: ReportData) -> str:
    outputs: dict[str, Any] = {}
    for section in report.sections:
        outputs.update(section.outputs)

    result_sections = [
        section
        for section in report.display_sections
        if section.section_id.startswith("result-") or "thickness" in section.section_id
    ]
    if result_sections:
        return _render_display_sections(result_sections)

    if not outputs:
        return (
            f"**Overall status:** {report.status}\n\n"
            "_No final calculation outputs recorded._"
        )

    lines = [f"**Overall status:** {report.status}", ""]
    lines.extend(
        "| Result | Value |",
        "| --- | --- |",
    )
    for key, value in outputs.items():
        lines.append(f"| {human_input_label(key)} | {format_report_cell(value)} |")
    return "\n".join(lines)


def _limitations_section(report: ReportData) -> str:
    if not report.limitations:
        return "_No additional limitations recorded beyond the governing code paragraph._"
    return "\n".join(f"- {item}" for item in report.limitations)


def _warnings_section(report: ReportData) -> str:
    if not report.report_warnings:
        return "_No warnings recorded._"
    lines = []
    for warning in report.report_warnings:
        level = warning.level.upper() if warning.level else "WARNING"
        lines.append(f"- **{level}:** {warning.message}")
    return "\n".join(lines)


def _overrides_section(report: ReportData) -> str:
    if not report.overrides:
        return "_None recorded._"
    lines = []
    for override in report.overrides:
        lines.append(f"**{override.rule}**")
        lines.append(f"- Engineer decision: {override.user_decision}")
        lines.append(f"- Effect: {override.effect}")
        lines.append("")
    return "\n".join(lines).strip()


def _references_section(report: ReportData) -> str:
    refs: list[str] = []
    for standard in report.standards:
        refs.append(standard)
    for section in report.sections:
        if section.paragraph:
            refs.append(f"ASME B31.3 §{section.paragraph}")
    seen: set[str] = set()
    unique: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            unique.append(ref)
    return "\n".join(f"- {ref}" for ref in unique) or "_No references recorded._"


def _key_result_lines(report: ReportData) -> list[str]:
    outputs: dict[str, Any] = {}
    for section in report.sections:
        outputs.update(section.outputs)
    lines: list[str] = []
    for key in ("required_thickness", "t", "minimum_required_thickness", "t_m"):
        if key in outputs:
            lines.append(f"{human_input_label(key)}: {format_report_cell(outputs[key])}")
    return lines


def _format_date(iso_timestamp: str) -> str:
    if not iso_timestamp:
        return "—"
    normalized = iso_timestamp.replace("Z", "+00:00")
    try:
        from datetime import datetime

        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%d %B %Y")
    except ValueError:
        return iso_timestamp[:10]


def _status_css_class(status: str) -> str:
    normalized = status.upper()
    if normalized in {"PASS", "COMPLETED"}:
        return "status-pass"
    if normalized in {"INCOMPLETE", "AWAITING_INPUT"}:
        return "status-incomplete"
    if normalized in {"INVALIDATED", "FAIL"}:
        return "status-invalid"
    return "meta"


def _markdown_to_html(markdown_text: str) -> str:
    prepared = _preprocess_equations_for_html(markdown_text)
    try:
        import markdown as md

        html = md.markdown(
            prepared,
            extensions=["tables", "fenced_code", "extra"],
        )
    except ImportError:
        escaped = escape(prepared)
        return "<pre>" + escaped + "</pre>"
    return _enhance_report_html(html)


def _preprocess_equations_for_html(markdown_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        latex = match.group(1).strip()
        return f'\n\n<div class="equation-display">\\[{latex}\\]</div>\n\n'

    return re.sub(r"\$\$(.+?)\$\$", repl, markdown_text, flags=re.DOTALL)


def _enhance_report_html(html: str) -> str:
    html = re.sub(
        r"<table>",
        '<div class="report-table-wrap"><table class="report-table">',
        html,
    )
    return html.replace("</table>", "</table></div>")
