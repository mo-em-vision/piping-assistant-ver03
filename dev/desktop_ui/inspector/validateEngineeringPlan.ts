import type { EngineeringPlanDto } from '@/types/backend/inspection'

export type EngineeringPlanValidationResult = {
  valid: boolean
  errors: string[]
  warnings: string[]
}

const CANONICAL_TOP_LEVEL_KEYS = new Set([
  'plan_id',
  'task_id',
  'workflow_id',
  'root_goal',
  'requirements',
  'dependencies',
  'input_strategy',
  'phases',
  'graph',
  'traversal',
  'legacy_goal_map',
  'debug',
])

const REQUIRED_SECTIONS = [
  'root_goal',
  'requirements',
  'dependencies',
  'input_strategy',
  'phases',
  'graph',
  'traversal',
] as const

const LEGACY_REQUIREMENT_FIELDS = new Set([
  'goal_class',
  'satisfaction',
  'state',
  'metadata',
  'edges',
  'name',
  'target_parameter',
  'question',
  'provenance',
  'authority',
  'workflow_id',
  'task_id',
  'parent_goal',
])

const PIPE_WALL_LOOKUP_IDS = [
  'REQ-allowable_stress_lookup',
  'REQ-basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes_lookup',
  'REQ-temperature_coefficient_Y_lookup',
  'REQ-weld_strength_reduction_factor_W_lookup',
  'REQ-metallurgical_group_lookup',
] as const

const PIPE_WALL_EQUATION_IDS = ['REQ-required_wall_thickness', 'REQ-minimum_required_thickness_eq'] as const

const FRESH_PIPE_WALL_HARD_BLOCKED = ['REQ-straight_pipe_section', 'REQ-pressure_design_case'] as const

function isPipeWallWorkflow(workflowId: string | undefined): boolean {
  if (!workflowId) {
    return false
  }
  const slug = workflowId.replace(/-/g, '_')
  return slug === 'pipe_wall_thickness' || slug === 'pipe_wall_thickness_design'
}

function isFlatGoalMap(plan: Record<string, unknown>): boolean {
  const keys = Object.keys(plan)
  const hasFlatIds = keys.some((key) => key.startsWith('GOAL-') || key.startsWith('REQ-'))
  return hasFlatIds && !('requirements' in plan)
}

