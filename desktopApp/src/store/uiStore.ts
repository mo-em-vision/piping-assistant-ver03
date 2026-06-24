import { create } from 'zustand'

import {
  clampLeftPanelWidth,
  clampRightPanelWidth,
  DEFAULT_LEFT_WIDTH,
  DEFAULT_RIGHT_WIDTH,
  MIN_PANEL_WIDTH,
} from '@/utils/panelLayout'

interface UiState {
  leftWidth: number
  rightWidth: number
  maxRightWidth: number
  leftCollapsed: boolean
  rightCollapsed: boolean
  setLeftWidth: (width: number) => void
  setRightWidth: (width: number, maxWidth?: number) => void
  setMaxRightWidth: (maxWidth: number) => void
  toggleLeftCollapsed: () => void
  toggleRightCollapsed: () => void
}

export const useUiStore = create<UiState>((set, get) => ({
  leftWidth: DEFAULT_LEFT_WIDTH,
  rightWidth: DEFAULT_RIGHT_WIDTH,
  maxRightWidth: MIN_PANEL_WIDTH,
  leftCollapsed: false,
  rightCollapsed: false,
  setLeftWidth: (width) => set({ leftWidth: clampLeftPanelWidth(width) }),
  setMaxRightWidth: (maxWidth) => {
    const nextMax = Math.max(MIN_PANEL_WIDTH, maxWidth)
    const rightWidth = clampRightPanelWidth(get().rightWidth, nextMax)
    set({ maxRightWidth: nextMax, rightWidth })
  },
  setRightWidth: (width, maxWidth) => {
    const limit = maxWidth ?? get().maxRightWidth
    set({ rightWidth: clampRightPanelWidth(width, limit) })
  },
  toggleLeftCollapsed: () => set((state) => ({ leftCollapsed: !state.leftCollapsed })),
  toggleRightCollapsed: () => set((state) => ({ rightCollapsed: !state.rightCollapsed })),
}))
