import { useCallback } from 'react'

import { ConnectionErrorBanner } from '@/components/errors/ConnectionErrorBanner'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'

import { AppHeader } from './AppHeader'
import { CenterPanel } from './CenterPanel'
import { LeftPanel } from './LeftPanel'
import { ResizeHandle } from './ResizeHandle'
import { RightPanel } from './RightPanel'
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
  const toggleLeftCollapsed = useUiStore((state) => state.toggleLeftCollapsed)
  const toggleRightCollapsed = useUiStore((state) => state.toggleRightCollapsed)

  const handleLeftResize = useCallback(
    (delta: number) => {
      setLeftWidth(useUiStore.getState().leftWidth + delta)
    },
    [setLeftWidth],
  )

  const handleRightResize = useCallback(
    (delta: number) => {
      setRightWidth(useUiStore.getState().rightWidth - delta)
    },
    [setRightWidth],
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

      <div className="workspace__body">
        {leftCollapsed ? (
          <div className="panel-collapsed-rail">
            <button
              type="button"
              onClick={toggleLeftCollapsed}
              aria-label="Expand left panel"
              title="Expand navigation"
            >
              ›
            </button>
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
                aria-label="Expand right panel"
                title="Expand task context"
              >
                ‹
              </button>
            </div>
          ) : (
            <>
              <ResizeHandle onResizeDelta={handleRightResize} />
              <div className="workspace__panel workspace__panel--right" style={{ width: rightWidth }}>
                <RightPanel />
              </div>
            </>
          )
        ) : null}
      </div>
    </div>
  )
}
