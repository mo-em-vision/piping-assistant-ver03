"""One-off profiler for submit_input operation breakdown."""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

os.environ.setdefault("DEV_INSPECTION_ENABLED", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.desktop_service import DesktopApiService  # noqa: E402
from config.loader import CLIConfig  # noqa: E402
from engine.inspection.operation_tracker import operations_snapshot  # noqa: E402


def _build_service() -> DesktopApiService:
    sessions_dir = Path(tempfile.mkdtemp(prefix="profile-submit-"))
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=ROOT / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def _next_parameter(state: dict) -> str | None:
    ask = state.get("current_ask") or {}
    param = ask.get("parameter_id")
    if isinstance(param, str) and param.strip():
        return param.strip()
    for item in state.get("parameters", []):
        if item.get("status") != "confirmed":
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def _value_for(param: str) -> tuple[object, str | None]:
    if param == "straight_pipe_section":
        return True, "dimensionless"
    if param == "pressure_loading":
        return "internal_pressure", None
    if param == "material_grade":
        return "SA-106B", None
    if param == "design_pressure":
        return 8.0, "bar"
    if param == "design_temperature":
        return 38.0, "degC"
    if "pressure" in param:
        return 2.0, "MPa"
    if "temperature" in param:
        return 100.0, "degC"
    if param in {"nominal_pipe_size", "outside_diameter"}:
        return 2.0, "in"
    if param in {"weld_joint_efficiency", "weld_joint_strength_reduction_factor_W", "temperature_coefficient_Y"}:
        return 1.0, None
    return 1.0, "dimensionless"


def main() -> None:
    service = _build_service()
    project = service.create_project("Profile Submit Input")
    session_id = service.activate_project(project["id"])["session_id"]
    state = service.create_task(workflow_id="pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]
    print(f"task_id={task_id}")

    for step in range(6):
        param = _next_parameter(state)
        if not param:
            print("no more parameters")
            break
        value, unit = _value_for(param)
        before_recent = {op["id"] for op in operations_snapshot()["recent"]}
        t0 = time.perf_counter()
        state = service.submit_input(
            task_id,
            parameter=param,
            value=value,
            unit=unit,
            session_id=session_id,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        new_ops = [
            op
            for op in operations_snapshot()["recent"]
            if op["id"] not in before_recent
        ]
        print(f"\n--- step {step + 1}: submit {param!r} — wall {elapsed_ms:.0f} ms ---")
        for op in reversed(new_ops):
            duration = op.get("duration_ms")
            dur_s = f"{duration:.1f} ms" if duration is not None else "?"
            print(f"  {op.get('category', ''):12} {op.get('name', ''):45} {dur_s:>12}  ({op.get('status')})")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
