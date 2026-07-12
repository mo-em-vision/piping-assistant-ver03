import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CenterPanel } from '@/components/layout/CenterPanel'
import { mockCompletedTaskState, mockTaskState } from '@/mock/taskState.mock'
import { useChatStore } from '@/store/chatStore'
import { useTaskStore } from '@/store/taskStore'

function mockWindowSelection(text: string, target: Node): void {
  const range = document.createRange()
  range.selectNodeContents(target)

  vi.spyOn(window, 'getSelection').mockReturnValue({
    isCollapsed: false,
    rangeCount: 1,
    toString: () => text,
    getRangeAt: () => range,
    anchorNode: target,
    focusNode: target,
  } as unknown as Selection)
}

describe('CenterPanel Ask AI selection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: mockTaskState,
      loading: false,
      userError: null,
    })
    useChatStore.setState({
      askAboutSelection: vi.fn().mockResolvedValue(undefined),
    } as Partial<ReturnType<typeof useChatStore.getState>>)
  })

  it('shows Ask AI menu when right-clicking selected workflow text', () => {
    render(<CenterPanel />)

    const outputText = screen.getByText('Governing equation')
    mockWindowSelection('Governing equation', outputText)

    fireEvent.contextMenu(outputText, { clientX: 120, clientY: 80 })

    expect(screen.getByRole('menuitem', { name: 'Ask AI' })).toBeInTheDocument()
  })

  it('calls askAboutSelection when Ask AI is chosen', () => {
    const askAboutSelection = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ askAboutSelection })

    render(<CenterPanel />)

    const outputText = screen.getByText('Governing equation')
    mockWindowSelection('Governing equation', outputText)

    fireEvent.contextMenu(outputText, { clientX: 120, clientY: 80 })
    fireEvent.click(screen.getByRole('menuitem', { name: 'Ask AI' }))

    expect(askAboutSelection).toHaveBeenCalledWith('Governing equation')
  })
})

describe('CenterPanel completion next steps', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useChatStore.setState({
      askAboutSelection: vi.fn().mockResolvedValue(undefined),
    } as Partial<ReturnType<typeof useChatStore.getState>>)
  })

  it('shows completion next steps instead of idle composer when task is completed', () => {
    useTaskStore.setState({
      activeTask: {
        id: mockCompletedTaskState.task_id,
        name: mockCompletedTaskState.name,
        description: mockCompletedTaskState.description,
        discipline: mockCompletedTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: mockCompletedTaskState,
      loading: false,
      userError: null,
    })

    render(<CenterPanel />)

    expect(screen.getByText('Next Steps:')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Waiting for the next workflow step…')).not.toBeInTheDocument()
  })
})

describe('CenterPanel workflow transcript', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useChatStore.setState({
      askAboutSelection: vi.fn().mockResolvedValue(undefined),
    } as Partial<ReturnType<typeof useChatStore.getState>>)
  })

  it('shows accumulated history and current prompt below', () => {
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: {
        ...mockTaskState,
        current_ask: {
          kind: 'input',
          parameter_id: 'nominal_pipe_size',
          prompt: 'Select the nominal pipe size for the straight section.',
        },
      },
      loading: false,
      userError: null,
    })

    const { container } = render(<CenterPanel />)

    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(
      screen.getByText(/Select the nominal pipe size for the straight section/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Complete the fields below to continue/)).not.toBeInTheDocument()

    const history = container.querySelector('.workflow-panel__history')
    const composer = container.querySelector('.workflow-panel__composer')
    expect(history).toBeTruthy()
    expect(composer).toBeTruthy()
    expect(
      history!.compareDocumentPosition(composer!) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('keeps prior explanation blocks when ask advances', () => {
    const explanation = 'The minimum required wall thickness shall be computed.'

    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: {
        ...mockTaskState,
        display_outputs: [
          {
            id: 'preview-intro',
            type: 'text',
            content: explanation,
          },
        ],
        current_ask: {
          kind: 'input',
          parameter_id: 'nominal_pipe_size',
          prompt: 'First prompt',
        },
      },
      loading: false,
      userError: null,
    })

    const { rerender } = render(<CenterPanel />)
    expect(screen.getByText(explanation)).toBeInTheDocument()

    useTaskStore.setState({
      activeTaskState: {
        ...useTaskStore.getState().activeTaskState!,
        parameters: [
          {
            ...useTaskStore.getState().activeTaskState!.parameters[0],
            status: 'confirmed' as const,
          },
          {
            name: 'design_temperature',
            label: 'Design Temperature',
            type: 'number',
            required: true,
            units: ['degF'],
            default_unit: 'degF',
            default_value: null,
            value: null,
            options: null,
            validation: null,
            status: 'pending' as const,
            requires_confirmation: false,
            submittable: true,
            guidance: 'Enter the design temperature.',
          },
        ],
        progress: {
          ...useTaskStore.getState().activeTaskState!.progress,
          submittable_parameters: ['design_temperature'],
          current_step_id: 'design_temperature',
        },
        display_outputs: [
          {
            id: 'preview-intro',
            type: 'text',
            content: explanation,
          },
          {
            id: 'preview-equation',
            type: 'equation',
            title: 'Governing equation',
            content: 't = PD / 2(SEW + PY)',
            display: 't = PD / 2(SEW + PY)',
          },
        ],
        current_ask: {
          kind: 'input',
          parameter_id: 'design_temperature',
          prompt: 'Enter the design temperature.',
        },
      },
    })

    rerender(<CenterPanel />)

    expect(screen.getByText(explanation)).toBeInTheDocument()
    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(screen.getByText(/Enter the design temperature/i)).toBeInTheDocument()
  })

  it('does not show superseded prompts in workflow history after step advance', () => {
    const priorPrompt = 'Select the nominal pipe size for the straight section.'

    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: {
        ...mockTaskState,
        display_outputs: [],
        current_ask: {
          kind: 'input',
          parameter_id: 'nominal_pipe_size',
          prompt: priorPrompt,
        },
      },
      loading: false,
      userError: null,
    })

    const { container, rerender } = render(<CenterPanel />)
    const history = () => container.querySelector('.workflow-panel__history')
    expect(history()).not.toHaveTextContent(priorPrompt)

    useTaskStore.setState({
      activeTaskState: {
        ...useTaskStore.getState().activeTaskState!,
        parameters: [
          {
            ...useTaskStore.getState().activeTaskState!.parameters[0],
            status: 'confirmed' as const,
          },
          {
            name: 'design_temperature',
            label: 'Design Temperature',
            type: 'number',
            required: true,
            units: ['degF'],
            default_unit: 'degF',
            default_value: null,
            value: null,
            options: null,
            validation: null,
            status: 'pending' as const,
            requires_confirmation: false,
            submittable: true,
            guidance: 'Enter the design temperature.',
          },
        ],
        progress: {
          ...useTaskStore.getState().activeTaskState!.progress,
          submittable_parameters: ['design_temperature'],
          current_step_id: 'design_temperature',
        },
        display_outputs: [
          {
            id: 'archived-prompt-nominal_pipe_size',
            type: 'text',
            content: priorPrompt,
            variant: 'body',
          },
        ],
        current_ask: {
          kind: 'input',
          parameter_id: 'design_temperature',
          prompt: 'Enter the design temperature.',
        },
      },
    })

    rerender(<CenterPanel />)

    expect(history()).not.toHaveTextContent(priorPrompt)
    expect(screen.getByText(/Enter the design temperature/i)).toBeInTheDocument()
  })

  it('does not build workflow history from timeline alone', () => {
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: {
        ...mockTaskState,
        display_outputs: [],
        progress: {
          ...mockTaskState.progress,
          timeline: mockTaskState.progress.timeline,
        },
      },
      loading: false,
      userError: null,
    })

    render(<CenterPanel />)

    expect(
      screen.getByText('Workflow history will appear here as you progress.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Thickness')).not.toBeInTheDocument()
  })
})

