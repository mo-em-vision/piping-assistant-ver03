import { lazy, Suspense } from 'react'



import { constants } from '@/config/constants'

import { useGraphExplorerStatus } from '@/hooks/useGraphExplorerStatus'

import { getActiveSessionId } from '@/store/projectStore'



import './InspectorPanels.css'



const EmbeddedGraphExplorer = lazy(async () => {

  const module = await import('@graph-explorer/embed')

  return { default: module.EmbeddedGraphExplorer }

})



type InspectorGraphPanelProps = {

  activeTaskId: string | null

  sessionId: string | null

}



export function InspectorGraphPanel({ activeTaskId, sessionId }: InspectorGraphPanelProps) {

  const { status } = useGraphExplorerStatus()

  const resolvedSessionId = sessionId ?? getActiveSessionId() ?? null



  if (!activeTaskId) {

    return (

      <div className="inspector-graph">

        <p className="inspector-graph__hint">Open a task to explore its active subgraph.</p>

      </div>

    )

  }



  return (

    <div className="inspector-graph inspector-graph--embedded">

      <Suspense fallback={<p className="inspector-graph__hint">Loading graph explorer…</p>}>

        <EmbeddedGraphExplorer

          taskId={activeTaskId}

          sessionId={resolvedSessionId}

          apiBaseUrl={constants.graphExplorerUrl}

          serverStatus={status.status}

          serverDetail={status.detail}

        />

      </Suspense>

    </div>

  )

}

