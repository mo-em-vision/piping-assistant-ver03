import { useEffect } from 'react'

import { useBackendConnection } from '@/hooks/useBackend'
import { useWorkspaceBootstrap } from '@/hooks/useWorkspaceBootstrap'
import { DevPanelTabsSync } from '@/components/layout/DevPanelTabsSync'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'

import './App.css'

function App() {
  const { backendStatus, isRetrying, retryConnection } = useBackendConnection()
  const { reload } = useWorkspaceBootstrap(backendStatus)

  // #region agent log
  useEffect(() => {
    fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
      body: JSON.stringify({
        sessionId: 'ed32ea',
        location: 'App.tsx:mount',
        message: 'App mounted',
        data: {
          backendStatus: backendStatus.status,
          electronApiPresent: typeof window.electronAPI !== 'undefined',
        },
        timestamp: Date.now(),
        hypothesisId: 'D',
      }),
    }).catch(() => {})
  }, [backendStatus.status])
  // #endregion

  return (
    <>
      <DevPanelTabsSync />
      <div className="app">
        <WorkspaceLayout
          backendStatus={backendStatus}
          isRetrying={isRetrying}
          onRetryBackend={() => {
            void retryConnection()
          }}
          onReloadWorkspace={reload}
        />
      </div>
    </>
  )
}

export default App
