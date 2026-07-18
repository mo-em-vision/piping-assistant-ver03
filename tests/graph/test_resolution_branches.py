"""Tests for PARAM resolution branch metadata and graph resolution."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.lookup_parameter_resolution import parameter_resolution_for_parameter
from engine.graph.resolution_branches import (
    apply_resolution_branch_defaults,
    default_resolution_branch_id,
    resolution_branch_fact_key,
    resolution_branches_from_metadata,
)
from engine.reference.parameter_composer_spec import build_composer_parameter_spec
from engine.reference.standards_markdown import split_frontmatter
from models.input import InputSource, InputStatus
from tests.helpers.facts import facts_from_inputs, legacy_input


def test_outside_diameter_has_two_resolution_branches() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "global"
        / "parameters"
        / "nodes"
        / "PARAM-outside-diameter.yaml"
    )
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    branches = resolution_branches_from_metadata(meta)
    assert [branch["id"] for branch in branches] == ["nps_lookup", "direct_od"]
    nested = meta.get("metadata") or {}
    assert nested.get("default_value") == "nps_lookup"


def test_default_resolution_branch_id_reads_param_default_value() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "global"
        / "parameters"
        / "nodes"
        / "PARAM-outside-diameter.yaml"
    )
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert default_resolution_branch_id(meta) == "nps_lookup"


def test_apply_resolution_branch_defaults_seeds_branch_fact() -> None:
    from engine.state.state_manager import TaskStateManager
    from models.fact import fact_scalar_value

    manager = TaskStateManager()
    task = manager.create_task("resolution-branch-default")
    assert apply_resolution_branch_defaults(task) is True
    branch = task.fact_store.active_fact("outside_diameter__resolution_branch")
    assert branch is not None
    assert fact_scalar_value(branch) == "nps_lookup"


def test_outside_diameter_branch_choice_before_selection() -> None:
    reader_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(reader_root, standard="asme_b31.3")
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    resolution = parameter_resolution_for_parameter(micro.store, "PARAM-outside-diameter", inputs={})
    assert resolution is not None
    assert resolution["method"] == "branch_choice"
    assert resolution["anchor"] == "outside_diameter"


def test_outside_diameter_composer_spec_is_resolution_branch() -> None:
    spec = build_composer_parameter_spec("outside_diameter")
    assert spec["type"] == "resolution_branch"
    ui = spec["resolution_ui"]
    assert ui["branch_fact_key"] == resolution_branch_fact_key("outside_diameter")
    assert [branch["id"] for branch in ui["branches"]] == ["nps_lookup", "direct_od"]
    assert ui["default_value"] == "nps_lookup"


def test_mawp_required_inputs_start_with_outside_diameter_anchor() -> None:
    from engine.reference.standards_reader import StandardsReader
    from models.input import InputSource, InputStatus
    from tests.graph.conftest import MAWP_ROOT
    from tests.helpers.facts import facts_from_inputs, legacy_input

    reader = StandardsReader(
        Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": __import__(
                "tests.acceptance.helpers", fromlist=["straight_section_assumption"]
            ).straight_section_assumption(),
            "pressure_design_case": __import__(
                "tests.acceptance.helpers", fromlist=["internal_pressure_assumption"]
            ).internal_pressure_assumption(),
            "wall_thickness_basis": legacy_input(
                "wall_thickness_basis",
                "nominal_schedule",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="mawp-branch-anchor",
    )
    engine = GraphEngine()
    missing = engine.required_user_inputs(
        MAWP_ROOT,
        reader,
        existing_inputs=set(inputs.keys()),
        task_inputs=inputs,
    )
    assert "outside_diameter" in missing
    assert "nominal_pipe_size" not in missing


def test_direct_od_branch_requires_outside_diameter_value() -> None:
    from engine.reference.standards_reader import StandardsReader
    from tests.graph.conftest import MAWP_ROOT, mawp_gate_open_inputs

    reader = StandardsReader(
        Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    engine = GraphEngine()
    inputs = mawp_gate_open_inputs()
    inputs.update(
        facts_from_inputs(
            {
                "outside_diameter__resolution_branch": legacy_input(
                    "outside_diameter__resolution_branch",
                    "direct_od",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="direct-od-branch",
        )
    )
    missing = engine.required_user_inputs(
        MAWP_ROOT,
        reader,
        existing_inputs=set(inputs.keys()),
        task_inputs=inputs,
    )
    assert "outside_diameter" in missing
    assert "nominal_pipe_size" not in missing
