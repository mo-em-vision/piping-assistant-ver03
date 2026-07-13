"""Load workflow runtime metadata from repo workflows/*.yaml and legacy sidecars."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.workflow_sidecar import _PROJECT_RUNTIME_WORKFLOW_IDS

_WORKFLOWS_ROOT = Path(__file__).resolve().parents[1] / "workflows"


def runtime_workflow_dirs(workflow_id: str) -> tuple[str, ...]:
    explicit = _PROJECT_RUNTIME_WORKFLOW_IDS.get(workflow_id)
    if explicit:
        return explicit
    return (workflow_id,)


def load_workflow_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 2:
            loaded = yaml.safe_load(parts[1])
            return loaded if isinstance(loaded, dict) else {}
    loaded = yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else {}


def workflow_yaml_matches(
    data: dict[str, Any],
    workflow_id: str,
    folder_ids: tuple[str, ...],
) -> bool:
    candidates = {workflow_id, *folder_ids}
    for key in ("key", "slug", "id", "engineering_intent"):
        value = str(data.get(key) or "").strip()
        if value and value in candidates:
            return True
    runtime = data.get("runtime")
    if isinstance(runtime, dict):
        for key in ("slug", "engineering_intent"):
            value = str(runtime.get(key) or "").strip()
            if value and value in candidates:
                return True
    return False


def load_workflow_document(workflow_id: str) -> dict[str, Any]:
    """Return the primary workflow YAML document for a slug or node id."""
    workflow_id = str(workflow_id or "").strip()
    if not workflow_id:
        return {}

    folder_ids = runtime_workflow_dirs(workflow_id)
    for folder in folder_ids:
        path = _WORKFLOWS_ROOT / folder / "runtime.yaml"
        if path.is_file():
            return load_workflow_yaml(path)

    for path in sorted(_WORKFLOWS_ROOT.glob("*.yaml")):
        loaded = load_workflow_yaml(path)
        if loaded and workflow_yaml_matches(loaded, workflow_id, folder_ids):
            return loaded
    return {}


def load_workflow_runtime_metadata(workflow_id: str) -> dict[str, Any]:
    """Return runtime metadata for a workflow (nested runtime block or flat sidecar)."""
    document = load_workflow_document(workflow_id)
    if not document:
        return {}

    runtime = document.get("runtime")
    if isinstance(runtime, dict):
        return dict(runtime)

    return document


def extract_suggested_workflow_ids(data: dict[str, Any]) -> list[str]:
    for container in (data, data.get("runtime") if isinstance(data.get("runtime"), dict) else {}):
        if not isinstance(container, dict):
            continue
        suggested = container.get("suggested_workflows")
        if isinstance(suggested, list):
            return [str(item).strip() for item in suggested if str(item).strip()]
    return []


def load_runtime_suggested_workflow_ids(workflow_id: str) -> list[str]:
    """Read suggested_workflows slugs from workflow runtime metadata."""
    document = load_workflow_document(workflow_id)
    if not document:
        return []
    suggested = extract_suggested_workflow_ids(document)
    if suggested:
        return suggested
    runtime = load_workflow_runtime_metadata(workflow_id)
    return extract_suggested_workflow_ids(runtime)
