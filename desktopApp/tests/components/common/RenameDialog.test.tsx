import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { RenameDialog } from '@/components/common/RenameDialog'

describe('RenameDialog', () => {
  it('submits trimmed name on save', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    const onCancel = vi.fn()

    render(
      <RenameDialog
        open
        title="Rename project"
        label="Project name"
        initialName="Original"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    )

    const input = screen.getByLabelText('Project name')
    await user.clear(input)
    await user.type(input, '  Renamed Project  ')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(onConfirm).toHaveBeenCalledWith('Renamed Project')
  })

  it('disables save when name is empty', () => {
    render(
      <RenameDialog
        open
        title="Rename task"
        label="Task name"
        initialName="   "
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  it('calls onCancel when cancel is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <RenameDialog
        open
        title="Rename task"
        label="Task name"
        initialName="Task A"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
