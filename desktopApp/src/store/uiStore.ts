import { create } from 'zustand'

const MIN_PANEL_WIDTH = 200
const MAX_PANEL_WIDTH = 480
const DEFAULT_LEFT_WIDTH = 260
const DEFAULT_RIGHT_WIDTH = 320

interface UiState {
  leftWidth: number
  rightWidth: number
  leftCollapsed: boolean
  rightCollapsed: boolean
  setLeftWidth: (width: number) => void
  setRightWidth: (width: number) => void
  toggleLeftCollapsed: () => void
  toggleRightCollapsed: () => void
}

function clampPanelWidth(width: number): number {
  return Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, width))
}

export const useUiStore = create<UiState>((set) => ({
  leftWidth: DEFAULT_LEFT_WIDTH,
  rightWidth: DEFAULT_RIGHT_WIDTH,
  leftCollapsed: false,
  rightCollapsed: false,
  setLeftWidth: (width) => set({ leftWidth: clampPanelWidth(width) }),
  setRightWidth: (width) => set({ rightWidth: clampPanelWidth(width) }),
  toggleLeftCollapsed: () => set((state) => ({ leftCollapsed: !state.leftCollapsed })),
  toggleRightCollapsed: () => set((state) => ({ rightCollapsed: !state.rightCollapsed })),
}))
