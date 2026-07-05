import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DevToolsHeaderControls } from '@/components/layout/DevToolsHeaderControls'
import { useDevToolsStore } from '@/store/devToolsStore'

vi.mock('@/config/env', () => ({
  env: { devToolsAvailable: true },
}))

describe('DevToolsHeaderControls', () => {
  beforeEach(() => {
    useDevToolsStore.setState({ devModeActive: false })
  })

  it('shows inspector controls only when dev mode is active', () => {
    render(<DevToolsHeaderControls />)

    expect(screen.getByRole('checkbox')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /inspector/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox'))

    expect(screen.getByRole('button', { name: /inspector/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /node dev studio/i })).toBeInTheDocument()
  })
})
