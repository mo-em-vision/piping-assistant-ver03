import { useBackendConnection } from '@/hooks/useBackend'
import { useWorkspaceBootstrap } from '@/hooks/useWorkspaceBootstrap'
import { DevNodeHoverProvider } from '@dev-ui/DevNodeHoverProvider'
import { DevModeElectronSync } from '@/components/layout/DevModeElectronSync'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'

import './App.css'

function App() {
  const { backendStatus, isRetrying, retryConnection } = useBackendConnection()
  const { reload } = useWorkspaceBootstrap(backendStatus)

  return (
    <DevNodeHoverProvider>
      <DevModeElectronSync />
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
    </DevNodeHoverProvider>
  )
}

export default App
