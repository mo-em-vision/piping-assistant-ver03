"""Dev-only guard for inspection features."""

from __future__ import annotations

import os


def inspection_enabled() -> bool:
    """True when developer inspection API and enriched payloads are enabled."""
    return os.environ.get("DEV_INSPECTION_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
