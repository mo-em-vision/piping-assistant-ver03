"""Verify no node-owned sidecar files remain after migration."""

from __future__ import annotations

from pathlib import Path

from engine.reference.node_sources import _SIDECAR_FILENAMES


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_no_node_owned_sidecars_remain() -> None:
    roots = [
        _project_root() / "knowledge",
        _project_root() / "workflows",
    ]
    offenders: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if lower in _SIDECAR_FILENAMES:
                offenders.append(str(path.relative_to(_project_root())))
            if lower.endswith(".execution.yaml") or lower.endswith(".nomenclature.yaml"):
                offenders.append(str(path.relative_to(_project_root())))
    assert offenders == [], offenders
