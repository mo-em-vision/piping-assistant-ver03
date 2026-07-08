import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { saveTranscriptCache } from '@/utils/transcriptCache'

describe('transcript reload UI', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_MOCK_DATA', 'false')
    sessionStorage.clear()
  })

  it('restores explanation and equation blocks after workspace reload', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    const taskState = createTaskState({
      display_outputs: [],
      flow_guidance: {
        transcript_blocks: [],
      },
    })

    saveTranscriptCache(taskState.task_id, [
      {
        id: 'preview-intro',
        type: 'text',
        content: 'The minimum required wall thickness shall be computed.',
      },
      {
        id: 'preview-equation',
        type: 'equation',
        title: 'Governing equation',
        content: 't = PD / 2(SEW + PY)',
        display: 't = PD / 2(SEW + PY)',
      },
    ])

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString()
        const method = (init?.method ?? 'GET').toUpperCase()

        if (url.includes('/health')) {
          return jsonResponse({ status: 'ok' })
        }

        if (url.includes('/api/v1/workflows')) {
          return jsonResponse({
            workflows: [
              {
                id: 'pipe_wall_thickness_design',
                name: 'Pipe Wall Thickness Design',
                description: 'ASME B31.3',
                discipline: 'Piping',
                available: true,
              },
            ],
          })
        }

        if (url.includes('/api/v1/recent-tasks')) {
          return jsonResponse({ recent_tasks: [] })
        }

        if (url.includes('/api/v1/projects')) {
          return jsonResponse({
            projects: [{ id: 'default', name: 'Default Project' }],
          })
        }

        if (url.match(/\/api\/v1\/tasks(\?|$)/) && method === 'GET') {
          return jsonResponse({
            session_id: 'default',
            active_task_id: taskState.task_id,
            tasks: [
              {
                id: taskState.task_id,
                name: taskState.name,
                workflow_id: taskState.workflow_id,
                discipline: taskState.discipline,
                status: 'in_progress',
              },
            ],
          })
        }

        if (
          url.includes(`/api/v1/tasks/${taskState.task_id}`) &&
          method === 'GET' &&
          !url.includes('/inputs')
        ) {
          return jsonResponse(taskState)
        }

        return jsonResponse({ error: { code: 'not_found', message: `${method} ${url}` } }, 404)
      }),
    )

    vi.stubGlobal('electronAPI', {
      getBackendStatus: async () => ({
        status: 'connected',
        url: 'http://127.0.0.1:8000',
      }),
      onBackendStatusChange: () => () => undefined,
      retryBackendConnection: async () => ({
        status: 'connected',
        url: 'http://127.0.0.1:8000',
      }),
    })

    const { useProjectStore } = await import('@/store/projectStore')
    const { useTaskStore } = await import('@/store/taskStore')
    const { CenterPanel } = await import('@/components/layout/CenterPanel')

    useProjectStore.setState({ activeProjectId: 'default', projects: [{ id: 'default', name: 'Default Project' }] })
    useTaskStore.setState({
      sessionId: null,
      activeTask: null,
      activeTaskState: null,
    })

    await useTaskStore.getState().loadWorkspace()

    render(<CenterPanel />)

    await waitFor(() => {
      expect(
        screen.getByText(/minimum required wall thickness shall be computed/i),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('Governing equation')).toBeInTheDocument()
  })
})
