import { useState } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import { MaterialSearchInput } from '@/components/workflow/MaterialSearchInput'

function MaterialSearchHarness({ onSubmit = vi.fn() }: { onSubmit?: (value?: string) => void }) {
  const [value, setValue] = useState('')
  return <MaterialSearchInput value={value} onChange={setValue} onSubmit={onSubmit} placeholder="Search materials" />
}

describe('MaterialSearchInput', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_MOCK_DATA', 'true')
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows ASTM suggestions after three characters', async () => {
    const user = userEvent.setup()
    render(<MaterialSearchHarness />)

    await user.type(screen.getByPlaceholderText('Search materials'), '106')
    await vi.advanceTimersByTimeAsync(200)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'astm_a106_gr_b' })).toBeInTheDocument()
    })
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
      expect(screen.getByRole('option', { name: 'astm_a106_gr_b' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('option', { name: 'astm_a106_gr_b' }))

    expect(onSubmit).toHaveBeenCalledWith('astm_a106_gr_b')
  })
})
