import type { TaskStateDto } from '@/types/backend/api'

export function buildAskAiTaskStateBrief(
  state: TaskStateDto | null | undefined,
  projectName?: string,
): string {
  if (!state) {
    return 'No task state is available.'
  }

  const lines: string[] = []

  if (projectName) {
    lines.push(`Project: ${projectName}`)
  }

  lines.push(`Task: ${state.name} (${state.discipline})`)

  if (state.description?.trim()) {
    lines.push(`Description: ${state.description.trim()}`)
  }

  lines.push(`Workflow: ${state.workflow_id}`)
  lines.push(`Status: ${state.status.replace(/_/g, ' ')}`)

  const heading = state.active_node_context?.display_heading?.trim()
  if (heading) {
    lines.push(`Current topic: ${heading}`)
  }

  const timeline = state.progress.timeline ?? state.progress.steps ?? []
  const currentStepId = state.progress.current_step_id
  const currentStep =
    timeline.find((step) => step.id === currentStepId) ??
    timeline.find((step) => step.status === 'active')

  if (currentStep) {
    const hint = currentStep.hint?.trim()
    lines.push(
      hint
        ? `Current step: ${currentStep.title} — ${hint}`
        : `Current step: ${currentStep.title}`,
    )
  }

  const completedSteps = timeline.filter(
    (step) => step.status === 'done' && (step.display_value != null || step.value != null),
  )

  if (completedSteps.length > 0) {
    lines.push('Inputs already provided:')
    for (const step of completedSteps) {
      const value =
        step.display_value ??
        (step.unit && step.unit !== 'dimensionless'
          ? `${String(step.value)} ${step.unit}`
          : String(step.value))
      lines.push(`- ${step.title}: ${value}`)
    }
  }

  const missingInputs = state.progress.missing_inputs ?? []
  if (missingInputs.length > 0) {
    lines.push(`Still needed: ${missingInputs.join(', ')}`)
  }

  const outputLabels = (state.display_outputs ?? [])
    .map((block) => block.title?.trim())
    .filter((title): title is string => Boolean(title))

  if (outputLabels.length > 0) {
    lines.push(`Visible workspace content: ${outputLabels.join('; ')}`)
  }

  return lines.join('\n')
}
