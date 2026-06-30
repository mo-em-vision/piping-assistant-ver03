import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NodeEditTab } from '@/components/dev/NodeEditTab'
import { devStudioApi } from '@/dev-studio/api/devStudioApi'
import { useTaskStore } from '@/store/taskStore'

vi.mock('@/dev-studio/api/devStudioApi', () => ({
  devStudioApi: {
    getNode: vi.fn(),
    getNodeTypes: vi.fn(),
    validateNode: vi.fn(),
    updateNode: vi.fn(),
  },
}))

describe('NodeEditTab', () => {
  const refreshActiveTask = vi.fn().mockResolvedValue(undefined)

  beforeEach(() => {
    vi.clearAllMocks()
    useTaskStore.setState({
      refreshActiveTask,
    } as Partial<ReturnType<typeof useTaskStore.getState>>)

    vi.mocked(devStudioApi.getNode).mockResolvedValue({
      pack: 'asme_b31.3',
      id: 'B313-PARAM-MATERIAL',
      type: 'parameter',
      metadata: {
        id: 'B313-PARAM-MATERIAL',
        type: 'parameter',
        title: 'Material',
        question: 'Select the pipe material.',
        input_id: 'material',
      },
      body: '',
      source_rel_path: 'nodes/material/node.yaml',
      incoming: [],
      outgoing: [],
    })
    vi.mocked(devStudioApi.getNodeTypes).mockResolvedValue({
      types: [
        {
          type: 'parameter',
          required: ['id', 'type', 'input_id'],
          sections: {
            general: ['id', 'type', 'title', 'input_id'],
            ui: ['question'],
          },
          graph_fields: [],
        },
      ],
    })
    vi.mocked(devStudioApi.validateNode).mockResolvedValue({ valid: true, errors: [], warnings: [] })
    vi.mocked(devStudioApi.updateNode).mockResolvedValue({
      pack: 'asme_b31.3',
      id: 'B313-PARAM-MATERIAL',
      type: 'parameter',
      metadata: {
        id: 'B313-PARAM-MATERIAL',
        type: 'parameter',
        title: 'Material',
        question: 'Updated material question.',
        input_id: 'material',
      },
      body: '',
      source_rel_path: 'nodes/material/node.yaml',
      incoming: [],
      outgoing: [],
    })
  })

  it('refreshes the active task after saving', async () => {
    render(
      <NodeEditTab nodeId="B313-PARAM-MATERIAL" pack="asme_b31.3" sourceField="question" />,
    )

    expect(await screen.findByDisplayValue('Select the pipe material.')).toBeInTheDocument()

    fireEvent.change(screen.getByDisplayValue('Select the pipe material.'), {
      target: { value: 'Updated material question.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save node' }))

    await waitFor(() => {
      expect(devStudioApi.updateNode).toHaveBeenCalled()
      expect(refreshActiveTask).toHaveBeenCalled()
    })
  })
})
