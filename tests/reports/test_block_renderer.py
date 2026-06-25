"""Tests for display-block to report rendering."""

from __future__ import annotations

from engine.reports.block_renderer import blocks_to_display_sections, render_blocks_markdown


def test_render_equation_and_table_blocks_separately() -> None:
    blocks = [
        {
            "id": "equation-1",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
            "content": "t = \\frac{PD}{2(SEW + PY)}",
            "input_table": {
                "columns": [
                    {"key": "symbol", "label": "Symbol"},
                    {"key": "value", "label": "Value"},
                ],
                "rows": [{"symbol": "P", "value": "8.0 bar"}],
            },
        },
    ]

    markdown = render_blocks_markdown(blocks)
    sections = blocks_to_display_sections(blocks)

    assert "$$" in markdown
    assert "\\frac" in markdown
    assert "| Symbol | Value |" in markdown
    assert "**Equation:**" not in markdown
    assert "8.000 bar" in markdown
    assert len(sections) == 1
    assert sections[0].equation_latex is not None
