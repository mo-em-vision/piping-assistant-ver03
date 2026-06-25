import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { RightPanel } from '@/components/layout/RightPanel'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { mockTaskState } from '@/mock/taskState.mock'

describe('RightPanel tabs', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset()
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: mockTaskState,
    })
  })

  it('shows Task and Chat tabs without embedding chat in Task tab', () => {
    render(<RightPanel />)

    expect(screen.getByRole('tab', { name: 'Task' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Chat' })).toBeInTheDocument()
    expect(screen.getByText('Task state')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Engineering report' })).not.toBeInTheDocument()
    expect(
      screen.queryByPlaceholderText(/Ask about this task, its inputs, or calculation outputs/i),
    ).not.toBeInTheDocument()
  })

  it('places reference tab close button inside the tab container', () => {
    useRightPanelStore.getState().openReferenceTab('B313-304.1.1', '§304.1.1')

    const { container } = render(<RightPanel />)

    const tabItem = container.querySelector('.side-panel__tab-item--closable')
    expect(tabItem).toBeTruthy()
    expect(tabItem?.querySelector('.side-panel__tab-label')).toHaveTextContent('§304.1.1')
    expect(tabItem?.querySelector('.side-panel__tab-close')).toBeTruthy()
  })

  it('shows Engineering report when the report step is active', () => {
    useTaskStore.setState({
      activeTaskState: {
        ...mockTaskState,
        progress: {
          ...mockTaskState.progress,
          timeline: mockTaskState.progress.timeline.map((step) =>
            step.id === 'report'
              ? { ...step, status: 'active', hint: 'Generate the engineering report' }
              : step.id === 'thickness'
                ? { ...step, status: 'done', display_value: '12.5 mm', value: 12.5, unit: 'mm' }
                : step,
          ),
        },
      },
    })

    render(<RightPanel />)

    expect(screen.getByRole('heading', { name: 'Engineering report' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()
  })

  it('shows Calculations section when node summaries are present', () => {
    useTaskStore.setState({
      activeTaskState: {
        ...mockTaskState,
        node_calculations: [
          {
            node_id: 'B313-304.1.2',
            paragraph: '304.1.2',
            title: 'Straight Pipe Under Internal Pressure',
            primary_result: {
              symbol: 't',
              label: 'Required wall thickness',
              value: '0.084',
              unit: 'mm',
            },
            inputs: [{ symbol: 'P', name: 'Design pressure', value: '8.0', unit: 'bar' }],
          },
        ],
      },
    })

    render(<RightPanel />)

    expect(screen.getByText('Calculations')).toBeInTheDocument()
    expect(screen.getByText(/t = 0\.084 mm/)).toBeInTheDocument()
  })
})
