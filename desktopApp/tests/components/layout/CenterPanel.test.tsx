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
