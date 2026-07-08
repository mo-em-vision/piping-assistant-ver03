import { vi } from 'vitest'

import type { TaskStateDto } from '@/types/backend/api'

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function createTaskState(overrides: Partial<TaskStateDto> = {}): TaskStateDto {
  return {
    task_id: 'pipe-wall-thickness-test01',
    name: 'Pipe Wall Thickness Design',
    workflow_id: 'pipe_wall_thickness_design',
    discipline: 'Piping',
    description: 'ASME B31.3 wall thickness design',
    status: 'awaiting_input',
    active_nodes: [],
    progress: {
      timeline: [],
      steps: [],
      missing_inputs: ['nominal_pipe_size'],
      missing_assumptions: [],
      step_progress: [],
    },
    inputs: {},
    outputs: {},
    warnings: [],
    parameters: [
      {
        name: 'nominal_pipe_size',
        label: 'Nominal Pipe Size',
        type: 'text',
        required: true,
        units: [],
        default_unit: 'dimensionless',
        default_value: null,
        value: null,
        options: null,
        validation: null,
        status: 'pending',
        requires_confirmation: false,
      },
    ],
    display_outputs: [],
    options: { available_workflows: [] },
    errors: [],
    ...overrides,
  }
}

export function installFetchMock(handlers: Record<string, (init?: RequestInit) => Response | Promise<Response>>) {
  const orderedHandlers = Object.entries(handlers).sort(
    ([left], [right]) => right.length - left.length,
  )

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const method = (init?.method ?? 'GET').toUpperCase()
    const key = `${method} ${url}`

    for (const [pattern, handler] of orderedHandlers) {
      if (key.includes(pattern) || url.includes(pattern)) {
        return handler(init)
      }
    }

    return jsonResponse(
      {
        error: {
          code: 'not_found',
          message: `Unhandled fetch in test: ${method} ${url}`,
        },
      },
      404,
    )
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
