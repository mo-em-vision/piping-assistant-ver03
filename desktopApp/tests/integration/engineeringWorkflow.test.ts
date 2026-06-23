import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fromApiErrorBody, toUserFacingError } from '@/services/errors/errorMapper'
import { buildTaskStateViewModel } from '@/store/taskStateManager'
import { mockTaskState } from '@/mock/taskState.mock'

describe('errorMapper', () => {
  it('maps API recovery payload into user-facing error', () => {
    const error = fromApiErrorBody({
      code: 'invalid_input',
      message: 'nominal_pipe_size is required',
      details: { parameter: 'nominal_pipe_size' },
      recovery: {
        title: 'Invalid engineering input',
        what_happened: 'nominal_pipe_size is required',
        possible_reason: 'Validation failed.',
        next_action: 'Update `nominal_pipe_size` and submit again.',
        affected_parameter: 'nominal_pipe_size',
        affected_task: '',
      },
    })

    expect(error.title).toBe('Invalid engineering input')
    expect(error.affectedParameter).toBe('nominal_pipe_size')
    expect(error.retryable).toBe(false)
  })

  it('maps network failures to api_unreachable', () => {
    const error = toUserFacingError(new TypeError('Failed to fetch'))

    expect(error.code).toBe('api_unreachable')
    expect(error.retryable).toBe(true)
  })
})

describe('taskStateManager', () => {
  it('builds progress view model from backend task state', () => {
    const viewModel = buildTaskStateViewModel(mockTaskState)

    expect(viewModel).not.toBeNull()
    expect(viewModel?.statusLabel).toBe('Awaiting input')
    expect(viewModel?.completedCount).toBe(2)
    expect(viewModel?.totalCount).toBe(4)
    expect(viewModel?.currentStep?.title).toBe('Thickness')
  })
})

