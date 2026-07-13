"""Tests for read-only reference chip resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.reference_links import (
    dedupe_reference_chips,
    enrich_presentation_block_dict,
    resolve_reference_chips,
    resolve_reference_chips_from_legacy_links,
)
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_enrich_display_output_uses_equation_node_id_chip(reader: StandardsReader) -> None:
    from api.reference_links import enrich_display_output_dict

    eq2 = enrich_display_output_dict(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "nomenclature_reference": {"node_id": "304.1.2-a", "label": "§304.1.2"},
        },
        reader,
    )
    eq3a = enrich_display_output_dict(
        {
            "id": "equation-asme-b313-304-1-2-eq-3a",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-2-eq-3a",
            "nomenclature_reference": {"node_id": "304.1.1-a", "label": "§304.1.1"},
        },
        reader,
    )
    assert eq2["reference_chips"][0]["label"] == "ASME B31.3 Eq. (2)"
    assert eq3a["reference_chips"][0]["label"] == "ASME B31.3 Eq. (3a)"
    assert eq2["equation_number"] == "2"
    assert eq3a["equation_number"] == "3a"


def test_node_id_ref_resolves_to_paragraph_label(reader: StandardsReader) -> None:
    chips = resolve_reference_chips({"node_id": "304.1.2-a"}, reader)
    assert len(chips) == 1
    chip = chips[0]
    assert chip["ref_type"] == "node"
    assert chip["label"].startswith("ASME B31.3 §304.1.2")
    assert chip["label"] != "304.1.2-a"
    assert chip["target"]["node_id"] == "304.1.2-a"


def test_equation_id_ref_resolves_to_equation_label(reader: StandardsReader) -> None:
    chips = resolve_reference_chips({"equation_id": "asme-b313-304-1-2-eq-3a"}, reader)
    assert len(chips) == 1
    chip = chips[0]
    assert chip["ref_type"] == "equation"
    assert "Eq." in chip["label"] or "(3a)" in chip["label"]
    assert chip["label"] != "asme-b313-304-1-2-eq-3a"


def test_unresolved_ref_uses_generic_label(reader: StandardsReader) -> None:
    chips = resolve_reference_chips({"node_id": "does-not-exist-node"}, reader)
    assert len(chips) == 1
    chip = chips[0]
    assert chip["label"] == "Standard reference"
    assert chip["label"] != chip["id"]
    assert chip.get("title") == "does-not-exist-node"


def test_dedupe_reference_chips_by_type_and_id() -> None:
    chips = dedupe_reference_chips(
        [
            {"ref_type": "node", "id": "304.1.2-a", "label": "A", "target": {"node_id": "304.1.2-a"}},
            {"ref_type": "node", "id": "304.1.2-a", "label": "B", "target": {"node_id": "304.1.2-a"}},
            {"ref_type": "equation", "id": "eq-1", "label": "Eq", "target": {"equation_id": "eq-1"}},
        ]
    )
    assert len(chips) == 2


def test_enrich_presentation_block_adds_chips_without_mutating_refs(reader: StandardsReader) -> None:
    block = {
        "block_id": "guidance-test",
        "kind": "guidance",
        "source": "guidance",
        "text": "Narration",
        "refs": {"node_id": "304.1.1-a"},
    }
    enriched = enrich_presentation_block_dict(block, reader)
    assert enriched["block_id"] == "guidance-test"
    assert enriched["refs"] == {"node_id": "304.1.1-a"}
    assert enriched["reference_chips"]
    assert enriched["reference_chips"][0]["label"].startswith("ASME B31.3 §304.1.1")


def test_legacy_reference_links_resolve_to_chips(reader: StandardsReader) -> None:
    chips = resolve_reference_chips_from_legacy_links(
        [{"node_id": "304.1.2-a", "label": "§304.1.2", "paragraph": "304.1.2-a"}],
        reader,
    )
    assert len(chips) == 1
    assert chips[0]["label"].startswith("ASME B31.3 §304.1.2")


def test_table_id_ref_resolves_to_db_table_id(reader: StandardsReader) -> None:
    chips = resolve_reference_chips({"table_id": "asme_b31.3_A-2"}, reader)
    assert len(chips) == 1
    chip = chips[0]
    assert chip["ref_type"] == "table"
    assert chip["id"] == "asme_b31.3_A-2"
    assert chip["label"] == "ASME B31.3 Table A-2"
    assert chip["target"]["table_id"] == "asme_b31.3_A-2"


def test_legacy_table_reference_chip_uses_db_table_id(reader: StandardsReader) -> None:
    chips = resolve_reference_chips_from_legacy_links(
        [
            {
                "node_id": "asme_b31.3_A-2",
                "label": "ASME B31.3 Table A-2",
                "reference_kind": "table",
            }
        ],
        reader,
    )
    assert len(chips) == 1
    assert chips[0]["id"] == "asme_b31.3_A-2"
    assert chips[0]["target"]["table_id"] == "asme_b31.3_A-2"
    assert "(para." not in chips[0]["label"]


def test_enrich_row_provenance_keeps_definition_reference_separate(reader: StandardsReader) -> None:
    from api.reference_links import enrich_row_provenance_dict

    row = enrich_row_provenance_dict(
        {
            "symbol": "S",
            "definition": "stress value for material",
            "value": "",
            "parameter_id": "PARAM-allowable-stress",
            "definition_reference": {
                "node_id": "304.1.1-b",
                "label": "§304.1.1",
                "paragraph": "304.1.1-b",
            },
            "value_reference": {
                "node_id": "asme-b313-table-A-1",
                "label": "Table A-1",
                "reference_kind": "table",
            },
        },
        reader,
    )

    definition_reference = row.get("definition_reference") or {}
    assert definition_reference.get("label") == "§304.1.1"
    row_chips = row.get("reference_chips") or []
    chip_labels = [str(chip.get("label") or "") for chip in row_chips]
    assert any("Table" in label for label in chip_labels)
    assert not any(label == "§304.1.1" for label in chip_labels)
