"""Tests for automatic E_j/E_c/W/Y coefficient table lookups."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.parameter_definitions import submit_task_input
from config.loader import CLIConfig
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.reference.parameter_keys import LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY
from engine.state.state_manager import TaskStateManager
from models.fact import SourceType, ValidationStatus, fact_scalar_value
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from engine.state.goal_projection import planning_projection
from tests.api.conftest import api_session_id
from tests.helpers.facts import legacy_input, populate_task_facts, set_fact_from_input
from tests.helpers.goals import task_with_planning

BASIC_CASTING_QUALITY_FACTOR_KEY = "basic_casting_quality_factor"

# Lookup-derived coefficients (symbols E_j, E_c, W, Y) must never be user-prompted.
_COEFFICIENT_PROMPT_KEYS = frozenset(
    {
        BASIC_CASTING_QUALITY_FACTOR_KEY,
        LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }
)

# Active on internal-pressure seamless-pipe Eq. (3a); E_c is out of scope for this path.
_INTERNAL_PRESSURE_RESOLVED_COEFFICIENTS: tuple[tuple[str, str], ...] = (
    (LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY, "E_j"),
    ("weld_joint_strength_reduction_factor_W", "W"),
    ("temperature_coefficient_Y", "Y"),
)

_INTERNAL_PRESSURE_SUBMISSIONS: dict[str, tuple[object, str | None]] = {
    "straight_pipe_section": (True, None),
    "pressure_loading": ("internal_pressure", None),
    "internal_design_gage_pressure": (8.0, "bar"),
    "nominal_pipe_size": ("6", None),
    "material_grade": ("SA-106B", None),
    "design_temperature": (38.0, "C"),
    "pipe_construction_type": ("Seamless pipe", None),
    "corrosion_allowance": (0.0, "mm"),
}


def _desktop_service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def _assert_internal_pressure_never_prompts_coefficients(state: dict) -> None:
    submittable = set(state.get("progress", {}).get("submittable_parameters") or [])
    overlap = sorted(submittable & _COEFFICIENT_PROMPT_KEYS)
    assert not overlap, (
        "E_j/E_c/W/Y coefficients must resolve from lookup/default logic, not user prompts; "
        f"found in submittable_parameters: {overlap}"
    )

    current_ask = state.get("current_ask") or {}
    if current_ask.get("kind") == "input":
        ask_id = str(current_ask.get("parameter_id") or "")
        assert ask_id not in _COEFFICIENT_PROMPT_KEYS, (
            "E_j/E_c/W/Y coefficients must not appear in current_ask on internal-pressure path; "
            f"got {ask_id!r}"
        )


def _fact_source_type(fact: dict) -> str:
    source_type = (fact.get("source") or {}).get("source_type")
    if isinstance(source_type, SourceType):
        return source_type.value
    text = str(source_type or "").strip()
    if text == str(SourceType.TABLE_LOOKUP):
        return SourceType.TABLE_LOOKUP.value
    return text


def _assert_coefficients_resolved_from_lookup(state: dict) -> None:
    facts = state.get("facts") or {}
    for key, symbol in _INTERNAL_PRESSURE_RESOLVED_COEFFICIENTS:
        fact = facts.get(key)
        assert fact is not None, f"missing resolved coefficient {symbol!r} fact {key!r}"
        source_type = _fact_source_type(fact)
        assert source_type == SourceType.TABLE_LOOKUP.value, (
            f"{symbol!r} ({key!r}) must resolve from table lookup, got source_type={source_type!r}"
        )
        assert fact.get("display_value") is not None

    assert BASIC_CASTING_QUALITY_FACTOR_KEY not in facts, (
        "E_c must not be materialized on internal-pressure seamless-pipe path"
    )


def _pipe_wall_task(
    manager: TaskStateManager,
    task_id: str,
    *,
    inputs: dict[str, EngineeringInput],
    missing: list[str],
) -> None:
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(task, inputs)
    planning = {
        "missing_inputs": [],
        "missing_assumptions": [],
        "missing_execution_assumptions": list(missing),
        "current_phase": "coefficient_resolution",
        "phase_missing": {"coefficient_resolution": list(missing)},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)


def test_joint_category_submission_resolves_weld_joint_efficiency_from_table(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    _pipe_wall_task(
        manager,
        "coeff-submit-test01",
        inputs={
            "material": EngineeringInput(
                "material",
                "A106 Gr B",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                "design_temperature",
                85.0,
                "C",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY: EngineeringInput(
                LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
                1.0,
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default=1.0,
                requires_confirmation=True,
            ),
        },
        missing=["pipe_construction_type", LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY],
    )

    submit_task_input(
        manager,
        "coeff-submit-test01",
        parameter="pipe_construction_type",
        value="Seamless pipe",
        unit=None,
        standards_root=standards_root,
    )

    task = manager.get_task("coeff-submit-test01")
    efficiency = task.fact_store.active_fact(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY)
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.CONFIRMED
    assert efficiency.source.source_type == SourceType.TABLE_LOOKUP
    assert fact_scalar_value(efficiency) == 1.0
    planning = planning_projection(task)
    assert LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY not in (
        planning["phase_missing"].get("coefficient_resolution") or []
    )


def test_apply_coefficient_lookups_waits_for_confirmed_joint_category(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("coeff-apply-test01", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(
        task,
        {
            "material": EngineeringInput(
                "material",
                "SA-106B",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "joint_category": EngineeringInput(
                "joint_category",
                "seamless",
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default="seamless",
                requires_confirmation=True,
            ),
            LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY: EngineeringInput(
                LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
                1.0,
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default=1.0,
                requires_confirmation=True,
            ),
        },
    )

    apply_coefficient_lookups(task, standards_root)

    efficiency = task.fact_store.active_fact(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY)
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.PENDING
    set_fact_from_input(
        task,
        legacy_input(
            "joint_category",
            "seamless",
            "dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    apply_coefficient_lookups(task, standards_root)
    efficiency = task.fact_store.active_fact(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY)
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.CONFIRMED
    assert efficiency.source.source_type == SourceType.TABLE_LOOKUP


def test_apply_coefficient_lookups_resolves_temperature_coefficient_y_from_table(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("coeff-y-lookup01", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(
        task,
        {
            "material_grade": EngineeringInput(
                "material_grade",
                "astm_a106_gr_b",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                "design_temperature",
                200.0,
                "F",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "metallurgical_group": EngineeringInput(
                "metallurgical_group",
                "ferritic_steels",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
    )

    apply_coefficient_lookups(task, standards_root)

    coefficient = task.fact_store.active_fact("temperature_coefficient_Y")
    assert coefficient is not None
    assert coefficient.validation.status == ValidationStatus.CONFIRMED
    assert coefficient.source.source_type == SourceType.TABLE_LOOKUP
    assert fact_scalar_value(coefficient) is not None


def test_apply_coefficient_lookups_resolves_y_when_thin_wall_boolean_fact_is_true(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("coeff-y-thin-wall01", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(
        task,
        {
            "material_grade": EngineeringInput(
                "material_grade",
                "astm_a106_gr_b",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                "design_temperature",
                85.0,
                "C",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "metallurgical_group": EngineeringInput(
                "metallurgical_group",
                "ferritic_steels",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
    )
    set_fact_from_input(
        task,
        legacy_input(
            input_id="thin_wall",
            value=True,
            unit="dimensionless",
            source=InputSource.SYSTEM,
            status=InputStatus.CONFIRMED,
        ),
    )

    apply_coefficient_lookups(task, standards_root)

    coefficient = task.fact_store.active_fact("temperature_coefficient_Y")
    assert coefficient is not None
    assert coefficient.source.source_type == SourceType.TABLE_LOOKUP
    assert fact_scalar_value(coefficient) == 0.4


def test_internal_pressure_path_never_prompts_for_coefficients(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Internal-pressure API journey never asks for E_j/E_c/W/Y; E_j/W/Y resolve from tables."""
    service = _desktop_service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    for _ in range(len(_INTERNAL_PRESSURE_SUBMISSIONS) + 4):
        if state.get("status") == "completed":
            break

        _assert_internal_pressure_never_prompts_coefficients(state)

        submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
        if not submittable:
            break

        current_ask = state.get("current_ask") or {}
        parameter_id = current_ask.get("parameter_id")
        if parameter_id not in submittable:
            parameter_id = submittable[0]

        if parameter_id not in _INTERNAL_PRESSURE_SUBMISSIONS:
            pytest.fail(
                "internal-pressure journey must not require direct E_j/E_c/W/Y submission; "
                f"unexpected prompt {parameter_id!r} (submittable={submittable})"
            )

        value, unit = _INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )

    _assert_internal_pressure_never_prompts_coefficients(state)
    assert state.get("status") == "completed"
    _assert_coefficients_resolved_from_lookup(state)

    manager = service._store_for(session_id).load_state_manager()
    planning = planning_projection(manager.get_task(task_id))
    phase_missing = planning.get("phase_missing") or {}
    for phase_id, fields in phase_missing.items():
        if not isinstance(fields, list):
            continue
        overlap = sorted(set(fields) & _COEFFICIENT_PROMPT_KEYS)
        assert not overlap, (
            f"E_j/E_c/W/Y outputs must not remain in phase_missing[{phase_id!r}]: {overlap}"
        )