export function validateEngineeringPlan(
  plan: EngineeringPlanDto | Record<string, unknown> | null | undefined,
): EngineeringPlanValidationResult {
  const errors: string[] = []
  const warnings: string[] = []

  if (!plan || typeof plan !== 'object') {
    return { valid: false, errors: ['engineering_plan payload is empty.'], warnings }
  }

  const raw = plan as Record<string, unknown>

  if (isFlatGoalMap(raw)) {
    return {
      valid: false,
      errors: ['Canonical engineering_plan must not be a flat top-level GOAL-*/REQ-* map.'],
      warnings,
    }
  }

  for (const key of REQUIRED_SECTIONS) {
    if (!(key in raw)) {
      errors.push(`engineering_plan missing required section: ${key}`)
    }
  }

  const unexpected = Object.keys(raw).filter((key) => !CANONICAL_TOP_LEVEL_KEYS.has(key))
  if (unexpected.length > 0 && !('requirements' in raw)) {
    errors.push(`engineering_plan has unexpected top-level keys: ${unexpected.join(', ')}`)
  }

  if (errors.length > 0) {
    return { valid: false, errors, warnings }
  }

  const engineeringPlan = plan as EngineeringPlanDto
  const requirements = engineeringPlan.requirements ?? {}
  const rootGoal = engineeringPlan.root_goal

  if (!rootGoal?.id) {
    errors.push('engineering_plan.root_goal is required.')
  }

  if (!requirements || Object.keys(requirements).length === 0) {
    errors.push('engineering_plan.requirements must not be empty.')
  }

  if (!engineeringPlan.input_strategy) {
    errors.push('engineering_plan.input_strategy is required.')
  }

  if (!engineeringPlan.phases?.length) {
    errors.push('engineering_plan.phases must not be empty.')
  }

  if (!engineeringPlan.graph) {
    errors.push('engineering_plan.graph is required.')
  }

  if (!engineeringPlan.traversal) {
    errors.push('engineering_plan.traversal is required.')
  }

  if (!engineeringPlan.dependencies?.length) {
    errors.push('engineering_plan.dependencies must not be empty.')
  }

  const knownIds = new Set([rootGoal?.id, ...Object.keys(requirements)].filter(Boolean) as string[])

  for (const blockedId of rootGoal?.blocked_by ?? []) {
    if (!knownIds.has(blockedId)) {
      errors.push(`blocked_by references unknown requirement: ${blockedId}`)
    }
  }

  for (const provisionalId of rootGoal?.provisional_blocked_by ?? []) {
    if (!knownIds.has(provisionalId)) {
      errors.push(`provisional_blocked_by references unknown requirement: ${provisionalId}`)
    }
  }

  for (const [requirementId, requirement] of Object.entries(requirements)) {
    for (const legacyField of LEGACY_REQUIREMENT_FIELDS) {
      if (legacyField in requirement) {
        errors.push(
          `Requirement ${requirementId} must not include legacy goal field: ${legacyField}`,
        )
      }
    }
  }

  const diameter = requirements['REQ-diameter_resolution'] as
    | { alternatives?: Array<{ id: string; method: string }> }
    | undefined
  if (diameter?.alternatives?.length !== 2) {
    errors.push(
      'REQ-diameter_resolution must expose exactly two alternatives (direct outside diameter and NPS lookup).',
    )
  } else {
    const altIds = new Set(diameter.alternatives.map((alt) => alt.id))
    const methods = new Set(diameter.alternatives.map((alt) => alt.method))
    if (!altIds.has('ALT-direct-outside-diameter') || !altIds.has('ALT-nps-lookup')) {
      errors.push(
        'REQ-diameter_resolution must include ALT-direct-outside-diameter and ALT-nps-lookup.',
      )
    }
    if (!methods.has('direct_input') || !methods.has('lookup')) {
      errors.push(
        'REQ-diameter_resolution alternatives must include direct_input and lookup methods.',
      )
    }
  }

  const odBlocked = (rootGoal?.blocked_by ?? []).filter(
    (id) => id === 'REQ-outside_diameter' || id === 'REQ-nominal_pipe_size',
  )
  if (odBlocked.length > 1) {
    errors.push('Root goal must not be blocked by both outside_diameter and nominal_pipe_size.')
  }

  const strategy = engineeringPlan.input_strategy
  if (strategy?.mode === 'single_next_question') {
    if ((strategy.next_fields?.length ?? 0) > 1) {
      errors.push(
        'input_strategy.next_fields must contain at most one field in single_next_question mode.',
      )
    }
    const activePhases = (engineeringPlan.phases ?? []).filter((phase) => phase.status === 'active')
    if (activePhases.length > 1) {
      errors.push('At most one plan phase may be active in single_next_question mode.')
    }
  }

  if (isPipeWallWorkflow(engineeringPlan.workflow_id)) {
    for (const lookupId of PIPE_WALL_LOOKUP_IDS) {
      if (!(lookupId in requirements)) {
        errors.push(`Pipe wall plan missing lookup requirement: ${lookupId}`)
      }
    }
    for (const equationId of PIPE_WALL_EQUATION_IDS) {
      if (!(equationId in requirements)) {
        errors.push(`Pipe wall plan missing equation requirement: ${equationId}`)
      }
    }

    const gatesOpen = FRESH_PIPE_WALL_HARD_BLOCKED.some((reqId) => {
      const req = requirements[reqId] as { status?: string } | undefined
      return req?.status === 'missing' || req?.status === 'ready'
    })
    if (gatesOpen) {
      const hardBlocked = [...(rootGoal?.blocked_by ?? [])].sort()
      const expected = [...FRESH_PIPE_WALL_HARD_BLOCKED].sort()
      if (hardBlocked.join('|') !== expected.join('|')) {
        errors.push(
          'Fresh pipe wall plan must hard-block only REQ-straight_pipe_section and REQ-pressure_design_case.',
        )
      }
      if (strategy?.next_fields?.join('|') !== 'straight_pipe_section') {
        errors.push('Fresh pipe wall plan next field must be straight_pipe_section.')
      }
      if (strategy?.current_phase !== 'expansion_assumptions') {
        errors.push('Fresh pipe wall plan current_phase must be expansion_assumptions.')
      }
      const internalPressure = requirements['REQ-internal_design_gage_pressure'] as
        | { activation_status?: string }
        | undefined
      if (internalPressure?.activation_status !== 'conditional') {
        errors.push(
          'REQ-internal_design_gage_pressure must be conditional before pressure_design_case is resolved.',
        )
      }
    }
  }

  const traversal = engineeringPlan.traversal
  if (traversal) {
    if (!traversal.current_active_node_id) {
      errors.push('traversal.current_active_node_id is required.')
    }
    if (!traversal.current_active_node) {
      errors.push('traversal.current_active_node is required.')
    }
    if (!traversal.pending_expansion_nodes?.length) {
      warnings.push('traversal.pending_expansion_nodes is empty.')
    }
    if (!traversal.expanded_nodes?.length) {
      warnings.push('traversal.expanded_nodes is empty.')
    }
    if (!traversal.branch_decisions?.length) {
      warnings.push('traversal.branch_decisions is empty.')
    }

    const pendingIds = new Set((traversal.pending_expansion_nodes ?? []).map((item) => item.node_id))
    const expandedIds = new Set((traversal.expanded_nodes ?? []).map((item) => item.node_id))
    const overlap = [...pendingIds].filter((id) => expandedIds.has(id))
    if (overlap.length > 0) {
      errors.push(
        `traversal expanded_nodes and pending_expansion_nodes overlap: ${overlap.join(', ')}`,
      )
    }
  }

  return { valid: errors.length === 0, errors, warnings }
}
