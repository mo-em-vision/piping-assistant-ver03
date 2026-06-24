import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TimelineStep } from '@/components/engineering/TimelineStep'

describe('TimelineStep edit affordance', () => {
  it('shows edit control and calls onEdit', () => {
    const onEdit = vi.fn()
    render(
      <TimelineStep
        title="Design pressure"
        status="done"
        displayValue="8 bar"
        editable
        onEdit={onEdit}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Edit Design pressure' }))
    expect(onEdit).toHaveBeenCalledTimes(1)
  })
})