describe('CenterPanel header title', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useChatStore.setState({
      askAboutSelection: vi.fn().mockResolvedValue(undefined),
    } as Partial<ReturnType<typeof useChatStore.getState>>)
  })

  it('does not render raw workflow_id when display metadata and task name are absent', () => {
    useTaskStore.setState({
      activeTask: {
        id: 'task-minimal',
        name: '',
        description: '',
        discipline: 'piping',
        status: 'in_progress',
      },
      activeTaskState: {
        task_id: 'task-minimal',
        name: '',
        workflow_id: 'pipe_wall_thickness_design',
        discipline: 'piping',
        description: '',
        status: 'awaiting_input',
        active_nodes: [],
        progress: { timeline: [] },
        display_outputs: [],
        flow_guidance: { transcript_blocks: [] },
      },
      loading: false,
      userError: null,
    })

    render(<CenterPanel />)

    expect(
      screen.queryByRole('heading', { name: 'pipe wall thickness design' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Workflow' })).toBeInTheDocument()
  })
})

describe('CenterPanel equation scroll ordering', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useChatStore.setState({
      askAboutSelection: vi.fn().mockResolvedValue(undefined),
    } as Partial<ReturnType<typeof useChatStore.getState>>)
  })

  it('renders input_waiting after equation blocks and keeps equation layout in one article', () => {
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: {
        ...mockTaskState,
        display_outputs: [
          {
            id: 'equation-asme-b313-304-1-2-eq-3a',
            type: 'equation',
            title: 'Governing equation',
            content: 't = PD / 2(SEW + PY)',
            display_role: 'equation',
            display_state: 'preview',
            lifecycle: 'preview',
            input_table: {
              columns: [
                { key: 'symbol', label: 'Symbol', sortable: false },
                { key: 'definition', label: 'Definition', sortable: false },
                { key: 'value', label: 'Value', sortable: false },
              ],
              rows: [
                {
                  symbol: 'P',
                  definition: 'Design pressure',
                  value: 'Awaiting user input',
                },
              ],
            },
          },
          {
            id: 'input-waiting',
            type: 'text',
            content: 'Waiting for your input to continue the workflow.',
            display_role: 'input_waiting',
            lifecycle: 'volatile',
            volatile: true,
            history_eligible: false,
          },
        ],
        current_ask: {
          kind: 'input',
          parameter_id: 'design_pressure',
          short_prompt: 'Enter design pressure.',
          prompt: 'Enter design pressure.',
        },
      },
      loading: false,
      userError: null,
    })

    const { container } = render(<CenterPanel />)

    const equationArticle = container.querySelector('.output-equation')
    const waitingText = screen.getByText('Waiting for your input to continue the workflow.')
    expect(equationArticle).toBeTruthy()
    expect(equationArticle?.querySelector('.output-equation__input-table')).toBeTruthy()
    expect(
      equationArticle!.compareDocumentPosition(waitingText) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })
})
