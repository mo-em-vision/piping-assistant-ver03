"""Graph integrity checks for developer inspection."""

from __future__ import annotations

from engine.inspection.integrity import run_integrity_checks


def test_integrity_checks_return_four_results(standards_reader) -> None:
    checks = run_integrity_checks(standards_reader)
    assert len(checks) == 4
    ids = {check.check_id for check in checks}
    assert ids == {
        "rename_node_id",
        "rename_display_title",
        "move_node_folder",
        "disable_node",
    }
