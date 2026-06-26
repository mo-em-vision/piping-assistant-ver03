"""MVP strategy §12–§13 — node validation and standard content testing."""

from __future__ import annotations

import pytest

from tests.acceptance.helpers import MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE


ACTIVE_NODES = (MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE, "pipe_wall_thickness_design")


class TestNodeValidationTesting:
    """§12 Node Validation — YAML validity, fields, dependencies, schema."""

    @pytest.mark.parametrize("node_id", ACTIVE_NODES)
    def test_active_nodes_pass_reader_validation(self, standards_reader, node_id: str) -> None:
        result = standards_reader.validate(node_id)
        assert result.passed, [issue.message for issue in result.issues]

    @pytest.mark.parametrize("node_id", (MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE))
    def test_dependency_references_resolve(self, standards_reader, node_id: str) -> None:
        record = standards_reader.load(node_id)
        for dep in record.depends_on:
            if dep.startswith("B313-"):
                assert standards_reader.find_node_path(dep) is not None


class TestStandardContentTesting:
    """§13 Standard Content — paragraph, equations, notes, limitations, references."""

    def test_b31_pack_nodes_db_is_built(self, standards_reader) -> None:
        assert standards_reader.nodes_db_available, (
            "Run python scripts/build_all_standards_dbs.py before content tests"
        )

    def test_wall_thickness_node_is_self_contained(self, standards_reader) -> None:
        record = standards_reader.load(WALL_THICKNESS_NODE)
        node_dir = record.path.parent

        assert record.metadata.get("paragraph")
        assert record.body.strip()
        assert record.metadata.get("equations")
        assert (node_dir / "equations" / "wall_thickness.md").exists()
        assert record.metadata.get("notes")
        assert (node_dir / "notes").exists()
        assert record.metadata.get("limitations")
        assert record.metadata.get("references")
        assert record.metadata.get("depends_on")

    def test_material_stress_node_has_lookup_and_table(self, standards_reader) -> None:
        record = standards_reader.load(MATERIAL_STRESS_NODE)

        assert record.body.strip()
        assert record.metadata.get("lookups")
        table_id = record.metadata["lookups"][0].get("table_id", "")
        assert table_id == "asme_b31.3_A-1"
        assert standards_reader.tables_database.get_table(table_id) is not None

    def test_equation_file_is_executable(self, standards_reader) -> None:
        equation_path = (
            standards_reader.load(WALL_THICKNESS_NODE).path.parent
            / "equations"
            / "wall_thickness.md"
        )
        text = equation_path.read_text(encoding="utf-8")
        assert "executor:" in text
        assert "steps:" in text
        assert "display:" in text
