"""Build presentation blocks from workflow state and the knowledge graph."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_store import GraphStore
from models.workflow_state import WorkflowState

from .blocks import (
    render_equation_blocks,
    render_lifecycle_context,
    render_lookup_results,
    render_parameter_requests,
    render_warnings,
    render_workflow_documentation,
)
from .inputs import engineering_inputs_from_parameters


def build_presentation(
    workflow_state: WorkflowState,
    store: GraphStore,
) -> tuple[dict[str, Any], ...]:
    """Render ordered presentation blocks from graph + workflow state only."""
    if not store.available:
        return ()

    inputs = engineering_inputs_from_parameters(workflow_state.parameters)
    blocks: list[dict[str, Any]] = []
    blocks.extend(render_workflow_documentation(workflow_state, store))
    blocks.extend(render_lifecycle_context(workflow_state))
    blocks.extend(render_parameter_requests(workflow_state))
    blocks.extend(render_warnings(workflow_state))
    blocks.extend(render_lookup_results(workflow_state))
    blocks.extend(render_equation_blocks(workflow_state, store, inputs))
    return tuple(blocks)
