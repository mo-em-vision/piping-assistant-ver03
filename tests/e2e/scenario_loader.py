"""Load YAML end-to-end scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Scenario:
    name: str
    description: str
    given: dict[str, Any]
    when: dict[str, Any]
    expected: dict[str, Any]
    steps: list[dict[str, Any]] = field(default_factory=list)
    source_path: Path | None = None


def load_scenario(path: Path) -> Scenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Scenario(
        name=str(raw.get("name", path.stem)),
        description=str(raw.get("description", "")),
        given=dict(raw.get("given", {})),
        when=dict(raw.get("when", {})),
        expected=dict(raw.get("expected", {})),
        steps=list(raw.get("steps", [])),
        source_path=path,
    )


def discover_scenarios(directory: Path) -> list[Scenario]:
    if not directory.exists():
        return []
    paths = sorted(directory.glob("*.yaml"))
    return [load_scenario(path) for path in paths]
