import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { NextWorkflowsOutput } from '@/components/outputs/NextWorkflowsOutput'

const createTask = vi.fn()

vi.mock('@/store/taskStore', () => ({
  useTaskStore: (selector: (state: { createTask: typeof createTask }) => unknown) =>
    selector({ createTask }),
}))

describe('NextWorkflowsOutput', () => {
  it('renders only Related Workflows lines without intro or descriptions', () => {
    render(
      <NextWorkflowsOutput
        block={{
          id: 'next-workflows-task-1-pipe_wall_thickness_design',
          type: 'next_workflows',
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

    expect(screen.getByText('Related Workflows: MAWP Design')).toBeTruthy()
    expect(screen.queryByText('Suggested next workflows')).toBeNull()
    expect(screen.queryByText('Calculate MAWP from thickness.')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Start workflow' })).toBeNull()
  })

  it('starts workflow when the related workflow line is clickable', () => {
    render(
      <NextWorkflowsOutput
        block={{
          id: 'next-workflows-task-1-pipe_wall_thickness_design',
          type: 'next_workflows',
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

    fireEvent.click(screen.getByRole('button', { name: 'Related Workflows: MAWP Design' }))
    expect(createTask).toHaveBeenCalledWith('mawp_design')
  })
})