describe('taskStore API integration', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()
  })

  it('loads workspace from backend responses', async () => {
    const taskState = {
      task_id: 'pipe-wall-thickness-test01',
      name: 'Pipe Thickness Calculation',
      workflow_id: 'pipe_wall_thickness_design',
      discipline: 'Piping',
      description: 'ASME B31.3 wall thickness design',
      status: 'awaiting_input',
      active_nodes: [],
      progress: {
        timeline: [],
        steps: [],
        missing_inputs: [],
        missing_assumptions: [],
        step_progress: [],
      },
      inputs: {},
      outputs: {},
      warnings: [],
      parameters: [],
      display_outputs: [],
      options: { available_workflows: [] },
      errors: [],
    }

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.includes('/api/v1/workflows')) {
          return new Response(
            JSON.stringify({
              workflows: [
                {
                  id: 'pipe_wall_thickness_design',
                  name: 'Pipe Thickness Calculation',
                  description: 'ASME B31.3',
                  discipline: 'Piping',
                  available: true,
                },
              ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        }
        if (url.includes('/api/v1/tasks') && !url.includes('/api/v1/tasks/')) {
          return new Response(
            JSON.stringify({
              session_id: 'default',
              active_task_id: taskState.task_id,
              tasks: [],
              recent_tasks: [],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        }
        if (url.includes(`/api/v1/tasks/${taskState.task_id}`)) {
          return new Response(JSON.stringify(taskState), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        }
        return new Response(JSON.stringify({ error: { code: 'not_found', message: url } }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )

    const { useTaskStore } = await import('@/store/taskStore')
    await useTaskStore.getState().loadWorkspace()

    const state = useTaskStore.getState()
    expect(state.userError).toBeNull()
    expect(state.availableTasks).toHaveLength(1)
    expect(state.activeTask?.id).toBe(taskState.task_id)
    expect(state.activeTaskState?.name).toBe('Pipe Thickness Calculation')
  })

  it('stores user-facing error when backend request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(
          JSON.stringify({
            error: {
              code: 'internal_error',
              message: 'Database unavailable',
              recovery: {
                title: 'Unexpected server error',
                what_happened: 'Database unavailable',
                possible_reason: 'Unhandled failure.',
                next_action: 'Retry the action.',
                affected_parameter: '',
                affected_task: '',
              },
            },
          }),
          { status: 500, headers: { 'Content-Type': 'application/json' } },
        )
      }),
    )

    const { useTaskStore } = await import('@/store/taskStore')
    await useTaskStore.getState().loadWorkspace()

    const state = useTaskStore.getState()
    expect(state.userError?.code).toBe('internal_error')
    expect(state.userError?.whatHappened).toBe('Database unavailable')
    expect(state.userError?.retryable).toBe(true)
  })
})

describe('engineering workflow integration', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()
  })

  it('creates task, submits input, and generates report via API mocks', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    let currentTask = createTaskState()

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString()
        const method = (init?.method ?? 'GET').toUpperCase()

        if (url.includes('/api/v1/workflows')) {
          return jsonResponse({
            workflows: [
              {
                id: 'pipe_wall_thickness_design',
                name: 'Pipe Thickness Calculation',
                description: 'ASME B31.3',
                discipline: 'Piping',
                available: true,
              },
            ],
          })
        }

        if (method === 'POST' && url.endsWith('/api/v1/tasks')) {
          return jsonResponse(currentTask, 201)
        }

        if (url.match(/\/api\/v1\/tasks(\?|$)/) && method === 'GET') {
          return jsonResponse({
            session_id: 'default',
            active_task_id: currentTask.task_id,
            tasks: [],
            recent_tasks: [],
          })
        }

        if (url.includes(`/api/v1/tasks/${currentTask.task_id}`) && method === 'GET' && !url.includes('/reports')) {
          return jsonResponse(currentTask)
        }

        if (method === 'POST' && url.includes('/inputs')) {
          currentTask = createTaskState({
            inputs: {
              nominal_pipe_size: {
                input_id: 'nominal_pipe_size',
                value: '6',
                unit: 'dimensionless',
                display_value: '6',
              },
            },
            progress: {
              ...currentTask.progress,
              missing_inputs: [],
            },
            display_outputs: [
              {
                id: 'result-thickness',
                type: 'result',
                title: 'Required thickness',
                label: 'Required thickness',
                value: '4.2 mm',
                unit: 'mm',
                status: 'pass',
              },
            ],
          })
          return jsonResponse(currentTask)
        }

        if (url.includes('/reports') && method === 'POST') {
          return jsonResponse(
            {
              task_id: currentTask.task_id,
              status: 'PASS',
              generated: true,
              generation_status: 'ready',
              conclusion: 'Wall thickness calculation complete.',
              files: {
                html: { available: true, filename: 'report.html', updated_at: '2026-06-23T00:00:00Z' },
              },
            },
            201,
          )
        }

        if (url.includes('/reports/preview') && method === 'GET') {
          return jsonResponse({
            task_id: currentTask.task_id,
            format: 'html',
            content: '<html><body>Engineering report</body></html>',
          })
        }

        return jsonResponse({ error: { code: 'not_found', message: `${method} ${url}` } }, 404)
      }),
    )

    const { useTaskStore } = await import('@/store/taskStore')
    const { useReportStore } = await import('@/store/reportStore')

    await useTaskStore.getState().createTask('pipe_wall_thickness_design')
    expect(useTaskStore.getState().activeTask?.name).toBe('Pipe Thickness Calculation')

    await useTaskStore.getState().submitParameter('nominal_pipe_size', '6')
    const taskState = useTaskStore.getState().activeTaskState
    expect(taskState?.inputs.nominal_pipe_size).toBeTruthy()
    expect(taskState?.display_outputs.some((block) => block.type === 'result')).toBe(true)

    await useReportStore.getState().generateReport(currentTask.task_id, 'html')
    expect(useReportStore.getState().summary?.generated).toBe(true)
    expect(useReportStore.getState().userError).toBeNull()
  })
})
