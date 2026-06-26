import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SidePanelContextMenu } from '@/components/layout/SidePanelContextMenu'

describe('SidePanelContextMenu', () => {
  it('calls item onClick when a menu item is selected', () => {
    const onDelete = vi.fn()
    const onClose = vi.fn()

    render(
      <SidePanelContextMenu
        x={120}
        y={80}
        ariaLabel="Actions for Test"
        onClose={onClose}
        items={[
          {
            label: 'Delete item',
            danger: true,
            onClick: onDelete,
          },
        ]}
      />,
    )

    fireEvent.click(screen.getByRole('menuitem', { name: /delete item/i }))
    expect(onDelete).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
