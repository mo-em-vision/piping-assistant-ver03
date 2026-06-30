import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { ExecutionTracePanel } from '@/components/dev/inspector/ExecutionTracePanel'
import { useInspectorStore } from '@/components/dev/inspector/inspectorStore'

import type { ExecutionTraceStepDto } from '@/types/backend/inspection'

const sampleSteps: ExecutionTraceStepDto[] = [
  {
    step_index: 0,
    workflow_id: 'wf-1',
    node_id: 'shell_formula',
    node_type: 'equation',
    incoming_edge: null,
    outgoing_edge: null,
    selection_reason: 'dependency_satisfied',
    inputs: { pressure: 1.0 },
    outputs: { thickness: 18.2 },
    duration_ms: 3.1,
    status: 'success',
  },
]

describe('ExecutionTracePanel', () => {
  it('renders execution steps and selects on click', async () => {
    useInspectorStore.setState({ selectedStepIndex: null, selectedNodeId: null })
    render(<ExecutionTracePanel steps={sampleSteps} />)
    expect(screen.getByText('shell_formula')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Step 1/i }))
    expect(useInspectorStore.getState().selectedStepIndex).toBe(0)
    expect(useInspectorStore.getState().selectedNodeId).toBe('shell_formula')
  })
})
