"""ASTM material search for desktop UI autocomplete."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _grade_alias_map(table: dict[str, Any]) -> dict[str, str]:
    aliases = table.get("aliases", {}).get("grade", {}) or {}
    return {str(alias): str(target) for alias, target in aliases.items()}


def _aliases_for_grade(
    grade_key: str,
    row: dict[str, Any],
    grade_aliases: dict[str, str],
) -> list[str]:
    values = [grade_key, str(row.get("display_name", grade_key))]
    values.extend(str(alias) for alias in row.get("aliases", []) or [])
    for alias, target in grade_aliases.items():
        if str(target) == grade_key:
            values.append(str(alias))
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def search_astm_materials(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return ASTM material matches when query is at least three characters."""
    needle = query.strip().lower()
    if len(needle) < 3:
        return []

    astm_root = standards_root / "astm"
    if not astm_root.is_dir():
        return []

    matches: list[tuple[int, str, str, str, str]] = []
    seen: set[str] = set()

    for pack_dir in sorted(astm_root.iterdir()):
        if not pack_dir.is_dir():
            continue

        table_path = pack_dir / "tables" / "material_properties.yaml"
        if not table_path.exists():
            continue

        table = yaml.safe_load(table_path.read_text(encoding="utf-8")) or {}
        specification = str(table.get("standard", pack_dir.name))
        grade_aliases = _grade_alias_map(table)
        materials = table.get("materials", {}) or {}

        for grade_key, row in materials.items():
            if not isinstance(row, dict):
                continue

            display_name = str(row.get("display_name", grade_key))
            for candidate in _aliases_for_grade(grade_key, row, grade_aliases):
                candidate_lower = candidate.lower()
                if needle not in candidate_lower:
                    continue

                dedupe_key = f"{specification}:{candidate_lower}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                score = 0 if candidate_lower.startswith(needle) else 1
                matches.append((score, candidate, display_name, pack_dir.name, specification))

    matches.sort(key=lambda item: (item[0], item[3].lower(), item[1].lower()))
    return [
        {
            "value": value,
            "label": label,
            "standard": standard_slug,
            "specification": specification,
        }
        for _, value, label, standard_slug, specification in matches[:limit]
    ]
