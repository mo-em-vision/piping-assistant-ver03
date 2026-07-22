"""Emit planner requirements from PARAM resolution-branch metadata."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_store import GraphStore
from engine.graph.resolution_branches import (
    branch_table_lookup_resolution,
    has_resolution_branches,
    resolution_branch_fact_key,
    resolution_branches_from_metadata,
    via_parameter_keys,
)
from engine.planner.question_spec_builder import build_question_spec
from engine.reference.parameter_keys import (
    canonical_parameter_key,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from models.engineering_plan import PlanRequirement, QuestionSpec, RequirementAlternative

_LOOKUP_SUFFIX = "_lookup"


def requirement_id(field: str) -> str:
    return f"REQ-{canonical_parameter_key(field)}"


def lookup_requirement_id(field: str) -> str:
    return f"REQ-{canonical_parameter_key(field)}{_LOOKUP_SUFFIX}"


def _replace_requirement_preserving_order(
    requirements: dict[str, PlanRequirement],
    *,
    old_id: str,
    new_req: PlanRequirement,
) -> None:
    keys = list(requirements.keys())
    if old_id not in keys:
        requirements[new_req.id] = new_req
        return
    rebuilt: dict[str, PlanRequirement] = {}
    for key in keys:
        if key == old_id:
            rebuilt[new_req.id] = new_req
        else:
            rebuilt[key] = requirements[key]
    requirements.clear()
    requirements.update(rebuilt)


_LEGACY_RESOLUTION_REQUIREMENT_IDS = {
    "outside_diameter": "REQ-diameter_resolution",
}

_LEGACY_BRANCH_LOOKUP_REQUIREMENT_IDS = {
    "outside_diameter": "REQ-outside_diameter_lookup",
}

_LEGACY_ALTERNATIVE_IDS = {
    ("outside_diameter", "direct_od"): "ALT-direct-outside-diameter",
    ("outside_diameter", "nps_lookup"): "ALT-nps-lookup",
}

_OUTSIDE_DIAMETER_LEGACY_MODE_FIELDS = ("d_input_mode", "diameter_input_mode")


def resolution_requirement_id(anchor_key: str) -> str:
    """Stable requirement id for a resolution-branch anchor parameter."""
    canonical = canonical_parameter_key(anchor_key)
    legacy = _LEGACY_RESOLUTION_REQUIREMENT_IDS.get(canonical)
    if legacy:
        return legacy
    return requirement_id(canonical)


def branch_lookup_requirement_id(anchor_key: str) -> str:
    """Lookup-output requirement id for a resolution-branch anchor."""
    canonical = canonical_parameter_key(anchor_key)
    legacy = _LEGACY_BRANCH_LOOKUP_REQUIREMENT_IDS.get(canonical)
    if legacy:
        return legacy
    return lookup_requirement_id(canonical)


# Backward-compatible exports for existing imports.
_DIAMETER_RESOLUTION_ID = resolution_requirement_id("outside_diameter")
_OUTSIDE_DIAMETER_LOOKUP_ID = branch_lookup_requirement_id("outside_diameter")


def alternative_id(anchor_key: str, branch_id: str) -> str:
    canonical_anchor = canonical_parameter_key(anchor_key)
    branch = str(branch_id or "").strip()
    legacy = _LEGACY_ALTERNATIVE_IDS.get((canonical_anchor, branch))
    if legacy:
        return legacy
    return f"ALT-{branch.replace('_', '-')}"


def _param_metadata_block(metadata: dict[str, Any]) -> dict[str, Any]:
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        return nested
    return metadata


def _is_resolution_branch_param(metadata: dict[str, Any]) -> bool:
    block = _param_metadata_block(metadata)
    composer_input = str(block.get("composer_input") or metadata.get("composer_input") or "").strip()
    return composer_input == "resolution_branch" and has_resolution_branches(metadata)


def _resolution_branch_question(metadata: dict[str, Any], anchor_key: str) -> str:
    block = _param_metadata_block(metadata)
    question = str(
        block.get("resolution_branch_question")
        or metadata.get("resolution_branch_question")
        or ""
    ).strip()
    if question:
        return question
    name = str(metadata.get("name") or anchor_key).strip()
    return name or anchor_key.replace("_", " ").title()


def _branch_alternative(
    store: GraphStore,
    *,
    anchor_key: str,
    branch: dict[str, Any],
) -> RequirementAlternative | None:
    branch_id = str(branch.get("id") or "").strip()
    if not branch_id:
        return None
    label = str(branch.get("label") or branch_id).strip()
    method = str(branch.get("method") or "").strip()
    via_keys = via_parameter_keys(store, branch)
    canonical_anchor = canonical_parameter_key(anchor_key)

    if method == "user_input":
        fields = via_keys or [canonical_anchor]
        return RequirementAlternative(
            id=alternative_id(canonical_anchor, branch_id),
            label=label,
            fields=fields,
            resolves=canonical_anchor,
            method="direct_input",
        )

    if method in {"table_lookup", "lookup"}:
        if not via_keys:
            return None
        return RequirementAlternative(
            id=alternative_id(canonical_anchor, branch_id),
            label=label,
            fields=via_keys,
            resolves=canonical_anchor,
            method="lookup",
        )

    if via_keys:
        return RequirementAlternative(
            id=alternative_id(canonical_anchor, branch_id),
            label=label,
            fields=via_keys,
            resolves=canonical_anchor,
            method="selection",
        )
    return None


def _lookup_branch_specs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        branch
        for branch in resolution_branches_from_metadata(metadata)
        if str(branch.get("method") or "").strip() in {"table_lookup", "lookup"}
    ]


def _via_keys_for_branches(store: GraphStore, metadata: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for branch in resolution_branches_from_metadata(metadata):
        keys.update(via_parameter_keys(store, branch))
    return keys


def _iter_resolution_branch_anchors(
    store: GraphStore,
    *,
    execution_order: list[str],
    planning_fields: set[str],
) -> list[tuple[str, str, dict[str, Any]]]:
    """Return (anchor_key, param_node_id, metadata) for active resolution-branch anchors."""
    anchors: list[tuple[str, str, dict[str, Any]]] = []
    seen: set[str] = set()

    def add_anchor(anchor_key: str, param_node_id: str, metadata: dict[str, Any]) -> None:
        canonical = canonical_parameter_key(anchor_key)
        if not canonical or canonical in seen:
            return
        if not _is_resolution_branch_param(metadata):
            return
        via_keys = _via_keys_for_branches(store, metadata)
        if canonical not in planning_fields and not via_keys.intersection(planning_fields):
            return
        seen.add(canonical)
        anchors.append((canonical, param_node_id, metadata))

    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        metadata = dict(node.metadata or {})
        anchor_key = canonical_parameter_key(str(metadata.get("key") or ""))
        if anchor_key:
            add_anchor(anchor_key, node_id, metadata)

    for field in planning_fields:
        param_node_id = param_node_id_for_input(field)
        metadata = load_parameter_node_metadata(param_node_id)
        if not isinstance(metadata, dict):
            continue
        anchor_key = canonical_parameter_key(str(metadata.get("key") or field))
        add_anchor(anchor_key, param_node_id, metadata)

    return anchors


def _build_resolution_question_spec(
    anchor_key: str,
    metadata: dict[str, Any],
) -> QuestionSpec:
    branch_field = resolution_branch_fact_key(anchor_key)
    return QuestionSpec(
        field=branch_field,
        label=_resolution_branch_question(metadata, anchor_key),
        expected_value_class="selection",
        priority=100,
        ask_policy="ask_now",
    )


def _emit_via_parameter_requirements(
    requirements: dict[str, PlanRequirement],
    *,
    store: GraphStore,
    metadata: dict[str, Any],
    anchor_key: str,
    resolution_req_id: str,
    root_goal_id: str,
    phase: str,
    planning_fields: set[str],
) -> list[str]:
    emitted: list[str] = []
    for branch in resolution_branches_from_metadata(metadata):
        method = str(branch.get("method") or "").strip()
        if method not in {"table_lookup", "lookup", "user_input"}:
            continue
        for via_key in via_parameter_keys(store, branch):
            if (
                via_key not in planning_fields
                and via_key != anchor_key
                and method == "user_input"
            ):
                continue
            via_req_id = requirement_id(via_key)
            if via_req_id in requirements:
                emitted.append(via_req_id)
                continue
            requirements[via_req_id] = PlanRequirement(
                id=via_req_id,
                field=via_key,
                parameter_node_id=param_node_id_for_input(via_key),
                requirement_class="user_input",
                status="missing",
                phase=phase,
                required_by=[resolution_req_id],
                depends_on=[],
                question_spec=build_question_spec(via_key, ask_policy="ask_if_needed"),
                resolution={
                    "method": "user_input",
                    "output_field": via_key,
                    "role": "lookup_key" if method in {"table_lookup", "lookup"} else "branch_input",
                },
            )
            emitted.append(via_req_id)
    return emitted


def _emit_branch_lookup_requirement(
    requirements: dict[str, PlanRequirement],
    *,
    store: GraphStore,
    metadata: dict[str, Any],
    anchor_key: str,
    param_node_id: str,
    resolution_req_id: str,
    phase: str,
    via_req_ids: list[str],
) -> None:
    lookup_branches = _lookup_branch_specs(metadata)
    if not lookup_branches:
        return

    lookup_id = branch_lookup_requirement_id(anchor_key)
    if lookup_id in requirements:
        return

    branch = lookup_branches[0]
    lookup_node_id = str(branch.get("lookup") or "").strip()
    resolution = branch_table_lookup_resolution(
        store,
        param_node_id,
        metadata,
        branch,
    ) or {
        "method": "lookup",
        "source_node_id": lookup_node_id,
        "output_field": anchor_key,
        "role": "lookup_output",
    }
    if lookup_node_id and not resolution.get("source_node_id"):
        resolution["source_node_id"] = lookup_node_id

    requirements[lookup_id] = PlanRequirement(
        id=lookup_id,
        field=anchor_key,
        parameter_node_id=param_node_id,
        requirement_class="table_lookup",
        status="blocked",
        phase=phase,
        required_by=[resolution_req_id],
        depends_on=via_req_ids,
        resolution=resolution,
    )


def maybe_emit_resolution_branch_requirements(
    requirements: dict[str, PlanRequirement],
    *,
    store: GraphStore,
    root_goal_id: str,
    planning_fields: set[str],
    execution_order: list[str],
    phase: str = "parameter_gathering",
) -> None:
    """Replace gatherable anchor user requirements with resolution-branch alternatives."""
    for anchor_key, param_node_id, metadata in _iter_resolution_branch_anchors(
        store,
        execution_order=execution_order,
        planning_fields=planning_fields,
    ):
        resolution_req_id = resolution_requirement_id(anchor_key)
        if resolution_req_id in requirements:
            continue

        alternatives: list[RequirementAlternative] = []
        for branch in resolution_branches_from_metadata(metadata):
            alt = _branch_alternative(store, anchor_key=anchor_key, branch=branch)
            if alt is not None:
                alternatives.append(alt)
        if len(alternatives) < 2:
            continue

        resolution_req = PlanRequirement(
            id=resolution_req_id,
            field=anchor_key,
            parameter_node_id=param_node_id,
            requirement_class="user_input",
            status="missing",
            phase=phase,
            required_by=[root_goal_id],
            depends_on=[],
            alternatives=alternatives,
            question_spec=_build_resolution_question_spec(anchor_key, metadata),
        )
        _replace_requirement_preserving_order(
            requirements,
            old_id=requirement_id(anchor_key),
            new_req=resolution_req,
        )

        via_req_ids = _emit_via_parameter_requirements(
            requirements,
            store=store,
            metadata=metadata,
            anchor_key=anchor_key,
            resolution_req_id=resolution_req_id,
            root_goal_id=resolution_req_id,
            phase=phase,
            planning_fields=planning_fields,
        )
        _emit_branch_lookup_requirement(
            requirements,
            store=store,
            metadata=metadata,
            anchor_key=anchor_key,
            param_node_id=param_node_id,
            resolution_req_id=resolution_req_id,
            phase=phase,
            via_req_ids=via_req_ids,
        )


def _active_branch_id(anchor_key: str, existing_inputs: dict) -> str | None:
    from engine.graph.resolution_branches import active_resolution_branch_id
    from engine.reference.parameter_keys import parameter_is_ready

    canonical = canonical_parameter_key(anchor_key)
    active = active_resolution_branch_id(canonical, existing_inputs)
    if active:
        return str(active)

    if canonical != "outside_diameter":
        if parameter_is_ready(existing_inputs, canonical):
            return None
        return None

    for mode_field in _OUTSIDE_DIAMETER_LEGACY_MODE_FIELDS:
        mode = field_value(mode_field, existing_inputs)
        if mode in {"direct_od", "nps_lookup", "direct_id"}:
            return str(mode)
    if parameter_is_ready(existing_inputs, "outside_diameter"):
        return "direct_od"
    if parameter_is_ready(existing_inputs, "nominal_pipe_size"):
        return "nps_lookup"
    if parameter_is_ready(existing_inputs, "inside_diameter"):
        return "direct_id"
    return None


def _alternative_for_branch(
    req: PlanRequirement,
    branch_id: str,
) -> RequirementAlternative | None:
    target = str(branch_id or "").strip()
    if not target:
        return None
    expected_id = alternative_id(req.field, target)
    for alt in req.alternatives or []:
        if alt.id == expected_id:
            return alt
    return None


def apply_resolution_branch_statuses(
    requirements: dict[str, PlanRequirement],
    *,
    existing_inputs: dict,
) -> None:
    """Update resolution-branch, lookup-output, and via-parameter requirement statuses."""
    from engine.reference.parameter_keys import parameter_is_ready

    for req in requirements.values():
        if not req.alternatives:
            continue

        anchor_key = canonical_parameter_key(req.field)
        branch_id = _active_branch_id(anchor_key, existing_inputs)
        active_alt = _alternative_for_branch(req, branch_id) if branch_id else None
        lookup_req = requirements.get(branch_lookup_requirement_id(anchor_key))

        if branch_id and active_alt is not None:
            if active_alt.method == "direct_input":
                if parameter_is_ready(existing_inputs, anchor_key):
                    req.status = "resolved"
                elif branch_id == "direct_id" and parameter_is_ready(existing_inputs, "inside_diameter"):
                    req.status = "resolved"
            elif active_alt.method == "lookup":
                req.status = "resolved"

        if lookup_req is None:
            continue

        lookup_active = active_alt is not None and active_alt.method == "lookup"

        if not lookup_active:
            lookup_req.status = "not_applicable"
        elif parameter_is_ready(existing_inputs, anchor_key):
            lookup_req.status = "resolved"
        else:
            blocked = any(
                not parameter_is_ready(existing_inputs, field)
                for alt in req.alternatives or []
                if alt.method == "lookup"
                for field in alt.fields
            )
            lookup_req.status = "blocked" if blocked else "ready"

        for alt in req.alternatives or []:
            for field in alt.fields:
                via_req = requirements.get(requirement_id(field))
                if via_req is None:
                    continue
                if active_alt is not None and alt.id == active_alt.id:
                    if parameter_is_ready(existing_inputs, field):
                        via_req.status = "resolved"
                    elif active_alt.method == "lookup":
                        via_req.status = "missing"
                else:
                    via_req.status = "not_applicable"
