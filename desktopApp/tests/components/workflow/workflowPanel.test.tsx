import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { WorkflowComposer } from '@/components/workflow/WorkflowComposer'
import { WorkflowHeader } from '@/components/workflow/WorkflowHeader'
import { WorkflowHistory } from '@/components/workflow/WorkflowHistory'
import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { mockTaskState } from '@/mock/taskState.mock'

describe('WorkflowHeader', () => {
  it('renders task name only', () => {
    render(<WorkflowHeader taskName="Pipe Wall Thickness Design" />)

    expect(screen.getByRole('heading', { name: 'Pipe Wall Thickness Design' })).toBeInTheDocument()
    expect(
      screen.queryByText(/Calculation of Minimum Required Thickness of a straight section pipe/i),
    ).not.toBeInTheDocument()
  })
})

describe('StandardReferenceLink', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset()
  })

  it('opens a reference tab when clicked', () => {
    render(<StandardReferenceLink nodeId="B313-304.1.1" label="§304.1.1" />)

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
  it('does not auto-scroll when items are appended or updated', () => {
    const scrollIntoView = vi.fn()
    vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(scrollIntoView)

    const equationItem: WorkflowHistoryItem = {
      id: 'output-preview-equation',
      kind: 'output',
      block: {
        id: 'preview-equation',
        type: 'equation',
        title: 'Governing equation',
        content: 't = PD / 2(SEW + PY)',
        display: 't = PD / 2(SEW + PY)',
      },
    }

    const { rerender } = render(<WorkflowHistory items={[equationItem]} />)
    scrollIntoView.mockClear()

    rerender(
      <WorkflowHistory
        items={[
          equationItem,
          {
            id: 'output-planning-status',
            kind: 'output',
            block: {
              id: 'planning-status',
              type: 'text',
              title: 'Task status:',
              content: 'Complete the fields below to continue.',
            },
          },
        ]}
      />,
    )

    expect(scrollIntoView).not.toHaveBeenCalled()
  })

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

  it('retains equation after new block appended', () => {
    const equationItem: WorkflowHistoryItem = {
      id: 'output-preview-equation',
      kind: 'output',
      block: {
        id: 'preview-equation',
        type: 'equation',
        title: 'Governing equation',
        content: 't = PD / 2(SEW + PY)',
        display: 't = PD / 2(SEW + PY)',
      },
    }

    const { rerender } = render(<WorkflowHistory items={[equationItem]} />)
    expect(screen.getByText('Governing equation')).toBeInTheDocument()

    rerender(
      <WorkflowHistory
        items={[
          equationItem,
          {
            id: 'output-planning-status',
            kind: 'output',
            block: {
              id: 'planning-status',
              type: 'text',
              title: 'Task status:',
              content: 'Complete the fields below to continue.',
            },
          },
        ]}
      />,
    )

    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(screen.getByText(/Complete the fields below to continue/)).toBeInTheDocument()
  })

  it('updates equation input table values in place', () => {
    const equationItem: WorkflowHistoryItem = {
      id: 'output-preview-equation',
      kind: 'output',
      block: {
        id: 'preview-equation',
        type: 'equation',
        content: 't = PD / 2(SEW + PY)',
        display: 't = PD / 2(SEW + PY)',
        input_table: {
          columns: [
            { key: 'symbol', label: 'Symbol', sortable: false },
            { key: 'definition', label: 'Definition', sortable: false },
            { key: 'value', label: 'Value', sortable: false },
          ],
          rows: [{ symbol: 'D', definition: 'Outside diameter', value: 'Awaiting user input' }],
        },
      },
    }

    const { rerender } = render(<WorkflowHistory items={[equationItem]} />)
    expect(screen.getByText('Awaiting user input')).toBeInTheDocument()

    rerender(
      <WorkflowHistory
        items={[
          {
            ...equationItem,
            block: {
              ...equationItem.block,
              input_table: {
                columns: equationItem.block.input_table!.columns,
                rows: [{ symbol: 'D', definition: 'Outside diameter', value: '114.3 mm' }],
              },
            },
          },
        ]}
      />,
    )

    expect(screen.getByText('114.3 mm')).toBeInTheDocument()
    expect(screen.queryByText('Awaiting user input')).not.toBeInTheDocument()
  })
})

