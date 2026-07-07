import { useBackendConnection } from '@/hooks/useBackend'
import { useWorkspaceBootstrap } from '@/hooks/useWorkspaceBootstrap'
import { DevModeElectronSync } from '@/components/layout/DevModeElectronSync'
import { DevPanelTabsSync } from '@/components/layout/DevPanelTabsSync'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'

import './App.css'

function App() {
  const { backendStatus, isRetrying, retryConnection } = useBackendConnection()
  const { reload } = useWorkspaceBootstrap(backendStatus)

  return (
    <>
      <DevModeElectronSync />
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
