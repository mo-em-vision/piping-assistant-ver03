"""NPS-based outside diameter resolution tests."""

from __future__ import annotations

from pathlib import Path

from engine.executor.executor import execute_workflow
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from tests.acceptance.helpers import confirmed_default_inputs, internal_pressure_assumption, straight_section_assumption


def test_nps_lookup_resolves_outside_diameter_for_calculation() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "standards", standard="asme_b31.3")
    state = TaskStateManager()
    task_id = "nps-lookup-wall-thickness"
    state.create_task(task_id)

    inputs = {
        "straight_pipe_section": straight_section_assumption(),
        "pressure_loading": internal_pressure_assumption(),
        "d_input_mode": EngineeringInput(
            input_id="d_input_mode",
            value="nps_lookup",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "nominal_pipe_size": EngineeringInput(
            input_id="nominal_pipe_size",
            value="2",
            unit="dimensionless",
            source=InputSource.USER,
        ),
        "design_pressure": EngineeringInput("design_pressure", 500, "psi", InputSource.USER),
        "material": EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
        "design_temperature": EngineeringInput("design_temperature", 200, "F", InputSource.USER),
        "joint_category": EngineeringInput(
            input_id="joint_category",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "corrosion_allowance": EngineeringInput(
            input_id="corrosion_allowance",
            value=0.5,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        **confirmed_default_inputs(),
    }
    for engineering_input in inputs.values():
        state.store_input(task_id, engineering_input)

    result = execute_workflow(task_id, "pipe_wall_thickness_design", state=state, reader=reader)
    assert result.status.value == "completed"
    assert state.get_task(task_id).outputs.get("required_thickness") is not None

    trace = state.get_task(task_id).outputs["_execution_trace"]
    calc = next(entry for entry in trace if entry["node_id"] == "B313-304.1.2")
    assert calc["inputs"]["D"] > 0
    assert calc["inputs"].get("D_source") == "asme_b36.10"
