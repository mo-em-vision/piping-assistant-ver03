"""Build standards table source payloads for the desktop UI."""



from __future__ import annotations



from typing import Any



from api.node_context import revision_year_from_metadata
from engine.reference.standards_reader import StandardsReader
from engine.reference.standards_tables import flatten_lookup_table_rows
from engine.reference.standards_tables import flatten_lookup_table_rows



_DEFAULT_STANDARD_LABEL = "ASME B31.3"





def _flatten_table_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return flatten_lookup_table_rows(data)


def _column_label(key: str) -> str:
    labels = {
        "temperature_c": "Temperature (°C)",
        "design_temperature": "Design Temperature (°F)",
        "coefficient_Y": "Coefficient Y",
        "material_id": "Material ID",
        "material": "Material",
        "base_metal_group": "Base Metal Group",
        "supplementary_examination": "Supplementary Examination in Accordance With Note(s)",
        "quality_factor_E_c": "Factor, E_c",
        "quality_factor_E": "Quality Factor E",
        "description": "Description",
    }
    return labels.get(key, key.replace("_", " ").strip().title())


def _collect_column_keys(data: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    keys = data.get("keys") or []
    if isinstance(keys, list):
        for key in keys:
            normalized = str(key).strip()
            if normalized and normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)

    for row in rows:
        for key in row:
            normalized = str(key).strip()
            if normalized and normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)

    preferred = (
        "base_metal_group",
        "material",
        "description",
        "supplementary_examination",
        "temperature_c",
        "design_temperature",
        "coefficient_Y",
        "quality_factor_E_c",
        "quality_factor_E",
        "allowable_stress",
        "joint_category",
        "class",
        "row_id",
        "material_id",
    )
    rank = {key: index for index, key in enumerate(preferred)}
    return sorted(ordered, key=lambda key: (rank.get(key, len(preferred)), key))


def table_source_payload(reader: StandardsReader, table_id: str) -> dict[str, Any]:

    path, data = reader.load_table_by_id(table_id)

    resolved_id = str(data.get("table_id") or table_id).strip()

    title = str(data.get("title") or resolved_id).strip()

    description = str(data.get("description") or "").strip() or None

    rows = _flatten_table_rows(data)

    column_keys = _collect_column_keys(data, rows)
    if column_keys:
        columns = [{"key": key, "label": _column_label(key)} for key in column_keys]
    else:
        columns = []



    normalized_rows: list[dict[str, Any]] = []

    for row in rows:

        normalized_rows.append({str(key): value for key, value in row.items()})



    source_path = "standards_tables.db"

    if path.name:

        source_path = path.name

    revision_year = None
    source_node = data.get("source_node")
    if source_node:
        try:
            record = reader.load(str(source_node))
            revision_year = revision_year_from_metadata(record.metadata)
        except FileNotFoundError:
            pass

    return {

        "table_id": resolved_id,

        "title": title,

        "description": description,

        "standard": _DEFAULT_STANDARD_LABEL,

        "revision_year": revision_year,

        "source_path": source_path,

        "columns": columns,

        "rows": normalized_rows,

        "hover_excerpt": description or title,

    }


