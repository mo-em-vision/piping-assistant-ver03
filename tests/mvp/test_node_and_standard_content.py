"""MVP strategy §12–§13 — node validation and standard content testing."""

from __future__ import annotations

import pytest

from engine.graph.param_priority import normalize_require_ids
from tests.acceptance.helpers import MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE


ACTIVE_NODES = (MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE, "pipe_wall_thickness_design")


class TestNodeValidationTesting:
    """§12 Node Validation — YAML validity, fields, dependencies, schema."""

    @pytest.mark.parametrize("node_id", ACTIVE_NODES)
    def test_active_nodes_pass_reader_validation(self, standards_reader, node_id: str) -> None:
        result = standards_reader.validate(node_id)
        assert result.passed, [issue.message for issue in result.issues]

    def test_wall_thickness_equation_requires_stress_parameter(self, standards_reader) -> None:
        record = standards_reader.load(WALL_THICKNESS_NODE)
        requires = normalize_require_ids(record.metadata.get("requires"))
        assert "B313-param-S" in requires

    def test_material_stress_lookup_resolves(self, standards_reader) -> None:
        record = standards_reader.load(MATERIAL_STRESS_NODE)
        assert record.metadata.get("type") == "equation"
        assert record.metadata.get("kind") == "lookup"
        assert record.metadata.get("table_id") == "asme_b31.3_A-1"


class TestStandardContentTesting:
    """§13 Standard Content — paragraph, equations, notes, limitations, references."""

    def test_b31_pack_nodes_db_is_built(self, standards_reader) -> None:
        assert standards_reader.nodes_db_available, (
            "Run python scripts/build_all_standards_dbs.py before content tests"
        )

    def test_wall_thickness_node_is_self_contained(self, standards_reader) -> None:
        record = standards_reader.load(WALL_THICKNESS_NODE)
        assert record.metadata.get("type") == "equation"
        assert record.metadata.get("sympy")
        assert record.metadata.get("requires")
        assert record.metadata.get("calculates")

    def test_material_stress_node_has_lookup_and_table(self, standards_reader) -> None:
        record = standards_reader.load(MATERIAL_STRESS_NODE)
        assert record.metadata.get("type") == "equation"
        assert record.metadata.get("kind") == "lookup"
        table_id = str(record.metadata.get("table_id", ""))
        assert table_id == "asme_b31.3_A-1"
        assert standards_reader.tables_database.get_table(table_id) is not None

    def test_equation_node_uses_sympy_execution(self, standards_reader) -> None:
        record = standards_reader.load(WALL_THICKNESS_NODE)
        assert "t" in str(record.metadata.get("sympy", ""))
        assert "execution_function" not in record.metadata
