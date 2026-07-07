"""Render desktop display output blocks as human-readable report content."""

from __future__ import annotations

from typing import Any

from engine.reports.equation_format import display_to_latex, equation_markdown
from engine.reports.number_format import format_report_cell, round_numbers_in_text
from models.report import ReportDisplaySection

_INPUT_LABELS: dict[str, str] = {
    "internal_design_gage_pressure": "Internal design gage pressure",
    "outside_diameter": "Outside diameter",
    "material": "Material",
    "design_temperature": "Design temperature",
    "corrosion_allowance": "Corrosion allowance",
    "weld_joint_efficiency": "Weld joint efficiency (E)",
    "weld_joint_strength_reduction_factor_W": "Weld strength reduction (W)",
    "temperature_coefficient_Y": "Temperature coefficient (Y)",
    "pressure_loading": "Pressure loading",
    "straight_pipe_section": "Straight pipe section",
    "nominal_pipe_size": "Nominal pipe size",
    "material_grade": "Material",
    "joint_category": "Joint category",
    "allowable_stress": "Allowable stress (S)",
    "thickness": "Thickness",
    "report": "Report",
    "mawp": "MAWP",
}


def input_label_for_timeline(step_id: str) -> str:
    return _INPUT_LABELS.get(step_id, step_id.replace("_", " ").title())


def has_timeline_input_label(step_id: str) -> bool:
    return step_id in _INPUT_LABELS

_SECTIONS_NEEDING_EXPLANATION: frozenset[str] = frozenset(
    {
        "path-preview-equation",
        "path-calculation-substituted-equation",
        "thin-wall-applicability-check",
        "minimum-thickness-equation",
        "pipe-schedule-recommendation",
    }
)


def blocks_to_display_sections(blocks: list[dict[str, Any]]) -> list[ReportDisplaySection]:
    sections: list[ReportDisplaySection] = []
    for block in blocks:
        section = _block_to_section(block)
        if section is not None:
            sections.append(section)
    return sections


def render_blocks_markdown(blocks: list[dict[str, Any]]) -> str:
    sections = blocks_to_display_sections(blocks)
    if not sections:
        return "_No engineering analysis recorded yet._"
    parts: list[str] = []
    for section in sections:
        if section.title:
            parts.append(f"### {section.title}")
        parts.append(section.body_markdown)
        parts.append("")
    return "\n".join(parts).strip()


def render_section_explanations(
    sections: list[ReportDisplaySection],
    explanations: dict[str, str],
) -> str:
    if not explanations:
        return ""
    parts: list[str] = []
    for section in sections:
        explanation = explanations.get(section.section_id, "").strip()
        if not explanation:
            continue
        heading = section.title or "Engineering note"
        parts.append(f"#### {heading}")
        parts.append(round_numbers_in_text(explanation))
        parts.append("")
    return "\n".join(parts).strip()


def _block_to_section(block: dict[str, Any]) -> ReportDisplaySection | None:
    block_type = str(block.get("type") or "")
    block_id = str(block.get("id") or block_type or "section")

    if block_type == "text":
        return _text_section(block_id, block)
    if block_type == "equation":
        return _equation_section(block_id, block)
    if block_type == "table":
        return _table_section(block_id, block)
    if block_type == "result":
        return _result_section(block_id, block)
    if block_type == "reference":
        return _reference_section(block_id, block)
    return None


def _text_section(block_id: str, block: dict[str, Any]) -> ReportDisplaySection | None:
    content = round_numbers_in_text(str(block.get("content") or "").strip())
    suffix = str(block.get("content_suffix") or "").strip()
    title = str(block.get("title") or "").strip()
    variant = str(block.get("variant") or "body")

    reference_links = block.get("reference_links")
    if isinstance(reference_links, list) and reference_links:
        labels = [
            str(link.get("label") or link.get("node_id") or "")
            for link in reference_links
            if isinstance(link, dict)
        ]
        labels = [label for label in labels if label]
        if labels and content:
            content = f"{content} {', '.join(labels)}"
        elif labels:
            content = ", ".join(labels)

    if suffix:
        content = f"{content} {suffix}".strip() if content else suffix
    if not content:
        return None

    if variant == "warning":
        title = title or "Warning"
        content = f"> **Warning:** {content}"

    section_id = _normalize_section_id(block_id)
    return ReportDisplaySection(
        section_id=section_id,
        title=title,
        body_markdown=content,
        needs_explanation=section_id in _SECTIONS_NEEDING_EXPLANATION,
    )


