import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusIndicator } from '@/components/engineering/StatusIndicator'

describe('StatusIndicator', () => {
  it('uses default label for variant', () => {
    render(<StatusIndicator variant="warning" />)

    expect(screen.getByText('Awaiting input')).toHaveClass('status-indicator--warning')
  })

  it('allows custom label override', () => {
    render(<StatusIndicator variant="error" label="Calculation failed" />)

    expect(screen.getByText('Calculation failed')).toBeInTheDocument()
  })
})
