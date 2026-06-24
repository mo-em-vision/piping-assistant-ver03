import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { WorkflowComposer } from '@/components/workflow/WorkflowComposer'
import { WorkflowHeader } from '@/components/workflow/WorkflowHeader'
import { WorkflowHistory } from '@/components/workflow/WorkflowHistory'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { mockTaskState } from '@/mock/taskState.mock'

describe('WorkflowHeader', () => {
  it('renders task name and display heading', () => {
    render(
      <WorkflowHeader
        taskName="Pipe Thickness Calculation"
        context={{
          node_id: 'B313-304.1.1',
          standard: 'ASME B31.3',
          paragraph: '304.1.1',
          display_heading:
            'Calculation of Minimum Required Thickness of a straight section pipe (according to ASME B 31.3 paragraph 304.1.1)',
          hover_excerpt: 'The required thickness of straight sections of pipe shall be determined...',
        }}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Pipe Thickness Calculation' })).toBeInTheDocument()
    expect(
      screen.getByText(/Calculation of Minimum Required Thickness of a straight section pipe/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /ASME B 31.3 paragraph 304.1.1/i }),
    ).toBeInTheDocument()
  })
})

describe('StandardReferenceLink', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset()
  })

  it('shows hover excerpt on enter and hides it on leave', () => {
    render(<StandardReferenceLink nodeId="B313-304.1.1" label="§304.1.1" hoverExcerpt="Preview text" />)

    const link = screen.getByRole('button', { name: '§304.1.1' }).parentElement
    expect(link).toBeTruthy()

    fireEvent.mouseEnter(link!)
    expect(screen.getByText('Preview text')).toBeInTheDocument()

    fireEvent.mouseLeave(link!)
    expect(screen.queryByText('Preview text')).not.toBeInTheDocument()
  })

  it('opens a reference tab when clicked', () => {
    render(<StandardReferenceLink nodeId="B313-304.1.1" label="§304.1.1" hoverExcerpt="Preview text" />)

    fireEvent.click(screen.getByRole('button', { name: '§304.1.1' }))

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('ref-B313-304.1.1')
    expect(state.tabs.some(
      (tab) =>
        tab.kind === 'reference' &&
        tab.referenceKind === 'node' &&
        tab.referenceId === 'B313-304.1.1',
    )).toBe(
      true,
    )
  })
})

describe('WorkflowHistory', () => {
  it('renders assumptions and equation content without chat labels', () => {
    render(
      <WorkflowHistory
        items={[
          {
            id: 'node-content-1',
            kind: 'node-content',
            block: {
              id: 'node-activation-assumptions-B313-304.1.1',
              type: 'text',
              title: null,
              content: 'Applied to a straight section of a pipe.',
              variant: 'assumption',
            },
          },
        ]}
      />,
    )

    expect(screen.queryByText('Output')).not.toBeInTheDocument()
    expect(screen.queryByText('Workflow')).not.toBeInTheDocument()
    expect(screen.getByText('Assumptions:')).toBeInTheDocument()
    expect(screen.getByText(/Applied to a straight section of a pipe\./)).toBeInTheDocument()
    expect(screen.getByText('Assumptions:').tagName).toBe('STRONG')
  })
})

describe('WorkflowComposer', () => {
  it('renders the next step prompt in bold above the input field', () => {
    const parameter = mockTaskState.parameters.find((item) => item.name === 'nominal_pipe_size')
    expect(parameter).toBeTruthy()

    render(
      <WorkflowComposer
        parameter={parameter!}
        nextStepPrompt="Enter the nominal pipe size."
      />,
    )

    const label = screen.getByText('Next Step:')
    expect(label.tagName).toBe('STRONG')
    expect(screen.getByText(/Enter the nominal pipe size\./)).toBeInTheDocument()
  })

  it('does not show the confirmation hint when no default value is available', () => {
    render(
      <WorkflowComposer
        parameter={{
          name: 'joint_category',
          label: 'Joint Category',
          type: 'dropdown',
          required: true,
          units: [],
          default_unit: 'dimensionless',
          default_value: null,
          value: null,
          options: [
            { value: 'seamless', label: 'Seamless' },
            { value: 'welded', label: 'Welded' },
          ],
          status: 'pending',
          requires_confirmation: true,
        }}
      />,
    )

    expect(screen.queryByText(/Confirm or change the proposed default value/i)).not.toBeInTheDocument()
  })

  it('prefills the input when a proposed default value is available', () => {
    render(
      <WorkflowComposer
        parameter={{
          name: 'weld_joint_efficiency',
          label: 'Weld Joint Efficiency',
          type: 'number',
          required: true,
          units: [],
          default_unit: 'dimensionless',
          default_value: 1,
          value: 1,
          options: [],
          status: 'confirmation_required',
          requires_confirmation: true,
        }}
      />,
    )

    expect(screen.queryByText(/Confirm or change the proposed default value/i)).not.toBeInTheDocument()
    expect(screen.getByRole('spinbutton')).toHaveValue(1)
  })
})
