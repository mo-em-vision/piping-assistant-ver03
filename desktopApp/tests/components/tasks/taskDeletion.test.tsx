import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { WorkflowHeader } from '@/components/workflow/WorkflowHeader'
import { TaskContextMenu } from '@/components/tasks/TaskContextMenu'

describe('WorkflowHeader', () => {
  it('calls onDelete when delete is clicked', () => {
    const onDelete = vi.fn()
    render(
      <WorkflowHeader
        taskName="Pipe Wall Thickness Design"
        onDelete={onDelete}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /delete pipe wall thickness design/i }))
    expect(onDelete).toHaveBeenCalledTimes(1)
  })
})

describe('TaskContextMenu', () => {
  it('calls onDelete for the selected task', () => {
    const onDelete = vi.fn()
    const onClose = vi.fn()
    const task = {
      id: 'pipe-wall-thickness-desi-test01',
      name: 'Pipe Wall Thickness Design',
      description: 'ASME B31.3 wall thickness design workflow',
      discipline: 'Piping',
      status: 'in_progress',
    }

    render(
      <TaskContextMenu task={task} x={120} y={80} onDelete={onDelete} onClose={onClose} />,
    )

    fireEvent.click(screen.getByRole('menuitem', { name: /delete task/i }))
    expect(onDelete).toHaveBeenCalledWith(task)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
