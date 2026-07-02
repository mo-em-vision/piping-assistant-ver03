"""Acceptance criteria §4 and §5 — standards coverage and node structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_paths import list_standard_packs


class TestStandardsCoverage:
    """§4 Standards Coverage — ASME B31.3 and extensible architecture."""

    def test_asme_b31_3_pack_is_available(self, project_root: Path) -> None:
        packs = list_standard_packs(project_root / "knowledge" / "standards")
        slugs = [slug for slug, _path in packs]
        assert "asme_b31.3" in slugs

    def test_b31_3_has_paragraph_calculation_and_table_assets(self, standards_reader) -> None:
        definition_node = standards_reader.load("B313-304.1.1")
        wall_node = standards_reader.load("B313-304.1.2")
        stress_node = standards_reader.load("B313-table-A-1")

        assert paragraph_reference(definition_node.metadata) == "304.1.1"
        assert definition_node.metadata.get("type") == "definition"
        assert definition_node.metadata.get("nomenclature")
        c_entry = next(
            item for item in definition_node.metadata["nomenclature"] if item["symbol"] == "c"
        )
        assert c_entry.get("defaults")
        assert c_entry["defaults"][0]["value"] == 0.5
        d_entry = next(
            item for item in definition_node.metadata["nomenclature"] if item["symbol"] == "D"
        )
        assert any(
            ref.get("standard") == "asme_b36.10" for ref in d_entry.get("references", [])
        )
        assert paragraph_reference(wall_node.metadata) == "304.1.2"
        assert wall_node.metadata.get("type") == "calculation"
        assert stress_node.metadata.get("type") == "equation"
        assert stress_node.metadata.get("kind") == "lookup"
        assert standards_reader.tables_db_path.is_file()
        assert standards_reader.load_table("A-1")["materials"]

        equation_path = (
            standards_reader.pack_root
            / "nodes"
            / "equation"
            / "asme_b313_304_1_2_wall_thickness.yaml"
        )
        assert equation_path.exists()

    def test_future_standard_architecture_supports_multiple_packs(self, project_root: Path) -> None:
        packs = list_standard_packs(project_root / "knowledge" / "standards")
        slugs = {slug for slug, _path in packs}
        assert len(slugs) >= 3
        assert "asme_b31.3" in slugs


class TestNodeAcceptanceCriteria:
    """§5 Node Acceptance Criteria — required metadata on active workflow nodes."""

    @pytest.mark.parametrize(
        "node_id,required_fields",
        [
            ("pipe_wall_thickness_design", ("id", "type", "depends_on", "report")),
            ("B313-304.1.1", ("id", "nomenclature", "report")),
            ("B313-304.1.2", ("id", "inputs", "outputs", "depends_on", "conditions", "equations", "report")),
            ("B313-table-A-1", ("id", "inputs", "outputs", "lookups")),
        ],
    )
    def test_active_nodes_contain_required_fields(
        self,
        standards_reader,
        node_id: str,
        required_fields: tuple[str, ...],
    ) -> None:
        metadata = standards_reader.load(node_id).metadata
        for field in required_fields:
            assert field in metadata, f"{node_id} missing {field}"

    def test_calculation_node_has_optional_traceability_fields(self, standards_reader) -> None:
        metadata = standards_reader.load("B313-304.1.2").metadata
        assert metadata.get("limitations")
        assert metadata.get("notes")
        assert metadata.get("references")

    @pytest.mark.parametrize("node_id", ("B313-304.1.1", "B313-304.1.2", "B313-table-A-1"))
    def test_active_nodes_pass_schema_validation(self, standards_reader, node_id: str) -> None:
        result = standards_reader.validate(node_id)
        assert result.passed, [issue.message for issue in result.issues]

    def test_302_3_5_has_structured_subsections(self, standards_reader) -> None:
        record = standards_reader.load("B313-302.3.5")
        subsection_ids = {item["id"] for item in record.metadata.get("subsections", [])}
        assert subsection_ids == {"a", "b", "c", "d", "e", "f"}

        subsection_e = standards_reader.load_subsection("B313-302.3.5", "e")
        assert subsection_e.paragraph == "302.3.5(e)"
        assert subsection_e.metadata["output"]["symbol"] == "W"
        assert "Weld Joint Strength Reduction Factor" in subsection_e.body
