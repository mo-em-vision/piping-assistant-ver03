"""Shared helpers for normalizing chat source citations."""

from __future__ import annotations

from typing import Any


def normalize_chat_sources(
    llm_sources: Any,
    fallback_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(llm_sources, list) and llm_sources:
        normalized: list[dict[str, Any]] = []
        for item in llm_sources:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip()
            source_id = str(
                item.get("id") or item.get("table_id") or item.get("node_id") or ""
            ).strip()
            label = str(item.get("label") or "").strip()
            if not kind or not source_id or not label:
                continue
            entry: dict[str, Any] = {
                "kind": kind,
                "id": source_id,
                "label": label,
            }
            for key in ("standard", "paragraph", "node_id", "table_id"):
                value = item.get(key)
                if value:
                    entry[key] = str(value)
            normalized.append(entry)
        if normalized:
            return normalized
    return [dict(source) for source in fallback_sources]