describe('WorkflowComposer', () => {
  beforeEach(() => {
    useTaskStore.setState({ submittingParameter: null })
  })

  it('greys out inputs while the backend is processing a submitted value', () => {
    useTaskStore.setState({ submittingParameter: 'internal_design_gage_pressure' })

    const { container } = render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Enter the design pressure for the pipe.',
          parameter: {
            name: 'internal_design_gage_pressure',
            label: 'Design Pressure',
            type: 'number',
            required: true,
            units: ['bar', 'psi', 'kPa'],
            default_unit: 'bar',
            default_value: null,
            value: null,
            options: [],
            status: 'pending',
            requires_confirmation: false,
          },
        }}
      />,
    )

    expect(container.querySelector('.workflow-panel__composer--processing')).toBeTruthy()
    expect(container.querySelector('.workflow-panel__next-step-inline--locked')).toBeTruthy()
    expect(screen.getByPlaceholderText('Value…')).toBeDisabled()
  })

  it('renders NPS picker to the right of the prompt', () => {
    const parameter = mockTaskState.parameters.find((item) => item.name === 'nominal_pipe_size')
    expect(parameter).toBeTruthy()

    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Select the nominal pipe size.',
          parameter: parameter!,
        }}
      />,
    )

    expect(screen.getByText('Next Step:')).toBeInTheDocument()
    const row = screen
      .getByText('Select the nominal pipe size.')
      .closest('.workflow-panel__next-step-inline')
    expect(row).toBeTruthy()
    expect(row).toContainElement(screen.getByRole('tab', { name: 'NPS' }))
    expect(screen.getByRole('tab', { name: 'NPS' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Submit selection' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Select pipe size' }))

    expect(screen.getByRole('listbox', { name: /Nominal pipe size options/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'NPS 4' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /OD /i })).not.toBeInTheDocument()
  })

  it('shows outside diameter options in combobox when OD mode is selected', () => {
    const parameter = mockTaskState.parameters.find((item) => item.name === 'nominal_pipe_size')
    expect(parameter).toBeTruthy()

    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Select the nominal pipe size.',
          parameter: parameter!,
        }}
      />,
    )

    fireEvent.click(screen.getByRole('tab', { name: 'Outside diameter' }))
    fireEvent.click(screen.getByRole('button', { name: 'Select outside diameter' }))

    expect(screen.getByRole('listbox', { name: /Outside diameter options/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '4.5 in (114.3 mm)' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'NPS 4' })).not.toBeInTheDocument()
  })

  it('shows inside diameter input when inside diameter mode is selected', () => {
    const parameter = mockTaskState.parameters.find((item) => item.name === 'nominal_pipe_size')
    expect(parameter).toBeTruthy()

    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Select the nominal pipe size.',
          parameter: parameter!,
        }}
      />,
    )

    fireEvent.click(screen.getByRole('tab', { name: 'Inside diameter' }))

    expect(screen.getByPlaceholderText('Enter inside diameter')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'mm' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Select pipe size' })).not.toBeInTheDocument()
  })

  it('shows pipe construction type options in a dropup picker', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Provide pipe construction type',
          parameter: {
            name: 'pipe_construction_type',
            label: 'Pipe Construction Type',
            type: 'dropdown',
            required: true,
            units: [],
            default_unit: 'dimensionless',
            default_value: null,
            value: null,
            options: [
              { value: 'Seamless pipe', label: 'Seamless pipe' },
              {
                value: 'Electric resistance welded pipe',
                label: 'Electric resistance welded pipe',
              },
            ],
            status: 'pending',
            requires_confirmation: false,
          },
        }}
      />,
    )

    expect(screen.getByRole('button', { name: 'Select pipe construction type' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Seamless pipe' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Select pipe construction type' }))

    expect(screen.getByRole('listbox', { name: /Pipe Construction Type options/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Seamless pipe' })).toBeInTheDocument()
    expect(
      screen.getByRole('option', { name: 'Electric resistance welded pipe' }),
    ).toBeInTheDocument()
  })

  it('does not show the confirmation hint when no default value is available', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: null,
          parameter: {
            name: 'joint_category',
            label: 'Joint Category',
            type: 'dropdown',
            required: true,
            units: [],
            default_unit: 'dimensionless',
            default_value: null,
            value: null,
            options: [
              { value: 'Seamless pipe', label: 'Seamless pipe' },
              { value: 'Electric resistance welded pipe', label: 'Electric resistance welded pipe' },
            ],
            status: 'pending',
            requires_confirmation: true,
          },
        }}
      />,
    )

    expect(screen.queryByText(/Confirm or change the proposed default value/i)).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/Choose an option above/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Select pipe construction type' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Select pipe construction type' }))

    expect(screen.getByRole('option', { name: 'Seamless pipe' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Electric resistance welded pipe' })).toBeInTheDocument()
  })

  it('renders inline unit pills beside the next step prompt for numeric inputs', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Enter the design pressure for the pipe.',
          parameter: {
            name: 'internal_design_gage_pressure',
            label: 'Design Pressure',
            type: 'number',
            required: true,
            units: ['bar', 'psi', 'kPa'],
            default_unit: 'bar',
            default_value: null,
            value: null,
            options: [],
            status: 'pending',
            requires_confirmation: false,
          },
        }}
      />,
    )

    expect(screen.getByText(/Enter the design pressure for the pipe\./)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Value…')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Design Pressure unit' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'bar' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'psi' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('prefills the input when a proposed default value is available', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: null,
          parameter: {
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
          },
        }}
      />,
    )

    expect(screen.queryByText(/Confirm or change the proposed default value/i)).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Value…' })).toHaveValue('1')
  })

  it('renders yes/no choices to the right of the straight pipe prompt', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt:
            'Is the pipe wall thickness you would like to calculate for a straight section of pipe? Non-straight sections (fittings, bends) are not yet supported.',
          parameter: {
            name: 'straight_pipe_section',
            label: 'Straight Pipe Section',
            type: 'checkbox',
            required: true,
            units: [],
            default_unit: 'dimensionless',
            default_value: true,
            value: true,
            options: [],
            status: 'confirmation_required',
            requires_confirmation: true,
          },
        }}
      />,
    )

    const row = screen.getByText(/straight section of pipe/i).closest('.workflow-panel__next-step-inline')
    expect(row).toBeTruthy()
    expect(row).toContainElement(screen.getByRole('button', { name: 'Yes' }))
    expect(row).toContainElement(screen.getByRole('button', { name: 'No' }))
    expect(screen.queryByText(/Applied to a straight section of a pipe\./)).not.toBeInTheDocument()
  })

  it('renders dropdown options to the right of the prompt', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt: 'Is the pipe subjected to internal or external pressure?',
          parameter: {
            name: 'pressure_loading',
            label: 'Pressure Loading',
            type: 'dropdown',
            required: true,
            units: [],
            default_unit: 'dimensionless',
            default_value: null,
            value: null,
            options: [
              { value: 'internal_pressure', label: 'Internal pressure' },
              { value: 'external_pressure', label: 'External pressure' },
            ],
            status: 'pending',
            requires_confirmation: false,
          },
        }}
      />,
    )

    const row = screen
      .getByText(/internal or external pressure/i)
      .closest('.workflow-panel__next-step-inline')
    expect(row).toBeTruthy()
    expect(row).toContainElement(screen.getByRole('option', { name: 'Internal pressure' }))
    expect(row).toContainElement(screen.getByRole('option', { name: 'External pressure' }))
  })

  it('renders an enabled material search input for the material step', () => {
    render(
      <WorkflowComposer
        ask={{
          kind: 'input',
          prompt:
            'Select the pipe material. (start typing to see the available options)',
          parameter: {
            name: 'material',
            label: 'Material',
            type: 'material',
            required: true,
            units: [],
            default_unit: 'dimensionless',
            default_value: null,
            value: null,
            options: null,
            validation: null,
            status: 'pending',
            requires_confirmation: false,
            submittable: true,
          },
        }}
        disabled={false}
      />,
    )

    expect(
      screen.getByText(/Select the pipe material\. \(start typing to see the available options\)/),
    ).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Search…')).toBeEnabled()
    expect(screen.queryByPlaceholderText('Waiting for the next workflow step…')).not.toBeInTheDocument()
  })
})
