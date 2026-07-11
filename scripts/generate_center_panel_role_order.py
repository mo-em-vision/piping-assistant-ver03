#!/usr/bin/env python3
"""Generate contracts/center_panel_report_role_order.json from models.display_role."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.display_role import DISPLAY_ROLE_ORDER  # noqa: E402

OUTPUT = ROOT / "contracts" / "center_panel_report_role_order.json"


def main() -> int:
    payload = [role.value for role in DISPLAY_ROLE_ORDER]
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
