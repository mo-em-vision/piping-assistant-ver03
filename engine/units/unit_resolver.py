"""Graph-native unit conversion via converts_to edges."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.units.unit_ids import (
    canonical_si_unit_id,
    normalize_unit_key,
    symbol_from_unit_id,
    unit_dimension_key,
    unit_id_from_legacy_symbol,
)


@dataclass(frozen=True)
class _AffineStep:
    factor: float
    offset: float


@dataclass
class UnitResolver:
    """Resolve units and convert values using the global unit pack graph."""

    pack_root: Path
    _graph: Any = None
    _alias_to_id: dict[str, str] | None = None
    _edges: dict[str, list[tuple[str, _AffineStep]]] | None = None
    _dimensions: dict[str, str] | None = None

    @classmethod
    def default(cls) -> UnitResolver:
        from engine.reference.knowledge_paths import units_root

        return cls(pack_root=units_root())

    def load(self) -> None:
        if self._graph is not None:
            return
        from engine.graph.graph_builder import GraphBuilder
        from engine.reference.graph_cache import build_or_load_graph

        pack_root = self.pack_root.resolve()
        if (pack_root / "nodes").is_dir():
            self._graph = build_or_load_graph(pack_root)
        else:
            self._graph = GraphBuilder(pack_root).build()
        self._build_indexes()

    def _build_indexes(self) -> None:
        graph = self._graph
        if graph is None:
            return

        alias_to_id: dict[str, str] = {}
        dimensions: dict[str, str] = {}
        edges: dict[str, list[tuple[str, _AffineStep]]] = {}

        for node_id, record in graph.nodes.items():
            if record.node_type != "unit":
                continue
            meta = record.metadata
            symbol = str(meta.get("symbol") or "").strip()
            if symbol:
                alias_to_id[normalize_unit_key(symbol)] = node_id
            alias_to_id[normalize_unit_key(node_id)] = node_id
            for alias in meta.get("aliases") or []:
                if isinstance(alias, str) and alias.strip():
                    alias_to_id[normalize_unit_key(alias)] = node_id
            dimension = unit_dimension_key(meta)
            if dimension:
                dimensions[node_id] = dimension

        for edge in graph.edges:
            if edge.edge_type not in {"converts_to", "derived_from"}:
                continue
            meta = edge.metadata or {}
            factor = float(meta.get("factor", 1.0))
            offset = float(meta.get("offset", 0.0))
            step = _AffineStep(factor=factor, offset=offset)
            edges.setdefault(edge.from_id, []).append((edge.to_id, step))
            if factor != 0.0:
                inverse = _AffineStep(factor=1.0 / factor, offset=-offset / factor)
                edges.setdefault(edge.to_id, []).append((edge.from_id, inverse))

        self._alias_to_id = alias_to_id
        self._edges = edges
        self._dimensions = dimensions

    def resolve_unit_id(self, unit: str) -> str | None:
        self.load()
        if not unit or not str(unit).strip():
            return "UNIT-dimensionless"
        text = str(unit).strip()
        if text.startswith("UNIT-"):
            if self._alias_to_id and normalize_unit_key(text) in self._alias_to_id:
                return self._alias_to_id[normalize_unit_key(text)]
            return text
        if self._alias_to_id:
            resolved = self._alias_to_id.get(normalize_unit_key(text))
            if resolved:
                return resolved
        return unit_id_from_legacy_symbol(text)

    def unit_symbol(self, unit_id: str) -> str:
        self.load()
        if self._graph:
            record = self._graph.get_node(unit_id)
            if record is not None:
                symbol = str(record.metadata.get("symbol") or "").strip()
                if symbol:
                    return symbol
        return symbol_from_unit_id(unit_id)

    def dimension(self, unit_id: str) -> str | None:
        self.load()
        if self._dimensions:
            return self._dimensions.get(unit_id)
        return None

    def _compose_affine(self, steps: list[_AffineStep]) -> _AffineStep:
        factor, offset = 1.0, 0.0
        for step in steps:
            offset = offset * step.factor + step.offset
            factor *= step.factor
        return _AffineStep(factor=factor, offset=offset)

    def _find_path(self, from_id: str, to_id: str) -> list[_AffineStep] | None:
        if from_id == to_id:
            return []
        if not self._edges:
            return None

        queue: deque[str] = deque([from_id])
        visited = {from_id}
        parent: dict[str, tuple[str, _AffineStep]] = {}

        while queue:
            current = queue.popleft()
            for neighbor, step in self._edges.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = (current, step)
                if neighbor == to_id:
                    queue.clear()
                    break
                queue.append(neighbor)

        if to_id not in parent and from_id != to_id:
            return None

        steps: list[_AffineStep] = []
        cursor = to_id
        while cursor != from_id:
            prev, step = parent[cursor]
            steps.append(step)
            cursor = prev
        steps.reverse()
        return steps

    def convert_value(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> tuple[float, str]:
        """Convert numeric value between units using the unit graph."""
        self.load()
        from_id = self.resolve_unit_id(from_unit)
        to_id = self.resolve_unit_id(to_unit)
        if from_id is None or to_id is None:
            raise ValueError(f"Unknown unit: {from_unit!r} or {to_unit!r}")

        from_dim = self.dimension(from_id)
        to_dim = self.dimension(to_id)
        if from_dim and to_dim and from_dim != to_dim:
            raise ValueError(
                f"Incompatible dimensions: {from_unit!r} ({from_dim}) vs {to_unit!r} ({to_dim})"
            )

        path = self._find_path(from_id, to_id)
        if path is None:
            raise ValueError(f"No conversion path from {from_unit!r} to {to_unit!r}")

        affine = self._compose_affine(path)
        converted = value * affine.factor + affine.offset
        return converted, self.unit_symbol(to_id)

    def convert_to_canonical_si(
        self,
        value: float,
        from_unit: str,
        *,
        dimension: str | None = None,
    ) -> tuple[float, str]:
        """Convert to SI canonical unit for the quantity dimension."""
        self.load()
        from_id = self.resolve_unit_id(from_unit)
        if from_id is None:
            raise ValueError(f"Unknown unit: {from_unit!r}")

        dim = dimension or self.dimension(from_id)
        if not dim:
            raise ValueError(f"Cannot determine dimension for unit {from_unit!r}")

        target_id = canonical_si_unit_id(dim)
        if target_id is None:
            raise ValueError(f"No canonical SI unit for dimension {dim!r}")

        return self.convert_value(value, from_id, target_id)


_default_resolver: UnitResolver | None = None


def get_unit_resolver() -> UnitResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = UnitResolver.default()
    return _default_resolver


def reset_unit_resolver() -> None:
    """Clear cached resolver (for tests)."""
    global _default_resolver
    _default_resolver = None
