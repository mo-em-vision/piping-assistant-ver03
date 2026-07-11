#!/usr/bin/env python3
"""One-time migration of persisted display roles to canonical DisplayRole shape."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.legacy_display_role_migration import (  # noqa: E402
    migrate_equation_trace_key,
    migrate_transcript_payload,
)

FLOW_GUIDANCE_TRANSCRIPT_KEY = "flow_guidance_transcript"


def _migrate_task_outputs(outputs: dict) -> tuple[dict, bool]:
    changed = False
    migrated = dict(outputs)

    transcript = migrated.get(FLOW_GUIDANCE_TRANSCRIPT_KEY)
    if isinstance(transcript, list):
        new_transcript: list[dict] = []
        for item in transcript:
            if not isinstance(item, dict):
                new_transcript.append(item)
                continue
            block = dict(item)
            payload = block.get("payload")
            if isinstance(payload, dict):
                new_payload = migrate_transcript_payload(payload)
                if new_payload != payload:
                    changed = True
                block["payload"] = new_payload
            new_transcript.append(block)
        migrated[FLOW_GUIDANCE_TRANSCRIPT_KEY] = new_transcript

    trace_keys = migrated.get("_equation_trace_keys")
    if isinstance(trace_keys, list):
        new_keys = [migrate_equation_trace_key(str(key)) for key in trace_keys]
        if new_keys != trace_keys:
            changed = True
            migrated["_equation_trace_keys"] = new_keys

    return migrated, changed


def migrate_sessions_dir(sessions_dir: Path, *, dry_run: bool = False) -> int:
    tasks_files = list(sessions_dir.rglob("tasks.json"))
    updated_files = 0

    for path in tasks_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        file_changed = False

        if isinstance(payload, dict) and "tasks" in payload:
            tasks = payload.get("tasks") or []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                outputs = task.get("outputs")
                if not isinstance(outputs, dict):
                    continue
                migrated_outputs, changed = _migrate_task_outputs(outputs)
                if changed:
                    task["outputs"] = migrated_outputs
                    file_changed = True
        elif isinstance(payload, list):
            for task in payload:
                if not isinstance(task, dict):
                    continue
                outputs = task.get("outputs")
                if not isinstance(outputs, dict):
                    continue
                migrated_outputs, changed = _migrate_task_outputs(outputs)
                if changed:
                    task["outputs"] = migrated_outputs
                    file_changed = True

        if file_changed:
            updated_files += 1
            if not dry_run:
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"{'Would update' if dry_run else 'Updated'} {updated_files} tasks.json file(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path.home() / "AppData" / "Roaming" / "engineering-desktop-app" / "sessions",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return migrate_sessions_dir(args.sessions_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
