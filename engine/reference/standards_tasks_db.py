"""Global workflow task content compiled from standards/tasks/."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_nodes import StandardsNodesDatabase
from engine.reference.standards_paths import resolve_global_tasks_db


class StandardsTasksDatabase(StandardsNodesDatabase):
    """Read and write compiled workflow root content for all standards."""

    @staticmethod
    def for_standards_root(standards_root: Path) -> StandardsTasksDatabase:
        return StandardsTasksDatabase(resolve_global_tasks_db(standards_root))
