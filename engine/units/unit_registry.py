"""Graph-backed unit registry: dimensions to allowed UNIT-* ids."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.reference.parameter_metadata import normalize_allowed_units
from engine.units.unit_ids import normalize_dimension, symbol_from_unit_id, unit_dimension_key
from engine.units.unit_resolver import UnitResolver, get_unit_resolver


_DIMENSIONLESS_UNITS: tuple[str, ...] = ("UNIT-dimensionless",)


@dataclass
class UnitRegistry:
    """Resolve allowed units from quantity dimensions via the global unit pack."""

    resolver: UnitResolver = field(default_factory=get_unit_resolver)
    _by_dimension: dict[str, tuple[str, ...]] | None = field(default=None, repr=False)

    def _ensure_index(self) -> None:
        if self._by_dimension is not None:
            return
        self.resolver.load()
        grouped: dict[str, set[str]] = {}
        graph = self.resolver._graph
        if graph is None:
            self._by_dimension = {}
            return
        for node_id, record in graph.nodes.items():
            if record.node_type != "unit":
                continue
            dimension = unit_dimension_key(record.metadata)
            if dimension:
                grouped.setdefault(dimension, set()).add(node_id)
        self._by_dimension = {
            dimension: tuple(sorted(unit_ids))
            for dimension, unit_ids in grouped.items()
        }

    def list_dimensions(self) -> tuple[str, ...]:
        self._ensure_index()
        assert self._by_dimension is not None
        return tuple(sorted(self._by_dimension.keys()))

    def units_for_dimension(self, dimension: str | None) -> tuple[str, ...]:
        if not dimension:
            return ()
        self._ensure_index()
        assert self._by_dimension is not None
        registry_key = normalize_dimension(dimension)
        if registry_key is None:
            return ()
        return self._by_dimension.get(registry_key, ())

    def allowed_units_for_parameter(
        self,
        *,
        param_meta: dict[str, Any],
        quantity_dimension: str | None,
        is_designation: bool,
    ) -> tuple[str, ...]:
        if is_designation:
            return _DIMENSIONLESS_UNITS

        explicit = normalize_allowed_units(param_meta)
        if explicit:
            return tuple(explicit)

        if quantity_dimension is None:
            canonical = str(param_meta.get("canonical_unit") or "").strip()
            if canonical == "UNIT-dimensionless":
                return _DIMENSIONLESS_UNITS
            return ()

        return self.units_for_dimension(quantity_dimension)

    def resolve_allowed_unit_symbols(
        self,
        *,
        param_meta: dict[str, Any],
        quantity_dimension: str | None,
        is_designation: bool,
    ) -> set[str]:
        allowed_ids = self.allowed_units_for_parameter(
            param_meta=param_meta,
            quantity_dimension=quantity_dimension,
            is_designation=is_designation,
        )
        symbols: set[str] = set()
        for unit_id in allowed_ids:
            symbols.add(symbol_from_unit_id(unit_id).lower())
            symbol = self.resolver.unit_symbol(unit_id)
            if symbol:
                symbols.add(symbol.lower())
        return symbols


_default_registry: UnitRegistry | None = None


def get_unit_registry() -> UnitRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = UnitRegistry()
    return _default_registry


def reset_unit_registry() -> None:
    """Clear cached registry (for tests)."""
    global _default_registry
    _default_registry = None
