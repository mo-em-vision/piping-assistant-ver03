import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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

  it('renders close buttons for each closable reference tab', () => {
    const store = useRightPanelStore.getState()
    store.openReferenceTab('B313-304.1.1', '§304.1.1')
    store.openReferenceTab('asme_b31.3_A-1A', 'Table A-1A', 'table')

    const { container } = render(<RightPanel />)

    const closableTabs = container.querySelectorAll('.side-panel__tab-item--closable')
    const closeButtons = container.querySelectorAll('.side-panel__tab-item--closable .side-panel__tab-close')
    expect(closableTabs).toHaveLength(2)
    expect(closeButtons).toHaveLength(2)
  })

  it('scrolls the active reference tab into view when opened', () => {
    const scrollIntoView = vi.fn()
    vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(scrollIntoView)

    useRightPanelStore.getState().openReferenceTab('B313-304.1.1', '§304.1.1')
    render(<RightPanel />)

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', inline: 'nearest' })
  })

  it('scrolls a closable tab into view on hover', () => {
    const scrollIntoView = vi.fn()
    vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(scrollIntoView)

    useRightPanelStore.getState().openReferenceTab('B313-304.1.1', '§304.1.1')
    const { container } = render(<RightPanel />)
    scrollIntoView.mockClear()

    const tabItem = container.querySelector('.side-panel__tab-item--closable')
    expect(tabItem).toBeTruthy()
    fireEvent.mouseEnter(tabItem!)

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', inline: 'nearest' })
  })

  it('activates the previous tab when closing the active reference tab', () => {
    const store = useRightPanelStore.getState()
    store.openReferenceTab('B313-304.1.1', '§304.1.1')
    store.openReferenceTab('asme_b31.3_A-1A', 'Table A-1A', 'table')

    const tabs = useRightPanelStore.getState().tabs
    const firstReferenceTabId = tabs[2]?.id
    const secondReferenceTabId = tabs[3]?.id
    expect(firstReferenceTabId).toBeTruthy()
    expect(secondReferenceTabId).toBeTruthy()

    store.setActiveTab(secondReferenceTabId!)
    store.closeTab(secondReferenceTabId!)

    expect(useRightPanelStore.getState().activeTabId).toBe(firstReferenceTabId)
  })

  it('scrolls the newly active tab into view after closing the active reference tab', () => {
    const scrollIntoView = vi.fn()
    vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(scrollIntoView)

    const store = useRightPanelStore.getState()
    store.openReferenceTab('B313-304.1.1', '§304.1.1')
    store.openReferenceTab('asme_b31.3_A-1A', 'Table A-1A', 'table')

    const tabs = useRightPanelStore.getState().tabs
    const secondReferenceTabId = tabs[3]?.id
    store.setActiveTab(secondReferenceTabId!)

    const { container } = render(<RightPanel />)
    scrollIntoView.mockClear()

    fireEvent.click(
      screen.getByRole('button', { name: 'Close Table A-1A' }),
    )

    expect(useRightPanelStore.getState().activeTabId).toBe(tabs[2]?.id)
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', inline: 'nearest' })
    expect(container.querySelectorAll('.side-panel__tab-item--closable')).toHaveLength(1)
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

  it('does not show Calculations or Warnings sections in the task tab', () => {
    useTaskStore.setState({
      activeTaskState: {
        ...mockTaskState,
        warnings: ['Thin-wall equation applicable when t < D/6'],
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

    expect(screen.queryByText('Calculations')).not.toBeInTheDocument()
    expect(screen.queryByText('Warnings')).not.toBeInTheDocument()
    expect(screen.queryByText(/t = 0\.084 mm/)).not.toBeInTheDocument()
  })
})
