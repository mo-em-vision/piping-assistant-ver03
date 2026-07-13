"""Contract helpers for canonical parameter keys in API payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from engine.reference.parameter_keys import (
    LEGACY_PARAMETER_KEY_ALIASES,
    canonical_parameter_key,
)
from engine.reference.standards_markdown import split_frontmatter

# System/runtime fact keys used on pipe-wall paths but not global PARAM ``key`` fields.
PIPE_WALL_SYSTEM_FACT_KEYS = frozenset(
    {
        "d_input_mode",
        "thin_wall",
    }
)


def load_global_parameter_registry_keys(
    project_root: Path | None = None,
) -> frozenset[str]:
    root = project_root or Path(__file__).resolve().parents[2]
    param_dir = root / "knowledge" / "global" / "parameters" / "nodes"
    keys: set[str] = set()
    for path in sorted(param_dir.glob("PARAM-*.yaml")):
        metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        key = str(metadata.get("key") or "").strip()
        if key:
            keys.add(key)
    if not keys:
        pytest.fail(f"no PARAM registry keys found under {param_dir}")
    return frozenset(keys)


def collect_api_parameter_fields(state: dict[str, Any]) -> dict[str, set[str]]:
    collected: dict[str, set[str]] = {
        "facts": set(),
        "parameter_names": set(),
        "current_ask": set(),
        "submittable": set(),
    }

    facts = state.get("facts") or {}
    if isinstance(facts, dict):
        collected["facts"].update(str(key) for key in facts if str(key).strip())

    for param in state.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        name = param.get("name")
        if name:
            collected["parameter_names"].add(str(name))

    current_ask = state.get("current_ask") or {}
    if isinstance(current_ask, dict) and current_ask.get("kind") == "input":
        parameter_id = current_ask.get("parameter_id")
        if parameter_id:
            collected["current_ask"].add(str(parameter_id))

    progress = state.get("progress") or {}
    if isinstance(progress, dict):
        for item in progress.get("submittable_parameters") or []:
            if item:
                collected["submittable"].add(str(item))

    return collected


def assert_api_state_uses_canonical_parameter_keys(
    state: dict[str, Any],
    *,
    registry: frozenset[str],
    system_fact_keys: frozenset[str] = PIPE_WALL_SYSTEM_FACT_KEYS,
) -> None:
    collected = collect_api_parameter_fields(state)
    legacy_keys = set(LEGACY_PARAMETER_KEY_ALIASES)
    parameter_slots = (
        collected["parameter_names"]
        | collected["current_ask"]
        | collected["submittable"]
    )

    for slot, keys in collected.items():
        for key in sorted(keys):
            if key in legacy_keys:
                pytest.fail(f"{slot} exposes legacy parameter alias {key!r}")
            if canonical_parameter_key(key) != key:
                pytest.fail(
                    f"{slot} exposes non-canonical parameter key {key!r} "
                    f"(canonical form {canonical_parameter_key(key)!r})"
                )

    for key in sorted(parameter_slots):
        if key not in registry:
            pytest.fail(
                f"parameter_id field {key!r} is not in the global PARAM registry"
            )

    for key in sorted(collected["facts"]):
        if key in registry or key in system_fact_keys:
            continue
        pytest.fail(
            f"facts[{key!r}] is neither a PARAM registry key nor an allowed system fact key"
        )
