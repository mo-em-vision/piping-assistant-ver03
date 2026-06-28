import { create } from 'zustand'

import {
  clampLeftPanelWidth,
  clampRightPanelWidth,
  DEFAULT_LEFT_WIDTH,
  DEFAULT_RIGHT_WIDTH,
  getDefaultRightWidth,
  MIN_PANEL_WIDTH,
  shouldSnapRightWidthToDefault,
} from '@/utils/panelLayout'

interface CreateTaskDialogState {
  open: boolean
  preselectedWorkflowId?: string
}

interface UiState {
  leftWidth: number
  rightWidth: number
  maxRightWidth: number
  isFullScreen: boolean
  leftCollapsed: boolean
  rightCollapsed: boolean
  createTaskDialog: CreateTaskDialogState
  setLeftWidth: (width: number) => void
  setRightWidth: (width: number, maxWidth?: number) => void
  setMaxRightWidth: (maxWidth: number) => void
  setFullScreen: (isFullScreen: boolean) => void
  toggleLeftCollapsed: () => void
  toggleRightCollapsed: () => void
  openCreateTaskDialog: (workflowId?: string) => void
  closeCreateTaskDialog: () => void
}

export const useUiStore = create<UiState>((set, get) => ({
  leftWidth: DEFAULT_LEFT_WIDTH,
  rightWidth: DEFAULT_RIGHT_WIDTH,
  maxRightWidth: MIN_PANEL_WIDTH,
  isFullScreen: false,
  leftCollapsed: false,
  rightCollapsed: true,
  createTaskDialog: { open: false },
  setLeftWidth: (width) => set({ leftWidth: clampLeftPanelWidth(width) }),
  setMaxRightWidth: (maxWidth) => {
    const nextMax = Math.max(MIN_PANEL_WIDTH, maxWidth)
    const state = get()

    if (nextMax <= MIN_PANEL_WIDTH) {
      set({ maxRightWidth: nextMax })
      return
    }

    const preferredDefault = getDefaultRightWidth(state.isFullScreen)
    let nextWidth = state.rightWidth

    if (
      shouldSnapRightWidthToDefault(
        state.rightWidth,
        state.maxRightWidth,
        nextMax,
        state.isFullScreen,
      )
    ) {
      nextWidth = preferredDefault
    }

    set({
      maxRightWidth: nextMax,
      rightWidth: clampRightPanelWidth(nextWidth, nextMax),
    })
  },
  setRightWidth: (width, maxWidth) => {
    const limit = maxWidth ?? get().maxRightWidth
    set({ rightWidth: clampRightPanelWidth(width, limit) })
  },
  setFullScreen: (isFullScreen) => {
    const state = get()
    if (state.isFullScreen === isFullScreen) {
      return
    }

    const previousDefault = getDefaultRightWidth(state.isFullScreen)
    const nextDefault = getDefaultRightWidth(isFullScreen)
    const shouldApplyDefault = state.rightWidth === previousDefault
    const updates: Partial<Pick<UiState, 'isFullScreen' | 'rightWidth'>> = { isFullScreen }

    if (shouldApplyDefault && state.maxRightWidth > MIN_PANEL_WIDTH) {
      updates.rightWidth = clampRightPanelWidth(nextDefault, state.maxRightWidth)
    }

    set(updates)
  },
  toggleLeftCollapsed: () => set((state) => ({ leftCollapsed: !state.leftCollapsed })),
  toggleRightCollapsed: () => set((state) => ({ rightCollapsed: !state.rightCollapsed })),
  openCreateTaskDialog: (workflowId) =>
    set({
      createTaskDialog: {
        open: true,
        preselectedWorkflowId: workflowId,
      },
    }),
  closeCreateTaskDialog: () =>
    set({
      createTaskDialog: {
        open: false,
        preselectedWorkflowId: undefined,
      },
    }),
}))
