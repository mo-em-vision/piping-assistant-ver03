"""Guards for lazy dev/debug projection rebuilds during normal workflow."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import pytest

SERIALIZER_DEBUG_PROJECTION_SPANS: frozenset[str] = frozenset(
    {
        "legacy_goal_map_projection",
        "engineering_plan_to_dict",
        "engineering_plan_view",
    }
)

INSPECTION_DEBUG_SPANS: frozenset[str] = frozenset(
    {
        "build_inspection_payload",
    }
)

INTERACTIVE_FORBIDDEN_SERIALIZER_SPANS: frozenset[str] = (
    SERIALIZER_DEBUG_PROJECTION_SPANS | INSPECTION_DEBUG_SPANS
)

# "Several seconds" guard for serializer debug projection spans on interactive paths.
SERIALIZER_DEBUG_SPAN_BUDGET_MS = 2_000.0


def iter_spans(trace: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    spans = trace.get("spans")
    if not isinstance(spans, list):
        return
    for span in spans:
        if isinstance(span, dict):
            yield span


def span_names(trace: Mapping[str, Any]) -> set[str]:
    return {str(span.get("name")) for span in iter_spans(trace) if span.get("name")}


def serializer_debug_projection_duration_ms(trace: Mapping[str, Any]) -> float:
    total = 0.0
    for span in iter_spans(trace):
        if span.get("op_type") != "serializer":
            continue
        name = span.get("name")
        if name not in SERIALIZER_DEBUG_PROJECTION_SPANS:
            continue
        total += float(span.get("duration_ms") or 0.0)
    return total


def assert_interactive_trace_skips_debug_projection_spans(
    trace: Mapping[str, Any],
    *,
    context: str,
) -> None:
    for span in iter_spans(trace):
        name = span.get("name")
        op_type = span.get("op_type")
        if op_type == "serializer" and name in INTERACTIVE_FORBIDDEN_SERIALIZER_SPANS:
            pytest.fail(
                f"{context}: interactive trace must not rebuild serializer debug projections; "
                f"found span {name!r} ({span.get('duration_ms')} ms)"
            )


def assert_interactive_trace_projection_budget(
    trace: Mapping[str, Any],
    *,
    context: str,
) -> None:
    assert_interactive_trace_skips_debug_projection_spans(trace, context=context)

    for span in iter_spans(trace):
        name = span.get("name")
        duration_ms = float(span.get("duration_ms") or 0.0)
        if name == "engineering_plan_projection":
            notes = str(span.get("notes") or "")
            assert "mode=interactive" in notes, (
                f"{context}: engineering_plan_projection must run in interactive mode "
                f"(notes={notes!r})"
            )
        if span.get("op_type") == "serializer" and name in SERIALIZER_DEBUG_PROJECTION_SPANS:
            assert duration_ms < SERIALIZER_DEBUG_SPAN_BUDGET_MS, (
                f"{context}: serializer debug span {name!r} took {duration_ms:.1f} ms "
                f"(budget {SERIALIZER_DEBUG_SPAN_BUDGET_MS:.0f} ms)"
            )

    debug_ms = serializer_debug_projection_duration_ms(trace)
    assert debug_ms == 0.0, (
        f"{context}: interactive trace spent {debug_ms:.1f} ms on serializer debug projections"
    )


def assert_trace_rebuilds_inspection_debug_projections(
    trace: Mapping[str, Any],
    *,
    context: str,
) -> None:
    names = span_names(trace)
    assert "build_inspection_payload" in names, (
        f"{context}: inspection request must rebuild dev/debug projections "
        f"(missing build_inspection_payload span; saw {sorted(names)})"
    )
