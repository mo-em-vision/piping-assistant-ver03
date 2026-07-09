"""Paragraph presentation metadata → center-panel text blocks."""

from __future__ import annotations

from pathlib import Path

from api.paragraph_display import build_paragraph_display_block


def test_paragraph_block_uses_presentation_summary_and_reference_label(
    standards_reader,
) -> None:
    block = build_paragraph_display_block(standards_reader, "304.1.2-a")
    assert block is not None
    assert "thin-wall" in block["content"].lower() or "internal pressure" in block["content"].lower()
    assert block["id"] == "paragraph-304.1.2-a"
    assert block.get("display_role") == "engineering_reference"

    links = block.get("reference_links") or []
    assert links
    label = str(links[0].get("label") or "")
    assert label.startswith("ASME B31.3") or label.startswith("§")
    assert "304.1.2-a" not in label


def test_paragraph_presentation_from_yaml_file(project_root: Path) -> None:
    from engine.reference.standards_reader import StandardsReader

    standards_root = project_root / "knowledge" / "standards"
    reader = StandardsReader(standards_root, standard="asme_b31.3")
    block = build_paragraph_display_block(reader, "304.1.1-a")
    assert block is not None
    content = str(block.get("content") or "")
    assert "design thickness" in content.lower()
    assert "corrosion" in content.lower()
    assert "manufacturer" not in content.lower()
    title = str(block.get("title") or "")
    assert "required thickness" in title.lower()
