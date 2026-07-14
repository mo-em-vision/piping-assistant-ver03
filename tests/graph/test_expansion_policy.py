"""Tests for data-driven graph expansion policy."""



from __future__ import annotations



from pathlib import Path



from engine.graph.expansion_policy import (

    collect_workflow_expansion_fields,

    dfs_collect_respecting_node_gates,

    expansion_projection_hint,

    workflow_expansion_gate_ready,

)

from engine.graph.graph_engine import GraphEngine

from engine.reference.standards_reader import StandardsReader

from tests.acceptance.helpers import straight_section_assumption

from tests.helpers.facts import facts_from_inputs





def _store(project_root: Path):

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")

    engine = GraphEngine()

    micro = engine._micro_engine(reader)

    assert micro is not None

    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)

    return micro.store, resolved





def test_collect_expansion_fields_from_authored_metadata(project_root: Path) -> None:

    store, root_id = _store(project_root)

    fields = collect_workflow_expansion_fields(store, root_id)

    assert "straight_pipe_section" in fields

    assert "pressure_loading" in fields





def test_node_assumptions_block_child_traversal(project_root: Path) -> None:

    store, root_id = _store(project_root)

    skipped: list[dict] = []

    order, _ = dfs_collect_respecting_node_gates(

        store,

        "304.1.1-a",

        inputs={},

        skipped_nodes=skipped,

    )

    assert "304.1.1-a" in order

    assert "304.1.2-a" not in order

    hint = expansion_projection_hint(store, "304.1.1-a", {})

    assert hint is not None

    assert hint["status"] == "awaiting_expansion_assumption"

    assert hint["field"] == "straight_pipe_section"





def test_node_assumptions_allow_traversal_when_satisfied(project_root: Path) -> None:

    store, root_id = _store(project_root)

    inputs = facts_from_inputs(

        {"straight_pipe_section": straight_section_assumption()},

        task_id="policy-test",

    )

    order, _ = dfs_collect_respecting_node_gates(store, "304.1.1-a", inputs=inputs)

    assert "304.1.1-a" in order

    assert expansion_projection_hint(store, "304.1.1-a", inputs) is None





def test_workflow_gate_follows_authored_fields(project_root: Path) -> None:

    store, root_id = _store(project_root)

    assert workflow_expansion_gate_ready(store, root_id, {}) is False

    inputs = facts_from_inputs(

        {"straight_pipe_section": straight_section_assumption()},

        task_id="policy-test",

    )

    assert workflow_expansion_gate_ready(store, root_id, inputs) is False





def test_internal_pressure_branch_excludes_external_pressure_nodes(project_root: Path) -> None:

    from engine.graph.lazy_expander import expand_workflow

    from tests.acceptance.helpers import internal_pressure_assumption

    from tests.helpers.facts import legacy_input

    from models.input import InputSource, InputStatus



    store, root_id = _store(project_root)

    inputs = facts_from_inputs(

        {

            "straight_pipe_section": straight_section_assumption(),

            "pressure_loading": internal_pressure_assumption(),

        },

        task_id="policy-test",

    )

    expansion = expand_workflow(store, root_id, inputs, lazy=False)

    assert "304.1.2-a" in expansion.active_nodes

    assert "304.1.3" not in expansion.active_nodes

    assert "PARAM-external-design-pressure" not in expansion.active_nodes





def test_external_pressure_branch_includes_external_design_pressure(project_root: Path) -> None:

    from engine.graph.lazy_expander import expand_workflow

    from tests.helpers.facts import legacy_input

    from models.input import InputSource, InputStatus



    store, root_id = _store(project_root)

    inputs = facts_from_inputs(

        {

            "straight_pipe_section": straight_section_assumption(),

            "pressure_loading": legacy_input(

                "pressure_loading",

                "external_pressure",

                source=InputSource.USER,

                status=InputStatus.CONFIRMED,

            ),

        },

        task_id="policy-test",

    )

    expansion = expand_workflow(store, root_id, inputs, lazy=False)

    assert "304.1.3" in expansion.active_nodes

    assert "PARAM-external-design-pressure" in expansion.active_nodes

    assert "asme-b313-304-1-2-eq-3a" not in expansion.active_nodes





def test_outside_diameter_path_selects_eq_3a_only(project_root: Path) -> None:

    from engine.graph.lazy_expander import expand_workflow

    from tests.acceptance.helpers import internal_pressure_assumption



    store, root_id = _store(project_root)

    inputs = facts_from_inputs(

        {

            "straight_pipe_section": straight_section_assumption(),

            "pressure_loading": internal_pressure_assumption(),

        },

        task_id="policy-test",

    )

    expansion = expand_workflow(store, root_id, inputs, lazy=False)

    assert "asme-b313-304-1-2-eq-3a" in expansion.active_nodes

    assert "asme-b313-304-1-2-eq-3b" not in expansion.active_nodes

    assert "asme-b313-mawp-pressure" not in expansion.active_nodes





def test_outside_diameter_path_does_not_require_inside_diameter(project_root: Path) -> None:
    from engine.graph.graph_engine import GraphEngine
    from tests.acceptance.helpers import internal_pressure_assumption
    from tests.helpers.facts import legacy_input
    from models.input import InputSource, InputStatus

    store, root_id = _store(project_root)
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
            "design_pressure": legacy_input(
                "design_pressure",
                8.0,
                "bar",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="policy-test",
    )
    required = micro.required_user_inputs(root_id, inputs)
    assert "inside_diameter" not in required
    assert "outside_diameter" in required


def test_inside_diameter_value_selects_eq_3b_only(project_root: Path) -> None:

    from engine.graph.lazy_expander import expand_workflow

    from tests.acceptance.helpers import internal_pressure_assumption

    from tests.helpers.facts import legacy_input

    from models.input import InputSource, InputStatus



    store, root_id = _store(project_root)

    inputs = facts_from_inputs(

        {

            "straight_pipe_section": straight_section_assumption(),

            "pressure_loading": internal_pressure_assumption(),

            "inside_diameter": legacy_input(

                "inside_diameter",

                100.0,

                "mm",

                source=InputSource.USER,

                status=InputStatus.CONFIRMED,

            ),

        },

        task_id="policy-test",

    )

    expansion = expand_workflow(store, root_id, inputs, lazy=False)

    assert "asme-b313-304-1-2-eq-3b" in expansion.active_nodes

    assert "asme-b313-304-1-2-eq-3a" not in expansion.active_nodes

