"""Tests for ASME B31.3 workflow ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader
from engine.reference.workflow_sidecar import merge_workflow_sidecar_metadata
from engine.validation.workflow_node_validator import validate_workflow_node

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "runtime_result",
        "current_phase",
        "active_goal_id",
        "navigation",
        "assumptions",
        "interactions",
        "inputs",
        "equations",
        "nomenclature",
        "conditions",
        "provisional_assumptions",
        "engineering_intent",
        "slug",
        "goal_output",
        "purpose",
        "title",
        "documentation",
        "texts",
        "suggested_workflows",
    }
)

_EXPECTED_WORKFLOW_IDS = frozenset({"WF-PIPE-WALL-THICKNESS", "WF-MAWP"})


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workflow_dir() -> Path:
    return _project_root() / "workflows"


def test_workflow_nodes_have_required_template_fields() -> None:
    paths = sorted(_workflow_dir().glob("*.yaml"))
    assert len(paths) == 2
    ids = {split_frontmatter(path.read_text(encoding="utf-8"))[0]["id"] for path in paths}
    assert ids == _EXPECTED_WORKFLOW_IDS
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "workflow"
        assert str(meta["id"]).startswith("WF-")
        assert validate_workflow_node(meta) == [], path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r} in frontmatter"


def test_workflow_sidecars_expose_runtime_metadata() -> None:
    reader = StandardsReader(_project_root() / "knowledge" / "standards", standard="asme_b31.3")
    for workflow_id in _EXPECTED_WORKFLOW_IDS:
        record = reader.load(workflow_id)
        assert record.metadata.get("slug") or record.metadata.get("key")
        assert record.metadata.get("engineering_intent") or record.metadata.get("key")

    pipe = reader.load("WF-PIPE-WALL-THICKNESS")
    assert pipe.metadata.get("texts")

    mawp = reader.load("WF-MAWP")
    assert mawp.metadata.get("equations")
    assert mawp.metadata.get("inputs")
    assert mawp.metadata.get("nomenclature")
    assert mawp.metadata.get("provisional_assumptions")
    assert mawp.metadata.get("navigation") is None
    assert pipe.metadata.get("interactions") is None


def test_workflow_slug_resolution() -> None:
    reader = StandardsReader(_project_root() / "knowledge" / "standards", standard="asme_b31.3")
    pipe = reader.load("pipe_wall_thickness_design")
    assert pipe.node_id == "WF-PIPE-WALL-THICKNESS"
    mawp = reader.load("mawp_design")
    assert mawp.node_id == "WF-MAWP"


def test_phases_synthesize_navigation_when_sidecar_missing() -> None:
    meta = {
        "type": "workflow",
        "key": "pipe_wall_thickness_design",
        "phases": [
            {
                "key": "parameter_gathering",
                "required_parameters": ["PARAM-internal-design-gage-pressure"],
            },
        ],
    }
    merged = merge_workflow_sidecar_metadata(meta)
    navigation = merged.get("navigation") or {}
    assert "internal_design_gage_pressure" in (navigation.get("phases") or {}).get(
        "parameter_gathering", []
    )
