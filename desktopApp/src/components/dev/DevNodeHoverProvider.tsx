import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { DevNodeTooltip } from '@/components/dev/DevNodeTooltip'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useUiStore } from '@/store/uiStore'
import type { NodeProvenanceDto } from '@/types/backend/api'

const DEFAULT_PACK = 'asme_b31.3'
const HIDE_DELAY_MS = 200

interface HoverState {
  provenance: NodeProvenanceDto
  x: number
  y: number
}

interface DevNodeHoverContextValue {
  showHover: (provenance: NodeProvenanceDto, x: number, y: number) => void
  hideHover: () => void
}

const DevNodeHoverContext = createContext<DevNodeHoverContextValue | null>(null)

export function DevNodeHoverProvider({ children }: { children: ReactNode }) {
  const [hover, setHover] = useState<HoverState | null>(null)
  const hideTimeoutRef = useRef<number | null>(null)

  const cancelScheduledHide = useCallback(() => {
    if (hideTimeoutRef.current != null) {
      window.clearTimeout(hideTimeoutRef.current)
      hideTimeoutRef.current = null
    }
  }, [])

  const showHover = useCallback(
    (provenance: NodeProvenanceDto, x: number, y: number) => {
      cancelScheduledHide()
      setHover({ provenance, x, y })
    },
    [cancelScheduledHide],
  )

  const hideHover = useCallback(() => {
    cancelScheduledHide()
    hideTimeoutRef.current = window.setTimeout(() => {
      setHover(null)
      hideTimeoutRef.current = null
    }, HIDE_DELAY_MS)
  }, [cancelScheduledHide])

  const openNodeEdit = useCallback((provenance: NodeProvenanceDto) => {
    cancelScheduledHide()
    setHover(null)
    useUiStore.setState({ rightCollapsed: false })
    useRightPanelStore.getState().openNodeEditTab(provenance.node_id, {
      pack: DEFAULT_PACK,
      sourceField: provenance.source_field ?? null,
      title: provenance.title ?? provenance.node_id,
    })
  }, [cancelScheduledHide])

  const value = useMemo(
    () => ({
      showHover,
      hideHover,
    }),
    [showHover, hideHover],
  )

  return (
    <DevNodeHoverContext.Provider value={value}>
      {children}
      {hover ? (
        <DevNodeTooltip
          provenance={hover.provenance}
          x={hover.x}
          y={hover.y}
          onOpenEdit={openNodeEdit}
          onMouseEnter={cancelScheduledHide}
          onMouseLeave={hideHover}
        />
      ) : null}
    </DevNodeHoverContext.Provider>
  )
}

export function useDevNodeHover(): DevNodeHoverContextValue | null {
  return useContext(DevNodeHoverContext)
}