def _equation_section(block_id: str, block: dict[str, Any]) -> ReportDisplaySection:
    title = str(block.get("title") or "Governing equation").strip()
    display = str(block.get("display") or "").strip()
    latex = str(block.get("content") or "").strip()
    if not latex and display:
        latex = display_to_latex(display)

    parts: list[str] = []
    if latex:
        parts.append(equation_markdown(latex))

    input_table = block.get("input_table")
    if isinstance(input_table, dict):
        table_md = _render_markdown_table(input_table)
        if table_md:
            parts.append(table_md)

    nomenclature = block.get("nomenclature_reference")
    if isinstance(nomenclature, dict):
        standard = nomenclature.get("standard")
        paragraph = nomenclature.get("paragraph")
        if standard and paragraph:
            parts.append(f"Symbols per {standard} §{paragraph}.")

    section_id = _normalize_section_id(block_id)
    return ReportDisplaySection(
        section_id=section_id,
        title=title,
        body_markdown="\n\n".join(part for part in parts if part).strip(),
        equation_latex=latex or None,
        needs_explanation=section_id in _SECTIONS_NEEDING_EXPLANATION
        or "equation" in section_id,
    )


def _table_section(block_id: str, block: dict[str, Any]) -> ReportDisplaySection:
    title = str(block.get("title") or "Data table").strip()
    columns = block.get("columns")
    rows = block.get("rows")
    body = _render_markdown_table_from_columns(columns, rows)
    return ReportDisplaySection(
        section_id=_normalize_section_id(block_id),
        title=title,
        body_markdown=body or "_No table data._",
    )


def _result_section(block_id: str, block: dict[str, Any]) -> ReportDisplaySection:
    label = str(block.get("label") or block.get("title") or "Result")
    value = block.get("value")
    unit = str(block.get("unit") or "").strip()
    status = str(block.get("status") or "info").upper()
    value_text = (
        f"{format_report_cell(value)} {unit}".strip() if value is not None else "—"
    )
    body = f"**{label}:** {value_text}  \n**Status:** {status}"
    return ReportDisplaySection(
        section_id=_normalize_section_id(block_id),
        title=label,
        body_markdown=body,
    )


def _reference_section(block_id: str, block: dict[str, Any]) -> ReportDisplaySection:
    standard = str(block.get("standard") or "").strip()
    paragraph = str(block.get("paragraph") or "").strip()
    title = str(block.get("title") or "Standard reference").strip()
    excerpt = round_numbers_in_text(str(block.get("excerpt") or block.get("content") or "").strip())
    label = f"{standard} §{paragraph}" if standard and paragraph else standard or paragraph
    body = excerpt or label or "_Reference recorded._"
    if label and excerpt:
        body = f"{excerpt} ({label})"
    return ReportDisplaySection(
        section_id=_normalize_section_id(block_id),
        title=title,
        body_markdown=body,
        needs_explanation=True,
    )


def _render_markdown_table(input_table: dict[str, Any]) -> str:
    columns = input_table.get("columns")
    rows = input_table.get("rows")
    return _render_markdown_table_from_columns(columns, rows)


def _render_markdown_table_from_columns(columns: Any, rows: Any) -> str:
    if not isinstance(columns, list) or not isinstance(rows, list) or not rows:
        return ""
    headers = [str(col.get("label") or col.get("key") or col) for col in columns]
    keys = [str(col.get("key") if isinstance(col, dict) else col) for col in columns]
    if not headers:
        return ""

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        if isinstance(row, dict):
            cells = [format_report_cell(row.get(key, "")) for key in keys]
        elif isinstance(row, list):
            cells = [format_report_cell(cell) for cell in row]
        else:
            continue
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def human_input_label(input_id: str) -> str:
    return _INPUT_LABELS.get(input_id, input_id.replace("_", " ").title())


def _normalize_section_id(block_id: str) -> str:
    return block_id
