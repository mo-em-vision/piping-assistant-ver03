"""Tests for API error recovery catalog."""

from __future__ import annotations

from api.error_catalog import build_recovery, enrich_api_error_payload


def test_enrich_invalid_input_includes_parameter_guidance() -> None:
    payload = enrich_api_error_payload(
        "invalid_input",
        "design_pressure must be positive",
        details={"parameter": "design_pressure"},
    )

    assert payload["code"] == "invalid_input"
    assert payload["recovery"]["title"] == "Invalid engineering input"
    assert "design_pressure" in payload["recovery"]["next_action"]
    assert payload["recovery"]["what_happened"] == "design_pressure must be positive"


def test_build_recovery_for_backend_unavailable() -> None:
    recovery = build_recovery("backend_unavailable", "Process exited")

    assert recovery["title"] == "Backend unavailable"
    assert recovery["what_happened"] == "Process exited"
    assert "Retry" in recovery["next_action"]
