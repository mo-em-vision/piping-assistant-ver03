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

    const outputText = screen.getByText(/Task status/i)
    mockWindowSelection('Task status', outputText)

    fireEvent.contextMenu(outputText, { clientX: 120, clientY: 80 })

    expect(screen.getByRole('menuitem', { name: 'Ask AI' })).toBeInTheDocument()
  })

  it('calls askAboutSelection when Ask AI is chosen', () => {
    const askAboutSelection = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ askAboutSelection })

    render(<CenterPanel />)

    const outputText = screen.getByText(/Task status/i)
    mockWindowSelection('Task status', outputText)

    fireEvent.contextMenu(outputText, { clientX: 120, clientY: 80 })
    fireEvent.click(screen.getByRole('menuitem', { name: 'Ask AI' }))

    expect(askAboutSelection).toHaveBeenCalledWith('Task status')
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

    expect(screen.getByText(/Complete the fields below to continue/)).toBeInTheDocument()
    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(
      screen.getByText(/Select the nominal pipe size for the straight section/i),
    ).toBeInTheDocument()

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

  it('archives superseded prompt text into workflow history after step advance', () => {
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

    const { rerender } = render(<CenterPanel />)
    expect(screen.queryByText(priorPrompt)).not.toBeInTheDocument()

    useTaskStore.setState({
      activeTaskState: {
        ...useTaskStore.getState().activeTaskState!,
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

    expect(screen.getByText(priorPrompt)).toBeInTheDocument()
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
