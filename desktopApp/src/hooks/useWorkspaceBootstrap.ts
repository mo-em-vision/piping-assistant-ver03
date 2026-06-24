import { useEffect } from 'react'

import type { BackendStatusPayload } from '@/config/constants'
import { materialApi } from '@/services/api/materialApi'
import { useConnectionStore } from '@/store/connectionStore'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

export function useWorkspaceBootstrap(backendStatus: BackendStatusPayload) {
  const checkApiConnection = useConnectionStore((state) => state.checkApiConnection)
  const apiStatus = useConnectionStore((state) => state.apiStatus)
  const loadProjects = useProjectStore((state) => state.loadProjects)
  const loadWorkspace = useTaskStore((state) => state.loadWorkspace)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)

  useEffect(() => {
    if (backendStatus.status !== 'connected') {
      return
    }

    void checkApiConnection().then((ok) => {
      if (ok) {
        void materialApi.warm().catch(() => undefined)
        void loadProjects().then(() => {
          void loadWorkspace()
          void loadMessages()
        })
      }
    })
  }, [backendStatus.status, checkApiConnection, loadMessages, loadProjects, loadWorkspace])

  return {
    apiStatus,
    loading,
    userError,
    reload: () => {
      void checkApiConnection().then((ok) => {
        if (ok) {
          void loadProjects().then(() => {
            void loadWorkspace()
            void loadMessages()
          })
        }
      })
    },
  }
}
