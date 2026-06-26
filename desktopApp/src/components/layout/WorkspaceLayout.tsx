import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { ConnectionErrorBanner } from '@/components/errors/ConnectionErrorBanner'
import { useWindowDisplayState } from '@/hooks/useWindowDisplayState'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { computeMaxRightPanelWidth } from '@/utils/panelLayout'

import { AppHeader } from './AppHeader'
import { CenterPanel } from './CenterPanel'
import { LeftPanel } from './LeftPanel'
import { ResizeHandle } from './ResizeHandle'
import { RightPanel } from './RightPanel'
import './SidePanel.css'
import './WorkspaceLayout.css'

import type { BackendStatusPayload } from '@/config/constants'

interface WorkspaceLayoutProps {
  backendStatus: BackendStatusPayload
  isRetrying: boolean
  onRetryBackend: () => void
  onReloadWorkspace: () => void
}

export function WorkspaceLayout({
  backendStatus,
  isRetrying,
  onRetryBackend,
  onReloadWorkspace,
}: WorkspaceLayoutProps) {
  const activeTask = useTaskStore((state) => state.activeTask)
  const leftWidth = useUiStore((state) => state.leftWidth)
  const rightWidth = useUiStore((state) => state.rightWidth)
  const leftCollapsed = useUiStore((state) => state.leftCollapsed)
  const rightCollapsed = useUiStore((state) => state.rightCollapsed)
  const setLeftWidth = useUiStore((state) => state.setLeftWidth)
  const setRightWidth = useUiStore((state) => state.setRightWidth)
  const setMaxRightWidth = useUiStore((state) => state.setMaxRightWidth)
  const toggleLeftCollapsed = useUiStore((state) => state.toggleLeftCollapsed)
  const toggleRightCollapsed = useUiStore((state) => state.toggleRightCollapsed)

  useWindowDisplayState()

  const bodyRef = useRef<HTMLDivElement>(null)
  const [workspaceBodyWidth, setWorkspaceBodyWidth] = useState(0)

  const rightPanelVisible = Boolean(activeTask) && !rightCollapsed

  const maxRightWidth = useMemo(
    () =>
      computeMaxRightPanelWidth({
        workspaceWidth: workspaceBodyWidth,
        leftWidth,
        leftCollapsed,
        rightPanelVisible,
      }),
    [workspaceBodyWidth, leftWidth, leftCollapsed, rightPanelVisible],
  )

  useEffect(() => {
    const body = bodyRef.current
    if (!body) {
      return
    }

    const updateWidth = () => {
      setWorkspaceBodyWidth(body.clientWidth)
    }

    updateWidth()

    const observer = new ResizeObserver(updateWidth)
    observer.observe(body)

    return () => {
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    setMaxRightWidth(maxRightWidth)
  }, [maxRightWidth, setMaxRightWidth])

  const handleLeftResize = useCallback(
    (delta: number) => {
      setLeftWidth(useUiStore.getState().leftWidth + delta)
    },
    [setLeftWidth],
  )

  const handleRightResize = useCallback(
    (delta: number) => {
      const state = useUiStore.getState()
      setRightWidth(state.rightWidth - delta, maxRightWidth)
    },
    [maxRightWidth, setRightWidth],
  )

  return (
    <div className="workspace">
      <AppHeader
        backendStatus={backendStatus}
        isRetrying={isRetrying}
        onRetry={onRetryBackend}
      />

      <ConnectionErrorBanner
        backendStatus={backendStatus}
        isRetrying={isRetrying}
        onRetryBackend={onRetryBackend}
        onReloadWorkspace={onReloadWorkspace}
      />

      <div ref={bodyRef} className="workspace__body">
        {leftCollapsed ? (
          <div className="panel-collapsed-rail">
            <button
              type="button"
              onClick={toggleLeftCollapsed}
              aria-label="Expand navigation panel"
              title="Expand navigation"
            >
              ›
            </button>
            <p className="panel-collapsed-rail__label" aria-hidden="true">
              Navigation/Projects/Tasks
            </p>
          </div>
        ) : (
          <>
            <div className="workspace__panel workspace__panel--left" style={{ width: leftWidth }}>
              <LeftPanel />
            </div>
            <ResizeHandle onResizeDelta={handleLeftResize} />
          </>
        )}

        <div className="workspace__panel workspace__panel--center">
          <CenterPanel />
        </div>

        {activeTask ? (
          rightCollapsed ? (
            <div className="panel-collapsed-rail panel-collapsed-rail--right">
              <button
                type="button"
                onClick={toggleRightCollapsed}
                aria-label="Expand task context panel"
                title="Expand task context"
              >
                ‹
              </button>
              <p className="panel-collapsed-rail__label" aria-hidden="true">
                Tasks/AI Chat/References
              </p>
            </div>
          ) : (
            <>
              <ResizeHandle onResizeDelta={handleRightResize} />
              <div
                className="workspace__panel workspace__panel--right"
                style={{ width: rightWidth, maxWidth: maxRightWidth }}
              >
                <RightPanel />
              </div>
            </>
          )
        ) : null}
      </div>
    </div>
  )
}
