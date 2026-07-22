#!/usr/bin/env python3
"""Cursor hook: diff-based protected-path validation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.restricted_path_check import validate_repo  # noqa: E402


def _extract_user_message(payload: dict) -> str:
    for key in ("user_message", "prompt", "message", "text", "userMessage"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    conversation = payload.get("conversation")
    if isinstance(conversation, list):
        for item in reversed(conversation):
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content") or item.get("text")
                if isinstance(content, str) and content.strip():
                    return content
    return ""


def _revert_paths(paths: list[str]) -> None:
    for path in paths:
        subprocess.run(
            ["git", "-C", str(ROOT), "checkout", "--", path],
            capture_output=True,
            text=True,
            check=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="afterFileEdit")
    args = parser.parse_args()

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    user_message = _extract_user_message(payload)

    try:
        ok, violations = validate_repo(user_message, repo_root=ROOT)
    except Exception as exc:  # noqa: BLE001 — fail closed
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "agent_message": f"Protected-path gate failed closed: {exc}",
                }
            )
        )
        return 2

    if ok:
        print(json.dumps({"permission": "allow"}))
        return 0

    messages = [violation.format_agent_message() for violation in violations]
    agent_message = " | ".join(messages)
    revert_paths: list[str] = []
    for violation in violations:
        revert_paths.extend(violation.paths)
    if revert_paths and args.event in {"afterFileEdit", "stop"}:
        _revert_paths(revert_paths)

    print(
        json.dumps(
            {
                "permission": "deny",
                "agent_message": agent_message,
            }
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
