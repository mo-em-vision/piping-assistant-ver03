"""Build standards table source payloads for the desktop UI."""



from __future__ import annotations



from typing import Any



from engine.reference.standards_reader import StandardsReader



_DEFAULT_STANDARD_LABEL = "ASME B31.3"





def _column_label(key: str) -> str:

    return key.replace("_", " ").strip().title()





def _flatten_table_rows(data: dict[str, Any]) -> list[dict[str, Any]]:

    rows = data.get("rows") or []

    if isinstance(rows, list) and rows:

        return [row for row in rows if isinstance(row, dict)]



    materials = data.get("materials") or {}

    if not isinstance(materials, dict):

        return []



    flattened: list[dict[str, Any]] = []

    for material_key, material_data in materials.items():

        if not isinstance(material_data, dict):

            continue

        for row in material_data.get("rows", []) or []:

            if not isinstance(row, dict):

                continue

            flattened.append(
                {
                    "material_id": material_key,
                    "material": str(material_data.get("display_name", material_key)),
                    **row,
                }
            )

    return flattened





def table_source_payload(reader: StandardsReader, table_id: str) -> dict[str, Any]:

    path, data = reader.load_table_by_id(table_id)

    resolved_id = str(data.get("table_id") or table_id).strip()

    title = str(data.get("title") or resolved_id).strip()

    rows = _flatten_table_rows(data)



    keys = data.get("keys") or []

    if isinstance(keys, list) and keys:

        columns = [{"key": str(key), "label": _column_label(str(key))} for key in keys]

    elif rows and isinstance(rows[0], dict):

        columns = [{"key": str(key), "label": _column_label(str(key))} for key in rows[0]]

    else:

        columns = []



    normalized_rows: list[dict[str, Any]] = []

    for row in rows:

        normalized_rows.append({str(key): value for key, value in row.items()})



    source_path = "standards_tables.db"

    if path.name:

        source_path = path.name



    return {

        "table_id": resolved_id,

        "title": title,

        "standard": _DEFAULT_STANDARD_LABEL,

        "source_path": source_path,

        "columns": columns,

        "rows": normalized_rows,

        "hover_excerpt": title,

    }


