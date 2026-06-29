"""Pack revision tracking for dev studio auto-refresh."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.graph.graph_builder import compute_source_fingerprint
from engine.reference.graph_cache import build_or_load_graph


@dataclass
class PackRevision:
    pack: str
    revision: str
    node_count: int
    updated_at: str


def compute_pack_revision(pack_root: Path) -> PackRevision:
    pack_root = pack_root.resolve()
    pack = pack_root.name
    fingerprint = compute_source_fingerprint(pack_root)
    graph = build_or_load_graph(pack_root)
    node_count = len(graph.nodes)
    if node_count == 0:
        return PackRevision(
            pack=pack,
            revision="empty",
            node_count=0,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    digest = hashlib.sha256(f"{fingerprint}:{node_count}".encode()).hexdigest()[:16]
    return PackRevision(
        pack=pack,
        revision=digest,
        node_count=node_count,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
