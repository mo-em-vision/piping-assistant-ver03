import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { NextWorkflowsOutput } from '@/components/outputs/NextWorkflowsOutput'

const createTask = vi.fn()

vi.mock('@/store/taskStore', () => ({
  useTaskStore: (selector: (state: { createTask: typeof createTask }) => unknown) =>
    selector({ createTask }),
}))

describe('NextWorkflowsOutput', () => {
  it('renders read-only suggestions when no action is provided', () => {
    render(
      <NextWorkflowsOutput
        block={{
          id: 'next-workflows-task-1-pipe_wall_thickness_design',
          type: 'next_workflows',
          title: 'Suggested next workflows',
          content: 'Based on this workflow, you may continue with:',
          suggestions: [
            {
              workflow_id: 'mawp_design',
              title: 'MAWP Design',
              description: 'Calculate MAWP from thickness.',
              available: false,
            },
          ],
        }}
      />,
    )

    expect(screen.getByText('MAWP Design')).toBeTruthy()
    expect(screen.getByText('Calculate MAWP from thickness.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Start workflow' })).toBeNull()
  })

  it('renders start action only when backend provides it', () => {
    render(
      <NextWorkflowsOutput
        block={{
          id: 'next-workflows-task-1-pipe_wall_thickness_design',
          type: 'next_workflows',
          title: 'Suggested next workflows',
          content: 'Based on this workflow, you may continue with:',
          suggestions: [
            {
              workflow_id: 'mawp_design',
              title: 'MAWP Design',
              available: true,
              action: { type: 'start_workflow', workflow_id: 'mawp_design' },
            },
          ],
        }}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Start workflow' }))
    expect(createTask).toHaveBeenCalledWith('mawp_design')
  })
})
