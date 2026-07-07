import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTaskState, installFetchMock } from '../helpers/apiMocks'
import { withPreservedDisplayOutputs } from '@/store/taskStore'
import { useProjectStore } from '@/store/projectStore'
import type { DisplayOutputBlock } from '@/types/backend/outputs'
import {
  clearTranscriptCache,
  loadTranscriptCache,
  saveTranscriptCache,
} from '@/utils/transcriptCache'

const equationBlock: DisplayOutputBlock = {
  id: 'path-preview-equation-B313-304.1.2',
  type: 'equation',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
}

describe('withPreservedDisplayOutputs', () => {
  beforeEach(() => {
    clearTranscriptCache()
  })

  it('merges in-session blocks for the same task', () => {
    const previous = createTaskState({
      display_outputs: [equationBlock],
    })
    const incoming = createTaskState({
      display_outputs: [
        {
          id: 'planning-status',
          type: 'text',
          content: 'Complete the fields below to continue.',
        },
      ],
    })

    const merged = withPreservedDisplayOutputs(previous, incoming)

    expect(merged.display_outputs).toHaveLength(2)
    expect(merged.display_outputs[0]).toEqual(equationBlock)
    expect(loadTranscriptCache(previous.task_id)).toHaveLength(2)
  })

  it('uses cached transcript on cold start for the same task', () => {
    const taskId = 'pipe-wall-thickness-test01'
    saveTranscriptCache(taskId, [equationBlock])

    const incoming = createTaskState({
      task_id: taskId,
      display_outputs: [],
    })

    const merged = withPreservedDisplayOutputs(null, incoming)

    expect(merged.display_outputs).toEqual([equationBlock])
  })

  it('does not inherit another task transcript on task switch', () => {
    const taskA = createTaskState({
      task_id: 'task-a',
      display_outputs: [equationBlock],
    })
    const taskB = createTaskState({
      task_id: 'task-b',
      display_outputs: [
        {
          id: 'planning-status',
          type: 'text',
          content: 'Task B status',
        },
      ],
    })

    const merged = withPreservedDisplayOutputs(taskA, taskB)

    expect(merged.display_outputs).toHaveLength(1)
    expect(merged.display_outputs[0]?.id).toBe('planning-status')
  })
})

describe('taskStore transcript integration', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()
    vi.stubEnv('VITE_MOCK_DATA', 'false')
    clearTranscriptCache()
    sessionStorage.clear()
  })

  it('preserves equation blocks after submitParameter when backend omits them', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    let currentTask = createTaskState({
      display_outputs: [equationBlock],
      current_ask: {
        kind: 'input',
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size.',
      },
    })

    installFetchMock({
      '/api/v1/tasks/': () =>
        jsonResponse({
          session_id: 'default',
          active_task_id: currentTask.task_id,
          tasks: [],
        }),
      [`/api/v1/tasks/${currentTask.task_id}`]: (init) => {
        const method = (init?.method ?? 'GET').toUpperCase()
        if (method === 'GET') {
          return jsonResponse(currentTask)
        }
        return jsonResponse({ error: { code: 'not_found', message: 'unhandled' } }, 404)
      },
      '/inputs': () => {
        currentTask = createTaskState({
          ...currentTask,
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
              id: 'planning-status',
              type: 'text',
              content: 'Updated status',
            },
          ],
        })
        return jsonResponse(currentTask)
      },
    })

    const { useTaskStore } = await import('@/store/taskStore')
    useProjectStore.setState({ activeProjectId: 'default' })
    useTaskStore.setState({
      sessionId: 'default',
      activeTask: {
        id: currentTask.task_id,
        name: currentTask.name,
        description: currentTask.description,
        discipline: currentTask.discipline,
        status: 'in_progress',
      },
      activeTaskState: currentTask,
    })

    await useTaskStore.getState().submitParameter('nominal_pipe_size', '6')

    const outputs = useTaskStore.getState().activeTaskState?.display_outputs ?? []
    expect(outputs.some((block) => block.id === equationBlock.id)).toBe(true)
    expect(outputs.some((block) => block.id === 'planning-status')).toBe(true)
    expect(outputs.some((block) => block.id === 'archived-prompt-nominal_pipe_size')).toBe(true)
  })

  it('loadWorkspace restores cached transcript on cold Zustand', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    const taskState = createTaskState({
      display_outputs: [],
    })

    saveTranscriptCache(taskState.task_id, [equationBlock])

    installFetchMock({
      '/api/v1/workflows': () =>
        jsonResponse({
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
      '/api/v1/recent-tasks': () => jsonResponse({ recent_tasks: [] }),
      '/api/v1/tasks': () =>
        jsonResponse({
          session_id: 'default',
          active_task_id: taskState.task_id,
          tasks: [],
        }),
      [`/api/v1/tasks/${taskState.task_id}`]: () => jsonResponse(taskState),
    })

    const { useTaskStore } = await import('@/store/taskStore')
    useProjectStore.setState({ activeProjectId: 'default' })
    useTaskStore.setState({
      sessionId: null,
      activeTask: null,
      activeTaskState: null,
    })

    await useTaskStore.getState().loadWorkspace()

    const outputs = useTaskStore.getState().activeTaskState?.display_outputs ?? []
    expect(outputs.some((block) => block.id === equationBlock.id)).toBe(true)
  })
})
