import { useBackendConnection } from '@/hooks/useBackend'
import { useWorkspaceBootstrap } from '@/hooks/useWorkspaceBootstrap'
import { DevNodeHoverProvider } from '@/components/dev/DevNodeHoverProvider'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'

import './App.css'

function App() {
  const { backendStatus, isRetrying, retryConnection } = useBackendConnection()
  const { reload } = useWorkspaceBootstrap(backendStatus)

  return (
    <DevNodeHoverProvider>
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
