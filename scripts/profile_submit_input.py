"""Profile submit_input and inspection_poll using performance traces.

Runs the smallest pipe wall thickness workflow, submits the first parameter,
optionally polls inspection once, and prints a bottleneck report from
``engine/inspection/performance_trace`` spans (not the legacy operation tracker).

Usage:
    set DEV_INSPECTION_ENABLED=1
    python scripts/profile_submit_input.py
    python scripts/profile_submit_input.py --steps 3 --inspection-poll
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("DEV_INSPECTION_ENABLED", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.desktop_service import DesktopApiService  # noqa: E402
from config.loader import CLIConfig  # noqa: E402
from engine.inspection.performance_trace import (  # noqa: E402
    attach_trace_to_payload,
    begin_interaction_trace,
    current_trace_snapshot,
    finish_interaction_trace,
    new_trace_id,
    recent_traces_snapshot,
    reset_trace_context,
)


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


def _next_parameter(state: dict[str, Any]) -> str | None:
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
    if param == "pressure_design_case":
        return "internal_pressure", None
    if param == "material_grade":
        return "SA-106B", None
    if param in {"material", "material_spec"}:
        return "SA-106B", None
    if param == "design_pressure":
        return 8.0, "bar"
    if param == "design_temperature":
        return 38.0, "degC"
    if param == "corrosion_allowance":
        return 3.0, "mm"
    if param in {"joint_category", "pipe_construction_type"}:
        return "seamless", None
    if param == "d_input_mode":
        return "direct_od", None
    if param == "geometry_input_mode":
        return "direct_od", None
    if param == "pipe_schedule":
        return "40", None
    if "pressure" in param:
        return 2.0, "MPa"
    if "temperature" in param:
        return 100.0, "degC"
    if param in {"nominal_pipe_size", "outside_diameter"}:
        return 2.0, "in"
    if param in {"weld_joint_efficiency", "weld_joint_strength_reduction_factor_W", "temperature_coefficient_Y"}:
        return 1.0, None
    return 1.0, "dimensionless"


def _run_traced(
    trigger: str,
    task_id: str,
    callback,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    trace_id = new_trace_id()
    begin_interaction_trace(trigger, trace_id=trace_id, task_id=task_id)
    status = "success"
    error: str | None = None
    payload: dict[str, Any] | None = None
    try:
        result = callback()
        if isinstance(result, dict):
            payload = result
            if "performance_trace" not in result:
                snapshot = current_trace_snapshot()
                if snapshot is not None:
                    payload = attach_trace_to_payload(dict(result))
        return result, payload.get("performance_trace") if payload else current_trace_snapshot()
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        try:
            finish_interaction_trace(status=status, error=error)
        finally:
            reset_trace_context()


def _leaf_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent_ids = {
        str(span.get("parent_span_id"))
        for span in spans
        if span.get("parent_span_id")
    }
    return [span for span in spans if str(span.get("span_id")) not in parent_ids]


def _op_type_totals(spans: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for span in _leaf_spans(spans):
        op_type = str(span.get("op_type") or "api")
        totals[op_type] += float(span.get("duration_ms") or 0.0)
    return dict(totals)


def _span_duration(spans: list[dict[str, Any]], name: str) -> float | None:
    matches = [float(span.get("duration_ms") or 0.0) for span in spans if span.get("name") == name]
    if not matches:
        return None
    return max(matches)


def _print_key_metrics(trace: dict[str, Any], *, label: str) -> None:
    spans = list(trace.get("spans") or [])
    total_ms = float(trace.get("total_duration_ms") or 0.0)
    print(f"\n=== Key metrics ({label}) ===")
    print(f"submit_input total:        {total_ms:8.1f} ms")
    for span_name in (
        "task_state",
        "engineering_plan_projection",
        "display_output_projection",
        "flow_guidance",
        "response_serialization",
        "refresh_task_planning",
        "goal_tree_refresh",
        "planning_refresh_skipped",
        "graph_build_plan",
        "canonical_task_state",
        "performance_trace_attachment",
    ):
        duration = _span_duration(spans, span_name)
        if duration is not None:
            print(f"{span_name:28} {duration:8.1f} ms")
    goal_tree = _span_duration(spans, "goal_tree_refresh")
    if goal_tree is None:
        print("goal_tree_refresh skipped: yes")
    else:
        print(f"goal_tree_refresh ran:     {goal_tree:8.1f} ms")


def _print_trace_report(trace: dict[str, Any], *, top_n: int = 5) -> None:
    trace_id = trace.get("trace_id", "?")
    trigger = trace.get("trigger", "?")
    total_ms = float(trace.get("total_duration_ms") or 0.0)
    llm = bool(trace.get("llm_call_occurred"))
    status = trace.get("status", "?")
    spans = list(trace.get("spans") or [])
    omitted = int(trace.get("spans_omitted") or 0)

    print(f"\nTrace {trace_id}")
    print(f"  trigger: {trigger}")
    print(f"  status:  {status}")
    print(f"  total:   {total_ms:.1f} ms")
    print(f"  llm:     {llm}")
    print(f"  spans:   {len(spans)}" + (f" (+{omitted} omitted)" if omitted else ""))

    by_op = _op_type_totals(spans)
    if by_op:
        leaf_total = sum(by_op.values())
        print("  op_type breakdown (leaf spans):")
        for op_type, ms in sorted(by_op.items(), key=lambda item: item[1], reverse=True):
            share = (ms / leaf_total * 100.0) if leaf_total > 0 else 0.0
            print(f"    {op_type:12} {ms:8.1f} ms  ({share:5.1f}%)")

    ranked = sorted(_leaf_spans(spans), key=lambda span: float(span.get("duration_ms") or 0.0), reverse=True)
    print(f"  top {min(top_n, len(ranked))} slowest spans:")
    for span in ranked[:top_n]:
        name = span.get("name", "?")
        op_type = span.get("op_type", "?")
        duration = float(span.get("duration_ms") or 0.0)
        notes = span.get("notes")
        note_suffix = f"  [{notes}]" if notes else ""
        llm_flag = " llm" if span.get("llm") else ""
        print(f"    {duration:8.1f} ms  {op_type:12} {name}{llm_flag}{note_suffix}")


def _print_summary(traces: list[dict[str, Any]]) -> None:
    if not traces:
        print("\nNo performance traces recorded. Is DEV_INSPECTION_ENABLED=1?")
        return

    submit_traces = [trace for trace in traces if trace.get("trigger") != "inspection_poll"]
    poll_traces = [trace for trace in traces if trace.get("trigger") == "inspection_poll"]

    print("\n=== Performance trace summary ===")
    print(f"submit/create traces: {len(submit_traces)}")
    print(f"inspection_poll traces: {len(poll_traces)}")

    if submit_traces:
        slowest_submit = max(submit_traces, key=lambda trace: float(trace.get("total_duration_ms") or 0.0))
        print(
            f"slowest submit trace: {slowest_submit.get('trace_id')} "
            f"({float(slowest_submit.get('total_duration_ms') or 0.0):.1f} ms, "
            f"trigger={slowest_submit.get('trigger')})"
        )
    if poll_traces:
        slowest_poll = max(poll_traces, key=lambda trace: float(trace.get("total_duration_ms") or 0.0))
        print(
            f"slowest inspection poll: {slowest_poll.get('trace_id')} "
            f"({float(slowest_poll.get('total_duration_ms') or 0.0):.1f} ms)"
        )

    any_llm = any(bool(trace.get("llm_call_occurred")) for trace in traces)
    print(f"llm_call_occurred in any trace: {any_llm}")

    print("\nNote: frontend spans (request_sent, frontend_state_update, render) appear only")
    print("when tracing through the desktop app. This script reports backend spans only.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile submit_input via performance traces.")
    parser.add_argument("--steps", type=int, default=2, help="Number of parameter submits (default: 2)")
    parser.add_argument(
        "--inspection-poll",
        action="store_true",
        help="Run one traced inspection poll after submits",
    )
    parser.add_argument("--top", type=int, default=5, help="Top slow spans per trace (default: 5)")
    args = parser.parse_args()

    service = _build_service()
    project = service.create_project("Profile Submit Input")
    session_id = service.activate_project(project["id"])["session_id"]
    state = service.create_task(workflow_id="pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]
    print(f"task_id={task_id}")
    print(f"workflow=pipe_wall_thickness_design")

    recorded_trace_ids: list[str] = []
    pressure_design_case_trace: dict[str, Any] | None = None
    corrosion_trace: dict[str, Any] | None = None

    for step in range(max(1, args.steps)):
        param = _next_parameter(state)
        if not param:
            print("no more parameters")
            break
        value, unit = _value_for(param)
        t0 = time.perf_counter()

        def _submit() -> dict[str, Any]:
            return service.submit_input(
                task_id,
                parameter=param,
                value=value,
                unit=unit,
                session_id=session_id,
            )

        state, trace = _run_traced("submit_input", task_id, _submit)
        wall_ms = (time.perf_counter() - t0) * 1000.0
        if trace:
            recorded_trace_ids.append(str(trace["trace_id"]))
            _print_trace_report(trace, top_n=args.top)
            if param == "pressure_design_case":
                pressure_design_case_trace = trace
            if param == "corrosion_allowance":
                corrosion_trace = trace
        print(f"\n--- step {step + 1}: submit {param!r} — wall {wall_ms:.0f} ms ---")

    if args.inspection_poll:
        t0 = time.perf_counter()

        def _poll() -> dict[str, Any]:
            return service.get_inspection(task_id, session_id)

        _payload, trace = _run_traced("inspection_poll", task_id, _poll)
        wall_ms = (time.perf_counter() - t0) * 1000.0
        if trace:
            recorded_trace_ids.append(str(trace["trace_id"]))
            _print_trace_report(trace, top_n=args.top)
        print(f"\n--- inspection poll — wall {wall_ms:.0f} ms ---")

    snapshot = recent_traces_snapshot(limit=40)
    traces = list(snapshot.get("traces") or [])
    if recorded_trace_ids:
        traces = [trace for trace in traces if trace.get("trace_id") in recorded_trace_ids] or traces
    if pressure_design_case_trace is not None:
        _print_key_metrics(pressure_design_case_trace, label="pressure_design_case submit")
    if corrosion_trace is not None:
        _print_key_metrics(corrosion_trace, label="corrosion_allowance submit")
    _print_summary(traces[: max(len(recorded_trace_ids), args.steps + (1 if args.inspection_poll else 0))])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
