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

  it('shows dev badge only when dev mode is active', () => {
    render(<DevToolsHeaderControls />)

    expect(screen.getByRole('checkbox')).toBeInTheDocument()
    expect(screen.queryByText('Dev')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox'))

    expect(screen.getByText('Dev')).toBeInTheDocument()
  })
})
