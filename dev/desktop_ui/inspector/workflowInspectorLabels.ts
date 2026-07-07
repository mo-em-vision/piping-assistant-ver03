const PHASE_LABELS: Record<string, string> = {
  expansion_assumptions: 'Expansion assumptions',
  path_decisions: 'Path decisions',
  parameter_gathering: 'Parameter gathering',
  coefficient_resolution: 'Coefficient resolution',
  execution_assumptions: 'Execution assumptions',
  definition_equation_completion: 'Definition / equation',
  ready: 'Ready to execute',
}

const ACTION_LABELS: Record<string, string> = {
  request_input: 'Waiting for user input',
  clarify: 'Needs clarification',
  propose_path: 'Ready to continue',
  route_standard: 'Routing standard',
  context_switch: 'Context switch',
  synthesize_report: 'Synthesizing report',
  general_response: 'General response',
  confirm_override: 'Confirm override',
}

export function formatNavigationPhase(phase: string | null | undefined): string {
  if (!phase) {
    return '—'
  }
  return PHASE_LABELS[phase] ?? phase.replaceAll('_', ' ')
}

export function formatPlannerAction(action: string | null | undefined): string {
  if (!action) {
    return '—'
  }
  return ACTION_LABELS[action] ?? action.replaceAll('_', ' ')
}
