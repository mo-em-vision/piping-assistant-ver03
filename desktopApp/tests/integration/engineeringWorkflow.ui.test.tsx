import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('engineering workflow UI (mock mode)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_MOCK_DATA', 'true')

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/health')) {
        return new Response('{"status":"ok"}', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('{}', { status: 404 })
    }))

    vi.stubGlobal('electronAPI', {
      getBackendStatus: async () => ({
        status: 'connected',
        url: 'http://127.0.0.1:8000',
      }),
      onBackendStatusChange: () => () => undefined,
      retryBackendConnection: async () => ({
        status: 'connected',
        url: 'http://127.0.0.1:8000',
      }),
    })
  })

  it('creates a task, submits input, and hides report until workflow completes', async () => {
    const { default: App } = await import('@/App')
    const user = userEvent.setup()

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Create new task' })).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: 'Create new task' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pipe thickness calculation/i })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /pipe thickness calculation/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Pipe Thickness Calculation' })).toBeInTheDocument()
    })

    const npsField = screen.getByPlaceholderText('Value…')
    await user.clear(npsField)
    await user.type(npsField, '6')
    await user.click(screen.getByRole('button', { name: 'Submit' }))

    const { useTaskStore } = await import('@/store/taskStore')
    await waitFor(() => {
      expect(useTaskStore.getState().activeTaskState?.inputs.nominal_pipe_size?.display_value).toBe(
        '6 NPS',
      )
    })

    expect(screen.queryByRole('heading', { name: 'Engineering report' })).not.toBeInTheDocument()
  })
})
