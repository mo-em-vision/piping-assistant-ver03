"""Acceptance criteria §4 and §5 — standards coverage and node structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_paths import list_standard_packs


class TestStandardsCoverage:
    """§4 Standards Coverage — ASME B31.3 and extensible architecture."""

    def test_asme_b31_3_pack_is_available(self, project_root: Path) -> None:
        packs = list_standard_packs(project_root / "standards")
        slugs = [slug for slug, _path in packs]
        assert "asme_b31.3" in slugs

    def test_b31_3_has_paragraph_calculation_and_table_assets(self, standards_reader) -> None:
        wall_node = standards_reader.load("B313-304.1.1")
        stress_node = standards_reader.load("B313-material-stress")

        assert wall_node.metadata.get("paragraph") == "304.1.1"
        assert wall_node.metadata.get("type") == "calculation"
        assert stress_node.metadata.get("type") == "lookup"
        assert (standards_reader.pack_root / "tables" / "material_allowable_stress.yaml").exists()

        formula_path = wall_node.path.parent / "formulas" / "wall_thickness.md"
        assert formula_path.exists()

    def test_future_standard_architecture_supports_multiple_packs(self, project_root: Path) -> None:
        packs = list_standard_packs(project_root / "standards")
        slugs = {slug for slug, _path in packs}
        assert len(slugs) >= 4
        assert "asme_b31.3" in slugs


class TestNodeAcceptanceCriteria:
    """§5 Node Acceptance Criteria — required metadata on active workflow nodes."""

    @pytest.mark.parametrize(
        "node_id,required_fields",
        [
            ("pipe_wall_thickness_design", ("id", "type", "depends_on", "report")),
            ("B313-304.1.1", ("id", "inputs", "outputs", "depends_on", "conditions", "report")),
            ("B313-material-stress", ("id", "inputs", "outputs", "depends_on", "report")),
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
        metadata = standards_reader.load("B313-304.1.1").metadata
        assert metadata.get("limitations")
        assert metadata.get("notes")
        assert metadata.get("references")

    @pytest.mark.parametrize("node_id", ("B313-304.1.1", "B313-material-stress"))
    def test_active_nodes_pass_schema_validation(self, standards_reader, node_id: str) -> None:
        result = standards_reader.validate(node_id)
        assert result.passed, [issue.message for issue in result.issues]
