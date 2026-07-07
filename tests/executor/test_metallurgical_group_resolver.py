"""Tests for metallurgical group derivation from material catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.metallurgical_group_resolver import apply_metallurgical_group_lookup
from engine.reference.material_catalog_db import GlobalMaterialCatalog
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import store_fact
from models.fact import FactClass, SourceType, ValidationStatus, build_categorical_fact
from models.fact import FactProvenance, FactSource
from models.task import TaskStatus


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def _store_material_grade(task, material_id: str) -> None:
    fact = build_categorical_fact(
        key="material_grade",
        parameter="PARAM-material-grade",
        label=material_id,
        normalized_key=material_id,
        fact_class=FactClass.USER_SUPPLIED,
        source=FactSource(source_type=SourceType.USER_INPUT, source_id="USER"),
        provenance=FactProvenance(task_id=task.task_id, created_by="user"),
        validation_status=ValidationStatus.CONFIRMED,
    )
    store_fact(task, fact)


def test_apply_metallurgical_group_lookup_sets_ferritic_for_a106(standards_root: Path) -> None:
    catalog = GlobalMaterialCatalog(standards_root)
    if not catalog.exists:
        catalog.rebuild()

    manager = TaskStateManager()
    task = manager.create_task("metallurgical-a106", status=TaskStatus.AWAITING_INPUT)
    _store_material_grade(task, "astm_a106_gr_b")

    apply_metallurgical_group_lookup(task, standards_root)

    fact = task.fact_store.active_fact("metallurgical_group")
    assert fact is not None
    assert fact.value.label == "ferritic_steels"
    assert fact.fact_class == FactClass.SYSTEM_GENERATED


def test_apply_metallurgical_group_lookup_sets_austenitic_for_a312(standards_root: Path) -> None:
    catalog = GlobalMaterialCatalog(standards_root)
    if not catalog.exists:
        catalog.rebuild()

    manager = TaskStateManager()
    task = manager.create_task("metallurgical-a312", status=TaskStatus.AWAITING_INPUT)
    _store_material_grade(task, "astm_a312_tp316")

    apply_metallurgical_group_lookup(task, standards_root)

    fact = task.fact_store.active_fact("metallurgical_group")
    assert fact is not None
    assert fact.value.label == "austenitic_steels"
