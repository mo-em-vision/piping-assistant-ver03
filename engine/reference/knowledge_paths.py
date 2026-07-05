"""Resolve knowledge root layout: standards packs and global ontologies."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_KNOWLEDGE_ROOT = Path("knowledge")


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def knowledge_root(*, project_root: Path | None = None) -> Path:
    """Return the knowledge data root (env KNOWLEDGE_ROOT or default ``knowledge/``)."""
    root = project_root or resolve_project_root()
    configured = os.environ.get("KNOWLEDGE_ROOT", str(_DEFAULT_KNOWLEDGE_ROOT)).strip()
    path = Path(configured)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def standards_root(*, project_root: Path | None = None, standards_root_override: Path | None = None) -> Path:
    """Return per-standard pack root under ``knowledge/standards/`` unless overridden."""
    if standards_root_override is not None:
        path = standards_root_override
        if not path.is_absolute():
            path = (project_root or resolve_project_root()) / path
        return path.resolve()
    return (knowledge_root(project_root=project_root) / "standards").resolve()


def global_root(*, project_root: Path | None = None) -> Path:
    """Return shared ontology root ``knowledge/global/``."""
    return (knowledge_root(project_root=project_root) / "global").resolve()


def dimensions_root(*, project_root: Path | None = None) -> Path:
    """Global physical-dimension ontology pack root."""
    return global_root(project_root=project_root) / "dimensions"


def dimensions_registry_path(*, project_root: Path | None = None, standards_root_override: Path | None = None) -> Path:
    """Registry linking pipe dimension packs to standards packs."""
    _ = standards_root_override  # legacy callers pass standards_root; registry is global
    return dimensions_root(project_root=project_root) / "registry.yaml"


def units_root(*, project_root: Path | None = None) -> Path:
    """Global unit ontology pack root."""
    return global_root(project_root=project_root) / "units"


def parameters_root(*, project_root: Path | None = None) -> Path:
    """Global canonical parameter ontology pack root."""
    return global_root(project_root=project_root) / "parameters"


def concepts_root(*, project_root: Path | None = None) -> Path:
    """Global engineering concept ontology pack root."""
    return global_root(project_root=project_root) / "concepts"


def authorities_root(*, project_root: Path | None = None) -> Path:
    """Global authority ontology pack root."""
    return global_root(project_root=project_root) / "authorities"


def materials_root(
    *,
    project_root: Path | None = None,
    standards_root: Path | None = None,
) -> Path:
    """Global material registry and search catalog root."""
    if standards_root is not None:
        return standards_root.resolve().parent / "global" / "materials"
    return global_root(project_root=project_root) / "materials"


def datatypes_root(*, project_root: Path | None = None) -> Path:
    """Global datatype ontology root (placeholder until populated)."""
    return global_root(project_root=project_root) / "datatypes"


def workflows_root(*, project_root: Path | None = None) -> Path:
    """Workflow YAML sources at repo root (not under knowledge/)."""
    return (project_root or resolve_project_root()) / "workflows"
