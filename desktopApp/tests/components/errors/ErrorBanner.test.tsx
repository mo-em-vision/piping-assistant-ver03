import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { invalidInputError, retryableApiError } from '../../fixtures/userErrors'

describe('ErrorBanner', () => {
  it('renders structured error details', () => {
    render(<ErrorBanner error={retryableApiError} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Cannot reach API')).toBeInTheDocument()
    expect(screen.getByText('What happened')).toBeInTheDocument()
    expect(screen.getByText('Network request failed.')).toBeInTheDocument()
    expect(screen.getByText('Possible reason')).toBeInTheDocument()
    expect(screen.getByText('Next action')).toBeInTheDocument()
  })

  it('shows retry button for retryable errors', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(<ErrorBanner error={retryableApiError} onRetry={onRetry} retryLabel="Retry connection" />)

    const retry = screen.getByRole('button', { name: 'Retry connection' })
    await user.click(retry)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('hides retry button when error is not retryable', () => {
    render(<ErrorBanner error={invalidInputError} onRetry={vi.fn()} />)

    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  it('renders compact summary without detail labels', () => {
    render(<ErrorBanner error={invalidInputError} compact />)

    expect(screen.queryByText('What happened')).not.toBeInTheDocument()
    expect(screen.getByText(invalidInputError.nextAction)).toBeInTheDocument()
  })
})
