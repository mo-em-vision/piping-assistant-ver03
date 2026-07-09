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

const durableExplanation: DisplayOutputBlock = {
  id: 'preview-intro',
  type: 'text',
  lifecycle: 'durable',
  content: 'The minimum required wall thickness shall be computed.',
}

const stableEq2Block: DisplayOutputBlock = {
  id: 'equation-asme-b313-304-1-1-eq-2',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'calculation_trace',
  equation_node_id: 'asme-b313-304-1-1-eq-2',
  content: 't_m = t + c',
  display: 't_m = t + c',
}

const stableEq3Block: DisplayOutputBlock = {
  id: 'equation-asme-b313-304-1-2-eq-3a',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'calculation_trace',
  equation_node_id: 'asme-b313-304-1-2-eq-3a',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
}

const previewEquation: DisplayOutputBlock = {
  id: 'path-preview-equation-B313-304.1.2',
  type: 'equation',
  lifecycle: 'preview',
  display_channel: 'current_equation_preview',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
}

const legacyPreviewEquation: DisplayOutputBlock = {
  id: 'path-preview-equation-304.1.1-a',
  type: 'equation',
  content: 't_m = t + c',
  display: 't_m = t + c',
}

describe('withPreservedDisplayOutputs', () => {
  beforeEach(() => {
    clearTranscriptCache()
  })

  it('merges durable in-session blocks for the same task', () => {
    const previous = createTaskState({
      display_outputs: [durableExplanation],
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

    expect(merged.display_outputs).toHaveLength(1)
    expect(merged.display_outputs[0]).toEqual(durableExplanation)
    expect(loadTranscriptCache(previous.task_id)).toHaveLength(1)
  })

  it('retains durable equation blocks when focus advances', () => {
    const taskId = 'pipe-wall-thickness-focus-advance'
    saveTranscriptCache(taskId, [stableEq2Block, durableExplanation])

    const incoming = createTaskState({
      task_id: taskId,
      display_outputs: [stableEq3Block],
    })

    const merged = withPreservedDisplayOutputs(null, incoming)

    expect(merged.display_outputs.map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'preview-intro',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
    expect(loadTranscriptCache(taskId).map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'preview-intro',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('strips legacy preview equations from cache and merges durable incoming blocks', () => {
    const taskId = 'pipe-wall-thickness-test01'
    saveTranscriptCache(taskId, [legacyPreviewEquation, durableExplanation])

    const incoming = createTaskState({
      task_id: taskId,
      display_outputs: [stableEq3Block],
    })

    const merged = withPreservedDisplayOutputs(null, incoming)

    expect(merged.display_outputs.map((block) => block.id)).toEqual([
      'preview-intro',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
    expect(loadTranscriptCache(taskId).map((block) => block.id)).toEqual([
      'preview-intro',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('does not inherit another task transcript on task switch', () => {
    const taskA = createTaskState({
      task_id: 'task-a',
      display_outputs: [durableExplanation],
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

    expect(merged.display_outputs).toHaveLength(0)
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

  it('preserves durable blocks after submitParameter when backend omits them', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    let currentTask = createTaskState({
      display_outputs: [durableExplanation, previewEquation],
      current_ask: {
        kind: 'input',
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size.',
      },
    })

    installFetchMock({
      [`/api/v1/tasks/${currentTask.task_id}/inputs`]: () => {
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
      [`/api/v1/tasks/${currentTask.task_id}`]: (init) => {
        const method = (init?.method ?? 'GET').toUpperCase()
        if (method === 'GET') {
          return jsonResponse(currentTask)
        }
        return jsonResponse({ error: { code: 'not_found', message: 'unhandled' } }, 404)
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
    expect(outputs.some((block) => block.id === durableExplanation.id)).toBe(true)
    expect(outputs.some((block) => block.id === previewEquation.id)).toBe(false)
    expect(outputs.some((block) => block.id === 'planning-status')).toBe(false)
  })

  it('loadWorkspace restores cached durable transcript on cold Zustand', async () => {
    const { createTaskState, jsonResponse } = await import('../helpers/apiMocks')

    const taskState = createTaskState({
      display_outputs: [],
    })

    saveTranscriptCache(taskState.task_id, [durableExplanation])
    localStorage.setItem('desktop:activeProjectId', 'default')

    installFetchMock({
      '/api/v1/workflows': () =>
        jsonResponse({
          workflows: [
            {
              id: 'pipe_wall_thickness_design',
              name: 'Pipe Wall Thickness Design',
              description: 'ASME B31.3',
              discipline: 'Piping',
              available: true,
            },
          ],
        }),
      '/api/v1/recent-tasks': () => jsonResponse({ recent_tasks: [] }),
      [`/api/v1/tasks/${taskState.task_id}`]: () => jsonResponse(taskState),
      '/api/v1/tasks?': () =>
        jsonResponse({
          session_id: 'default',
          active_task_id: taskState.task_id,
          tasks: [],
        }),
    })

    const { useTaskStore } = await import('@/store/taskStore')
    const { useProjectStore } = await import('@/store/projectStore')
    useProjectStore.setState({ activeProjectId: 'default' })
    useTaskStore.setState({
      sessionId: null,
      activeTask: null,
      activeTaskState: null,
    })

    await useTaskStore.getState().loadWorkspace()

    const outputs = useTaskStore.getState().activeTaskState?.display_outputs ?? []
    expect(outputs.some((block) => block.id === durableExplanation.id)).toBe(true)
  })
})
