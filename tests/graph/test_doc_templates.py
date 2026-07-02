"""Documentation template rendering tests."""

from __future__ import annotations

from engine.graph.doc_templates import build_doc_context, render_doc_template
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, new_task, TaskStatus
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


def test_render_doc_template_substitutes_known_keys() -> None:
    text = "Design pressure {{design_pressure}} ({{P}} psi)."
    rendered = render_doc_template(
        text,
        {"design_pressure": 500, "P": 500},
    )
    assert rendered == "Design pressure 500 (500 psi)."


def test_render_doc_template_leaves_unknown_keys() -> None:
    text = "Value {{missing_key}} unchanged."
    assert render_doc_template(text, {"design_pressure": 1}) == text


def test_render_doc_template_handles_numeric_values() -> None:
    assert render_doc_template("t = {{required_thickness}} mm", {"required_thickness": 0.084}) == (
        "t = 0.084 mm"
    )


def test_build_doc_context_from_task_inputs() -> None:
    task = new_task("doc-context", status=TaskStatus.ACTIVE)
    set_fact_from_input(task, legacy_input(input_id="design_pressure",
        value=1_000_000,
        unit="Pa",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
        symbol="P",))
    context = build_doc_context(task)
    assert context["design_pressure"] == 1_000_000
    assert context["P"] == 1_000_000
