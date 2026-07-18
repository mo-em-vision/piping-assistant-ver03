"""Compare profile_submit_input key metrics against a saved baseline."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.profile_submit_input import (  # noqa: E402
    _build_service,
    _next_parameter,
    _run_traced,
    _span_duration,
    _value_for,
)
from engine.reference.standards_reader import StandardsReader  # noqa: E402
from engine.state.task_facts import deactivate_fact  # noqa: E402
from models.task import TaskStatus  # noqa: E402
from tests.acceptance.helpers import run_completed_workflow  # noqa: E402


def _span_present(spans: list[dict], name: str) -> bool:
    return any(span.get("name") == name for span in spans)


def _parse_key_metrics(text: str, label: str) -> dict[str, float]:
    metrics: dict[str, float] = {}
    block = None
    for line in text.splitlines():
        if line.startswith(f"=== Key metrics ({label})"):
            block = []
            continue
        if block is not None:
            if line.startswith("==="):
                break
            if line.startswith("submit_input total"):
                metrics["submit_input_total"] = float(re.search(r"([\d.]+)", line).group(1))
            elif line.startswith("goal_tree_refresh skipped"):
                metrics["goal_tree_refresh_skipped"] = 1.0
            elif line.startswith("goal_tree_refresh ran"):
                metrics["goal_tree_refresh"] = float(re.search(r"([\d.]+)", line).group(1))
            else:
                match = re.match(r"^(\S+)\s+([\d.]+)\s+ms", line.strip())
                if match:
                    metrics[match.group(1)] = float(match.group(2))
    return metrics


def _run_corrosion_profile(service, session_id: str) -> dict[str, float] | None:
    """Profile post-calculation corrosion_allowance submit (structure unchanged)."""
    reader = StandardsReader(
        ROOT / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    manager = service._load_manager()
    state = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]
    run_completed_workflow(manager, reader, task_id)
    task = manager.get_task(task_id)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    deactivate_fact(task, "corrosion_allowance")
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    manager.replace_task(task_id, task)
    from api.workflow_bootstrap import refresh_task_planning

    refresh_task_planning(
        task,
        reader,
        propose_defaults=False,
        allow_lightweight_refresh=False,
    )
    manager.replace_task(task_id, task)
    service._save_manager(manager, session_id)

    def _submit() -> dict:
        return service.submit_input(
            task_id,
            parameter="corrosion_allowance",
            value=3.0,
            unit="mm",
            session_id=session_id,
        )

    _, trace = _run_traced("submit_input", task_id, _submit)
    if trace is None:
        return None
    spans = list(trace.get("spans") or [])
    return {
        "submit_input_total": float(trace.get("total_duration_ms") or 0.0),
        "task_state": _span_duration(spans, "task_state") or 0.0,
        "refresh_task_planning": _span_duration(spans, "refresh_task_planning") or 0.0,
        "goal_tree_refresh": _span_duration(spans, "goal_tree_refresh") or 0.0,
        "planning_refresh_skipped": 1.0 if _span_present(spans, "planning_refresh_skipped") else 0.0,
    }


def _run_profile(*, steps: int) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    service = _build_service()
    project = service.create_project("Profile Phase Report")
    session_id = service.activate_project(project["id"])["session_id"]
    state = service.create_task(workflow_id="pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]

    pressure_trace = None
    corrosion_trace = None

    for _step in range(max(1, steps)):
        param = _next_parameter(state)
        if not param:
            break
        value, unit = _value_for(param)

        def _submit() -> dict:
            return service.submit_input(
                task_id,
                parameter=param,
                value=value,
                unit=unit,
                session_id=session_id,
            )

        state, trace = _run_traced("submit_input", task_id, _submit)
        if trace and param == "pressure_design_case":
            pressure_trace = trace
        if trace and param == "corrosion_allowance":
            corrosion_trace = trace

    pressure_metrics = None
    corrosion_metrics = None
    if pressure_trace is not None:
        spans = list(pressure_trace.get("spans") or [])
        pressure_metrics = {
            "submit_input_total": float(pressure_trace.get("total_duration_ms") or 0.0),
            "task_state": _span_duration(spans, "task_state") or 0.0,
            "refresh_task_planning": _span_duration(spans, "refresh_task_planning") or 0.0,
            "goal_tree_refresh": _span_duration(spans, "goal_tree_refresh") or 0.0,
            "engineering_plan_projection": _span_duration(spans, "engineering_plan_projection") or 0.0,
            "display_output_projection": _span_duration(spans, "display_output_projection") or 0.0,
            "planning_refresh_skipped": 1.0 if _span_present(spans, "planning_refresh_skipped") else 0.0,
        }
    if corrosion_trace is not None:
        spans = list(corrosion_trace.get("spans") or [])
        corrosion_metrics = {
            "submit_input_total": float(corrosion_trace.get("total_duration_ms") or 0.0),
            "task_state": _span_duration(spans, "task_state") or 0.0,
            "refresh_task_planning": _span_duration(spans, "refresh_task_planning") or 0.0,
            "goal_tree_refresh": _span_duration(spans, "goal_tree_refresh") or 0.0,
            "planning_refresh_skipped": 1.0 if _span_present(spans, "planning_refresh_skipped") else 0.0,
        }
    return pressure_metrics, corrosion_metrics


def _print_comparison(title: str, before: dict[str, float], after: dict[str, float]) -> None:
    print(f"\n=== {title} ===")
    print(f"{'metric':28} {'before':>10} {'after':>10} {'delta':>10}")
    keys = sorted(set(before) | set(after))
    for key in keys:
        b = before.get(key, 0.0)
        a = after.get(key, 0.0)
        delta = a - b
        print(f"{key:28} {b:10.1f} {a:10.1f} {delta:+10.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run profile and compare to baseline file.")
    parser.add_argument("--baseline", type=Path, default=ROOT / "profile_before.txt")
    parser.add_argument("--steps", type=int, default=2, help="Submit steps (default: 2 = through pressure_design_case)")
    parser.add_argument("--corrosion", action="store_true", help="Also profile post-calc corrosion_allowance submit")
    parser.add_argument("--output", type=Path, help="Write report to file (stdout still printed)")
    args = parser.parse_args()

    baseline_text = args.baseline.read_text(encoding="utf-8", errors="replace")
    before_pressure = _parse_key_metrics(baseline_text, "pressure_design_case submit")
    if not before_pressure:
        before_pressure = {
            "submit_input_total": 4255.6,
            "task_state": 1932.5,
            "engineering_plan_projection": 1813.3,
            "refresh_task_planning": 1991.2,
            "goal_tree_refresh": 767.2,
        }

    pressure_after, corrosion_after = _run_profile(steps=args.steps)
    if pressure_after is None:
        print("No pressure_design_case submit captured.")
        sys.exit(1)
    if args.corrosion and corrosion_after is None:
        service = _build_service()
        project = service.create_project("Profile Phase Report Corrosion")
        session_id = service.activate_project(project["id"])["session_id"]
        corrosion_after = _run_corrosion_profile(service, session_id)

    lines: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        lines.append(line)

    emit()
    emit("=== pressure_design_case submit (before vs after) ===")
    emit(f"{'metric':28} {'before':>10} {'after':>10} {'delta':>10}")
    keys = sorted(set(before_pressure) | set(pressure_after))
    for key in keys:
        b = before_pressure.get(key, 0.0)
        a = pressure_after.get(key, 0.0)
        delta = a - b
        emit(f"{key:28} {b:10.1f} {a:10.1f} {delta:+10.1f}")

    if corrosion_after is not None:
        emit()
        emit("=== corrosion_allowance submit (after only, post-calculation) ===")
        for key, value in corrosion_after.items():
            emit(f"{key:28} {value:10.1f} ms")
        if corrosion_after.get("planning_refresh_skipped", 0.0) > 0:
            emit("lightweight planning_refresh_skipped: yes")
        if corrosion_after.get("goal_tree_refresh", 0.0) > 0:
            emit(
                "goal_tree_refresh ran (finalize pass): "
                f"{corrosion_after.get('goal_tree_refresh', 0.0):.1f} ms"
            )
        elif corrosion_after.get("planning_refresh_skipped", 0.0) <= 0:
            emit("goal_tree_refresh: not traced")

    if args.output:
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote report to {args.output}")


if __name__ == "__main__":
    main()
