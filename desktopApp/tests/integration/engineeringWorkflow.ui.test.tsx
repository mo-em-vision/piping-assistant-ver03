import { render, screen, waitFor, within } from '@testing-library/react'
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

  it('creates a task, submits input, and generates a report', async () => {
    const { default: App } = await import('@/App')
    const user = userEvent.setup()

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ New engineering task' })).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: '+ New engineering task' }))

    expect(screen.getByRole('heading', { name: 'Pipe Thickness Calculation' })).toBeInTheDocument()

    const inputsHeading = screen.getByRole('heading', { name: 'Engineering inputs' })
    const inputsSection = inputsHeading.closest('section')
    expect(inputsSection).not.toBeNull()

    const npsField = within(inputsSection as HTMLElement).getByRole('textbox')
    await user.clear(npsField)
    await user.type(npsField, '6')
    await user.click(within(inputsSection as HTMLElement).getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(screen.getByText('6')).toBeInTheDocument()
    })

    const reportSection = screen.getByRole('heading', { name: 'Engineering report' }).closest('section')
    await user.click(within(reportSection as HTMLElement).getByRole('button', { name: 'Generate report' }))

    await waitFor(() => {
      expect(within(reportSection as HTMLElement).getByText('Generated')).toBeInTheDocument()
    })
  })
})
