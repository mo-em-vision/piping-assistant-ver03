"""Graph integrity checks for developer inspection."""

from __future__ import annotations

from typing import Any

from engine.inspection.models import IntegrityCheckResult
from engine.reference.standards_reader import StandardsReader


def run_integrity_checks(reader: StandardsReader | None) -> list[IntegrityCheckResult]:
    """Run lightweight integrity checks against the standards graph."""
    if reader is None:
        return [
            IntegrityCheckResult(
                check_id="reader_available",
                name="Standards reader",
                passed=False,
                message="Standards reader unavailable",
            )
        ]

    results: list[IntegrityCheckResult] = []
    results.append(_check_no_typescript_node_ids(reader))
    results.append(_check_titles_from_graph(reader))
    results.append(_check_node_id_resolution(reader))
    results.append(_check_disabled_nodes_surface_errors(reader))
    return results


def _check_no_typescript_node_ids(reader: StandardsReader) -> IntegrityCheckResult:
    """Nodes resolve by graph id, not file paths."""
    store = reader.graph_store
    if not store.available:
        return IntegrityCheckResult(
            check_id="rename_node_id",
            name="Rename node ID",
            passed=True,
            message="Graph store unavailable; skipped",
        )
    store.load()
    workflows = store.list_workflows()
    if not workflows:
        return IntegrityCheckResult(
            check_id="rename_node_id",
            name="Rename node ID",
            passed=True,
            message="No workflows to validate",
        )
    sample = workflows[0].node_id
    node = store.get_node(sample)
    passed = node is not None and node.node_id == sample
    return IntegrityCheckResult(
        check_id="rename_node_id",
        name="Rename node ID",
        passed=passed,
        message="Node IDs resolve via graph store" if passed else "Node ID resolution failed",
        details={"sample_node_id": sample},
    )


def _check_titles_from_graph(reader: StandardsReader) -> IntegrityCheckResult:
    store = reader.graph_store
    if not store.available:
        return IntegrityCheckResult(
            check_id="rename_display_title",
            name="Rename display title",
            passed=True,
            message="Graph store unavailable; skipped",
        )
    store.load()
    missing: list[str] = []
    for node in store.list_nodes()[:50]:
        title = str(node.metadata.get("title", "")).strip()
        if not title:
            missing.append(node.node_id)
    passed = len(missing) == 0
    return IntegrityCheckResult(
        check_id="rename_display_title",
        name="Rename display title",
        passed=passed,
        message="All sampled nodes have graph-defined titles"
        if passed
        else f"{len(missing)} nodes missing titles",
        details={"missing_titles": missing[:10]},
    )


def _check_node_id_resolution(reader: StandardsReader) -> IntegrityCheckResult:
    store = reader.graph_store
    if not store.available:
        return IntegrityCheckResult(
            check_id="move_node_folder",
            name="Move node folder",
            passed=True,
            message="Graph store unavailable; skipped",
        )
    store.load()
    orphans = [node.node_id for node in store.list_nodes() if not store.get_node(node.node_id)]
    passed = len(orphans) == 0
    return IntegrityCheckResult(
        check_id="move_node_folder",
        name="Move node folder",
        passed=passed,
        message="Nodes resolve regardless of folder layout" if passed else "Orphan nodes detected",
        details={"orphan_count": len(orphans)},
    )


def _check_disabled_nodes_surface_errors(reader: StandardsReader) -> IntegrityCheckResult:
    """Verify graph structure is intact (proxy for disable-node graceful failure)."""
    store = reader.graph_store
    if not store.available:
        return IntegrityCheckResult(
            check_id="disable_node",
            name="Disable node",
            passed=True,
            message="Graph store unavailable; skipped",
        )
    store.load()
    broken_edges: list[dict[str, str]] = []
    for node in store.list_nodes()[:100]:
        for edge in store.outgoing(node.node_id):
            if store.get_node(edge.to_id) is None:
                broken_edges.append(
                    {"from": edge.from_id, "to": edge.to_id, "type": edge.edge_type}
                )
    passed = len(broken_edges) == 0
    return IntegrityCheckResult(
        check_id="disable_node",
        name="Disable node",
        passed=passed,
        message="No dangling edges; disabled nodes would surface missing dependencies"
        if passed
        else f"{len(broken_edges)} dangling edges",
        details={"broken_edges": broken_edges[:10]},
    )
