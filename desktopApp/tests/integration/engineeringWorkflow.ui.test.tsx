import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

async function selectNominalPipeSize(user: ReturnType<typeof userEvent.setup>, label = 'NPS 6') {
  await user.click(screen.getByRole('button', { name: 'Select pipe size' }))
  await user.click(screen.getByRole('option', { name: label }))
}

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
      expect(screen.getByRole('button', { name: /pipe wall thickness design/i })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /pipe wall thickness design/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Pipe Wall Thickness Design' })).toBeInTheDocument()
    })

    expect(screen.getByText('Governing equation')).toBeInTheDocument()

    await selectNominalPipeSize(user)

    const { useTaskStore } = await import('@/store/taskStore')
    await waitFor(() => {
      const fact = useTaskStore.getState().activeTaskState?.facts?.nominal_pipe_size as
        | { display_value?: string }
        | undefined
      expect(fact?.display_value).toBe('6')
    })

    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(
      screen.getByText(/minimum required wall thickness for straight pipe under internal pressure/i),
    ).toBeInTheDocument()

    expect(screen.queryByRole('heading', { name: 'Engineering report' })).not.toBeInTheDocument()
  })

  it('keeps explanation text visible after advancing to the next parameter prompt', async () => {
    const { default: App } = await import('@/App')
    const user = userEvent.setup()

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Create new task' })).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: 'Create new task' }))
    await user.click(screen.getByRole('button', { name: /pipe wall thickness design/i }))

    await waitFor(() => {
      expect(
        screen.getByText(/minimum required wall thickness for straight pipe under internal pressure/i),
      ).toBeInTheDocument()
    })

    await selectNominalPipeSize(user)

    await waitFor(() => {
      expect(
        screen.getByText(/minimum required wall thickness for straight pipe under internal pressure/i),
      ).toBeInTheDocument()
    })

    expect(
      screen.getAllByText(/Select the nominal pipe size|Waiting for nominal pipe size/i).length,
    ).toBeGreaterThan(0)
  })
})
