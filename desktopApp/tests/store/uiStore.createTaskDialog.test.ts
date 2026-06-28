import { beforeEach, describe, expect, it } from 'vitest'

import { useUiStore } from '@/store/uiStore'

describe('uiStore create task dialog', () => {
  beforeEach(() => {
    useUiStore.setState({
      createTaskDialog: { open: false },
    })
  })

  it('opens the create task dialog with an optional preselected workflow', () => {
    useUiStore.getState().openCreateTaskDialog('pipe_wall_thickness_design')

    expect(useUiStore.getState().createTaskDialog).toEqual({
      open: true,
      preselectedWorkflowId: 'pipe_wall_thickness_design',
    })
  })

  it('closes the create task dialog and clears the preselected workflow', () => {
    useUiStore.getState().openCreateTaskDialog('pipe_wall_thickness_design')
    useUiStore.getState().closeCreateTaskDialog()

    expect(useUiStore.getState().createTaskDialog).toEqual({
      open: false,
      preselectedWorkflowId: undefined,
    })
  })
})
