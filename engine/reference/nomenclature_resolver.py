"""Resolve symbol definitions and defaults from nomenclature definition nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.assumption_checker import field_value, normalize_assumption_value
from engine.reference.knowledge_paths import dimensions_root, materials_root
from engine.reference.graph_edge_schema import (
    dimension_allowed_unit_ids,
    edge_target,
    edge_targets,
    iter_stored_edges,
)
from engine.reference.knowledge_paths import parameters_root
from engine.reference.paragraph_sidecar import merge_paragraph_sidecar_metadata
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact


@dataclass(frozen=True)
class NomenclatureDefault:
    value: Any
    unit: str
    condition: str | None = None
    requires_confirmation: bool = True


@dataclass(frozen=True)
class NomenclatureEntry:
    symbol: str
    description: str
    unit: str = "dimensionless"
    input_id: str | None = None
    allowed_units: tuple[str, ...] = ()
    references: tuple[dict[str, Any], ...] = ()
    defaults: tuple[NomenclatureDefault, ...] = ()


def input_applies(
    spec: dict[str, Any],
    task_inputs: dict[str, Fact],
) -> bool:
    when = spec.get("when")
    if not when or not isinstance(when, dict):
        return True
    field_name = str(when.get("field", ""))
    allowed = when.get("in") or []
    if not field_name:
        return True
    value = field_value(field_name, task_inputs)
    if value is None:
        return False
    normalized_allowed = {normalize_assumption_value(v) for v in allowed}
    return value in normalized_allowed


def _load_global_parameter_metadata(param_id: str) -> dict[str, Any] | None:
    path = parameters_root() / "nodes" / f"{param_id}.yaml"
    if not path.is_file():
        return None
    metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    if str(metadata.get("type", "")) != "parameter":
        return None
    return metadata


def _legacy_unit_label(unit_id: str) -> str:
    text = str(unit_id or "").strip()
    if text.startswith("UNIT-"):
        return text.replace("UNIT-", "").lower()
    return text or "dimensionless"


def _references_from_parameter_edges(param_meta: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for edge in param_meta.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        target = str(edge.get("target", "")).strip()
        if target.startswith("B3610-"):
            refs.append({"standard": "asme_b36.10", "node_id": target})
        elif target.startswith("B313-table-"):
            refs.append({"table": target, "node_id": target})
        elif target.startswith("304."):
            refs.append({"paragraph": target, "node_id": target})
    return tuple(refs)


def _entry_from_parameter(param_meta: dict[str, Any]) -> NomenclatureEntry | None:
    symbol = str(param_meta.get("canonical_symbol") or "").strip()
    if not symbol:
        return None
    key = str(param_meta.get("key") or "").strip()
    description = str(param_meta.get("description") or param_meta.get("name") or "").strip()
    unit = "dimensionless"
    allowed_units: tuple[str, ...] = ()
    dim_ref = str(param_meta.get("dimension") or "").strip()
    if dim_ref.startswith("DIM-"):
        dim_meta = _load_dimension_node(dim_ref)
        if dim_meta is not None:
            allowed = dimension_allowed_unit_ids(dim_meta)
            if allowed:
                allowed_units = tuple(_legacy_unit_label(item) for item in allowed)
            canonical = str(dim_meta.get("canonical_unit") or "").strip()
            if canonical:
                unit = _legacy_unit_label(canonical)
    return NomenclatureEntry(
        symbol=symbol,
        description=description,
        unit=unit,
        input_id=key or None,
        allowed_units=allowed_units,
        references=_references_from_parameter_edges(param_meta),
        defaults=(),
    )


def _defaults_from_parameter_defaults(
    param_key: str,
    default_items: list[Any],
    *,
    fallback_unit: str,
) -> tuple[NomenclatureDefault, ...]:
    defaults: list[NomenclatureDefault] = []
    for item in default_items or []:
        if not isinstance(item, dict):
            continue
        defaults.append(
            NomenclatureDefault(
                value=item.get("value"),
                unit=str(item.get("unit", fallback_unit)),
                condition=(
                    str(item["condition"]).strip() if item.get("condition") else None
                ),
                requires_confirmation=bool(item.get("requires_confirmation", True)),
            )
        )
    return tuple(defaults)


def _load_nomenclature_from_introduced_parameters(
    metadata: dict[str, Any],
) -> dict[str, NomenclatureEntry]:
    entries: dict[str, NomenclatureEntry] = {}
    param_defaults = metadata.get("parameter_defaults") or {}
    for edge in metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type", "")).strip() != "introduces_parameter":
            continue
        param_id = str(edge.get("target", "")).strip()
        if not param_id.startswith("PARAM-"):
            continue
        param_meta = _load_global_parameter_metadata(param_id)
        if param_meta is None:
            continue
        entry = _entry_from_parameter(param_meta)
        if entry is None:
            continue
        param_key = str(param_meta.get("key") or "").strip()
        if param_key and param_key in param_defaults:
            default_items = param_defaults.get(param_key) or []
            entry = NomenclatureEntry(
                symbol=entry.symbol,
                description=entry.description,
                unit=entry.unit,
                input_id=entry.input_id,
                allowed_units=entry.allowed_units,
                references=entry.references,
                defaults=_defaults_from_parameter_defaults(
                    param_key,
                    default_items if isinstance(default_items, list) else [],
                    fallback_unit=entry.unit,
                ),
            )
        entries[entry.symbol] = entry
    return entries


def load_nomenclature(reader: StandardsReader, node_id: str) -> dict[str, NomenclatureEntry]:
    """Load symbol definitions from paragraph introduces_parameter edges or legacy nomenclature."""
    record = reader.load(node_id)
    metadata = merge_paragraph_sidecar_metadata(
        record.metadata,
        record_path=record.path,
        node_id=record.node_id,
    )
    entries: dict[str, NomenclatureEntry] = {}
    for item in metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        if not symbol:
            continue

        defaults: list[NomenclatureDefault] = []
        for default_item in item.get("defaults", []) or []:
            if not isinstance(default_item, dict):
                continue
            defaults.append(
                NomenclatureDefault(
                    value=default_item.get("value"),
                    unit=str(default_item.get("unit", item.get("unit", "dimensionless"))),
                    condition=(
                        str(default_item["condition"]).strip()
                        if default_item.get("condition")
                        else None
                    ),
                    requires_confirmation=bool(
                        default_item.get("requires_confirmation", True)
                    ),
                )
            )

        allowed = item.get("allowed_units") or []
        refs = item.get("citations") or item.get("references") or []
        entries[symbol] = NomenclatureEntry(
            symbol=symbol,
            description=str(item.get("description", "")).strip(),
            unit=str(item.get("unit", "dimensionless")),
            input_id=str(item["input_id"]) if item.get("input_id") else None,
            allowed_units=tuple(str(u) for u in allowed),
            references=tuple(r for r in refs if isinstance(r, dict)),
            defaults=tuple(defaults),
        )
    if entries:
        return entries
    return _load_nomenclature_from_introduced_parameters(metadata)


def entry_for_symbol(
    nomenclature: dict[str, NomenclatureEntry],
    *,
    symbol: str | None = None,
    input_id: str | None = None,
) -> NomenclatureEntry | None:
    if symbol and symbol in nomenclature:
        return nomenclature[symbol]
    if input_id:
        for entry in nomenclature.values():
            if entry.input_id == input_id:
                return entry
    return None


def spec_symbol(spec: dict[str, Any], *, fallback: str = "") -> str:
    """Return the engineering symbol from an input or output spec."""
    symbol = spec.get("symbol") or spec.get("name")
    if symbol:
        return str(symbol)
    if fallback:
        return fallback
    return str(spec.get("id", ""))


_DIMENSION_NODE_CACHE: dict[str, dict[str, Any] | None] = {}


def _load_dimension_node(node_id: str) -> dict[str, Any] | None:
    if node_id in _DIMENSION_NODE_CACHE:
        return _DIMENSION_NODE_CACHE[node_id]
    path = dimensions_root() / "nodes" / f"{node_id}.yaml"
    if not path.is_file():
        _DIMENSION_NODE_CACHE[node_id] = None
        return None
    metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    if str(metadata.get("type", "")) != "dimension":
        _DIMENSION_NODE_CACHE[node_id] = None
        return None
    _DIMENSION_NODE_CACHE[node_id] = metadata
    return metadata


def resolve_dimension_input_spec(input_spec: dict[str, Any]) -> dict[str, Any]:
    """Merge input metadata from global dimension node references (e.g. DIM-temperature)."""
    merged = dict(input_spec)
    refs = input_spec.get("references") or input_spec.get("citations") or []
    dimension_refs = [
        str(ref).strip()
        for ref in refs
        if str(ref).strip().startswith("DIM-")
    ]
    if not dimension_refs:
        return merged

    dim_meta = _load_dimension_node(dimension_refs[0])
    if dim_meta is None:
        return merged

    key = str(dim_meta.get("key", "")).strip()
    if key and not merged.get("dimension"):
        merged["dimension"] = key

    raw_canonical = dim_meta.get("canonical_unit")
    if raw_canonical is not None:
        canonical = str(raw_canonical).strip()
        if canonical and canonical.lower() != "null" and not merged.get("canonical_unit"):
            merged["canonical_unit"] = canonical

    if not merged.get("allowed_units"):
        allowed = dimension_allowed_unit_ids(dim_meta)
        if allowed:
            merged["allowed_units"] = allowed

    display_name = str(input_spec.get("display_name", "")).strip()
    if display_name:
        merged["name"] = display_name
        if not str(input_spec.get("description", "")).strip():
            merged["description"] = display_name

    return merged


def resolve_dimension_output_spec(output_spec: dict[str, Any]) -> dict[str, Any]:
    """Merge output metadata from global dimension node references (e.g. DIM-pressure)."""
    merged = dict(output_spec)
    refs = output_spec.get("references") or []
    dimension_refs = [
        str(ref).strip()
        for ref in refs
        if str(ref).strip().startswith("DIM-")
    ]
    if not dimension_refs:
        return merged

    dim_meta = _load_dimension_node(dimension_refs[0])
    if dim_meta is None:
        return merged

    key = str(dim_meta.get("key", "")).strip()
    if key and not merged.get("dimension"):
        merged["dimension"] = key

    raw_canonical = dim_meta.get("canonical_unit")
    if raw_canonical is not None:
        canonical = str(raw_canonical).strip()
        if canonical and canonical.lower() != "null" and not merged.get("canonical_unit"):
            merged["canonical_unit"] = canonical

    if not merged.get("allowed_units"):
        allowed = dimension_allowed_unit_ids(dim_meta)
        if allowed:
            merged["allowed_units"] = allowed

    return merged


def enrich_output_spec(output_spec: dict[str, Any]) -> dict[str, Any]:
    """Apply dimension enrichment to an output spec."""
    return resolve_dimension_output_spec(output_spec)


_MATERIAL_CATALOG_CACHE: dict[str, dict[str, Any] | None] = {}


def _load_material_catalog_node(node_id: str) -> dict[str, Any] | None:
    if node_id in _MATERIAL_CATALOG_CACHE:
        return _MATERIAL_CATALOG_CACHE[node_id]
    path = materials_root() / "nodes" / f"{node_id}.yaml"
    if not path.is_file():
        _MATERIAL_CATALOG_CACHE[node_id] = None
        return None
    metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    if str(metadata.get("type", "")) != "material_catalog":
        _MATERIAL_CATALOG_CACHE[node_id] = None
        return None
    _MATERIAL_CATALOG_CACHE[node_id] = metadata
    return metadata


def resolve_material_input_spec(input_spec: dict[str, Any]) -> dict[str, Any]:
    """Merge input metadata from global material catalog references (e.g. MAT-catalog)."""
    merged = dict(input_spec)
    refs = input_spec.get("references") or input_spec.get("citations") or []
    catalog_refs = [
        str(ref).strip()
        for ref in refs
        if str(ref).strip().startswith("MAT-")
    ]
    if not catalog_refs:
        return merged

    catalog_meta = _load_material_catalog_node(catalog_refs[0])
    if catalog_meta is None:
        return merged

    canonical = str(catalog_meta.get("canonical_unit", "UNIT-dimensionless")).strip()
    if canonical:
        merged.setdefault("canonical_unit", canonical)
    merged.setdefault("unit", "dimensionless")
    return merged


def task_input_key(spec: dict[str, Any]) -> str:
    """Resolve the task-level input id for a table or node input spec."""
    bridge = str(spec.get("task_input_id", "")).strip()
    if bridge:
        return bridge
    return str(spec.get("id", ""))


def enrich_input_spec(
    input_spec: dict[str, Any],
    nomenclature: dict[str, NomenclatureEntry] | None = None,
) -> dict[str, Any]:
    """Apply material, dimension, task bridge, and nomenclature enrichment."""
    spec = resolve_material_input_spec(input_spec)
    spec = resolve_dimension_input_spec(spec)
    bridge = str(spec.get("task_input_id", "")).strip()
    if bridge:
        spec["binds_to"] = bridge
    if nomenclature:
        spec = resolve_input_spec(spec, nomenclature)
    return spec


def resolve_input_spec(
    input_spec: dict[str, Any],
    nomenclature: dict[str, NomenclatureEntry],
) -> dict[str, Any]:
    """Merge calculation input metadata with nomenclature definitions."""
    merged = dict(input_spec)
    symbol = str(input_spec.get("name", ""))
    input_id = str(input_spec.get("id", ""))
    entry = entry_for_symbol(nomenclature, symbol=symbol or None, input_id=input_id or None)
    if entry is None:
        return merged

    if not merged.get("description"):
        merged["description"] = entry.description
    if merged.get("unit") in (None, "", "dimensionless") and entry.unit != "dimensionless":
        merged["unit"] = entry.unit
    if not merged.get("allowed_units") and entry.allowed_units:
        merged["allowed_units"] = list(entry.allowed_units)

    if entry.defaults and merged.get("default") is None:
        first = entry.defaults[0]
        merged["default"] = first.value
        if first.requires_confirmation:
            merged["requires_confirmation"] = True
            merged["source"] = merged.get("source", "default")
        merged["default_condition"] = first.condition

    return merged


def load_nomenclature_for_node(
    reader: StandardsReader,
    record_metadata: dict[str, Any],
) -> dict[str, NomenclatureEntry]:
    """Load nomenclature from explicit ref or dependency definition nodes."""
    refs: list[str] = []
    for item in record_metadata.get("inputs", []) or []:
        if isinstance(item, dict) and item.get("nomenclature_ref"):
            refs.append(str(item["nomenclature_ref"]))
    for dep in record_metadata.get("depends_on", []) or []:
        if isinstance(dep, dict) and dep.get("node_id"):
            dep_id = str(dep["node_id"])
            try:
                dep_record = reader.load(dep_id)
                if dep_record.metadata.get("type") == "definition":
                    refs.append(dep_id)
            except FileNotFoundError:
                continue

    merged: dict[str, NomenclatureEntry] = {}
    for node_id in dict.fromkeys(refs):
        merged.update(load_nomenclature(reader, node_id))
    return merged


def b36_reference(entry: NomenclatureEntry) -> dict[str, Any] | None:
    for ref in entry.references:
        standard = str(ref.get("standard", "")).lower().replace(".", "_")
        if "b36_10" in standard or standard == "asme_b36_10":
            return ref
    return None


def default_question(entry: NomenclatureEntry, default: NomenclatureDefault) -> str:
    label = entry.symbol
    if default.condition:
        return (
            f"For {label}: the default is {default.value} {default.unit} when "
            f"{default.condition}. Confirm or enter another value."
        )
    return (
        f"For {label}: the default is {default.value} {default.unit}. "
        f"Confirm or enter another value."
    )
