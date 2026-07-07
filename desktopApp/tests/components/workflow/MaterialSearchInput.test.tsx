import { useState } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import { MaterialSearchInput } from '@/components/workflow/MaterialSearchInput'
import { useRightPanelStore } from '@/store/rightPanelStore'

function MaterialSearchHarness({
  onSubmit = vi.fn(),
  inline = false,
}: {
  onSubmit?: (value?: string, displayValue?: string) => void
  inline?: boolean
}) {
  const [value, setValue] = useState('')
  return (
    <MaterialSearchInput
      inline={inline}
      value={value}
      onChange={setValue}
      onSubmit={onSubmit}
      placeholder="Search materials"
    />
  )
}

describe('MaterialSearchInput', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_MOCK_DATA', 'true')
    vi.useFakeTimers({ shouldAdvanceTime: true })
    useRightPanelStore.setState({
      tabs: [
        { id: 'task', kind: 'task', title: 'Task' },
        { id: 'chat', kind: 'chat', title: 'Chat' },
      ],
      activeTabId: 'task',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows ASTM suggestions after three characters', async () => {
    const user = userEvent.setup()
    const { container } = render(<MaterialSearchHarness />)

    await user.type(screen.getByPlaceholderText('Search materials'), '106')
    await vi.advanceTimersByTimeAsync(200)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'ASTM A106 Grade B' })).toBeInTheDocument()
    })

    expect(container.querySelector('.material-search-input__anchor')).toBeTruthy()
    expect(container.querySelector('.composer-suggestions')).toBeTruthy()
    expect(screen.getByText('Select a material from the list.')).toBeInTheDocument()
  })

  it('does not submit free text without choosing a suggestion', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<MaterialSearchHarness onSubmit={onSubmit} />)

    await user.type(screen.getByPlaceholderText('Search materials'), '106')
    await vi.advanceTimersByTimeAsync(200)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'ASTM A106 Grade B' })).toBeInTheDocument()
    })

    await user.keyboard('{Enter}')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits selected suggestion', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    function PrefilledHarness() {
      const [value, setValue] = useState('106')
      return <MaterialSearchInput value={value} onChange={setValue} onSubmit={onSubmit} />
    }

    render(<PrefilledHarness />)
    await vi.advanceTimersByTimeAsync(200)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'ASTM A106 Grade B' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('option', { name: 'ASTM A106 Grade B' }))

    expect(onSubmit).toHaveBeenCalledWith('astm_a106_gr_b', 'ASTM A106 Grade B')
  })

  it('opens material tab when info button is clicked without submitting', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    function PrefilledHarness() {
      const [value, setValue] = useState('106')
      return <MaterialSearchInput value={value} onChange={setValue} onSubmit={onSubmit} />
    }

    render(<PrefilledHarness />)
    await vi.advanceTimersByTimeAsync(200)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'View details for ASTM A106 Grade B' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'View details for ASTM A106 Grade B' }))

    const state = useRightPanelStore.getState()
    expect(onSubmit).not.toHaveBeenCalled()
    expect(state.activeTabId).toBe('material-astm_a106_gr_b')
    expect(state.tabs.some((tab) => tab.kind === 'material' && tab.materialId === 'astm_a106_gr_b')).toBe(
      true,
    )
  })
})
