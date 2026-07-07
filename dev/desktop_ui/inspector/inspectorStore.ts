import { create } from 'zustand'

interface InspectorState {
  open: boolean
  height: number
  selectedStepIndex: number | null
  selectedNodeId: string | null
  toggleOpen: () => void
  setOpen: (open: boolean) => void
  setHeight: (height: number) => void
  selectStep: (stepIndex: number | null) => void
  selectNode: (nodeId: string | null) => void
}

export const useInspectorStore = create<InspectorState>((set) => ({
  open: false,
  height: 380,
  selectedStepIndex: null,
  selectedNodeId: null,
  toggleOpen: () => set((state) => ({ open: !state.open })),
  setOpen: (open) => set({ open }),
  setHeight: (height) =>
    set({
      height: Math.max(200, Math.min(height, Math.round(window.innerHeight * 0.85))),
    }),
  selectStep: (selectedStepIndex) => set({ selectedStepIndex }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
}))
