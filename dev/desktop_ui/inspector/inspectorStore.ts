import { create } from 'zustand'

import type { InspectorTabId } from '@/types/backend/inspection'

interface InspectorState {
  open: boolean
  height: number
  activeTab: InspectorTabId
  selectedStepIndex: number | null
  replayFrameIndex: number
  selectedNodeId: string | null
  toggleOpen: () => void
  setOpen: (open: boolean) => void
  setHeight: (height: number) => void
  setActiveTab: (tab: InspectorTabId) => void
  selectStep: (stepIndex: number | null) => void
  selectNode: (nodeId: string | null) => void
  setReplayFrameIndex: (index: number) => void
}

export const useInspectorStore = create<InspectorState>((set) => ({
  open: false,
  height: 280,
  activeTab: 'trace',
  selectedStepIndex: null,
  replayFrameIndex: 0,
  selectedNodeId: null,
  toggleOpen: () => set((state) => ({ open: !state.open })),
  setOpen: (open) => set({ open }),
  setHeight: (height) =>
    set({
      height: Math.max(160, Math.min(height, Math.round(window.innerHeight * 0.85))),
    }),
  setActiveTab: (activeTab) => set({ activeTab }),
  selectStep: (selectedStepIndex) => set({ selectedStepIndex }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
  setReplayFrameIndex: (replayFrameIndex) => set({ replayFrameIndex }),
}))
