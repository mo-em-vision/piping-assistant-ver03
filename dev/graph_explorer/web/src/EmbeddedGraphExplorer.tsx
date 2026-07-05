import '@xyflow/react/dist/style.css'

import { ReactFlowProvider, useReactFlow } from '@xyflow/react'
import { useCallback, useEffect, useState } from 'react'

import AnalysisPanel from './components/AnalysisPanel'
import FilterBar from './components/FilterBar'
import GraphCanvas from './components/GraphCanvas'
import SearchBar from './components/SearchBar'
import Toolbar from './components/Toolbar'
import { fetchAnalysis, fetchNodeDetail, useGraphWebSocket } from './hooks/useGraphWebSocket'
import { useGraphStore } from './store/graphStore'
import type { NodeDetail } from './types'

import './theme/embed-theme.css'

export interface EmbeddedGraphExplorerProps {
  taskId?: string | null
  sessionId?: string | null
  apiBaseUrl: string
  serverStatus?: string
  serverDetail?: string
}

function EmbeddedGraphExplorerContent({
  taskId,
  sessionId,
  apiBaseUrl,
  serverStatus,
  serverDetail,
}: EmbeddedGraphExplorerProps) {
  useGraphWebSocket({ taskId, sessionId, apiBaseUrl })
  const connected = useGraphStore((s) => s.connected)
  const context = useGraphStore((s) => s.context)
  const setSelectedNodeId = useGraphStore((s) => s.setSelectedNodeId)
  const setNodeDetail = useGraphStore((s) => s.setNodeDetail)
  const setAnalysis = useGraphStore((s) => s.setAnalysis)
  const analysis = useGraphStore((s) => s.analysis)
  const revision = useGraphStore((s) => s.revision)
  const { setCenter, getNode, fitView } = useReactFlow()
  const [fitViewTrigger, setFitViewTrigger] = useState(0)

  useEffect(() => {
    if (!revision) return
    void fetchAnalysis({ taskId, sessionId, apiBaseUrl }).then((data) => {
      if (data) setAnalysis(data)
    })
  }, [apiBaseUrl, revision, sessionId, setAnalysis, taskId])

  const focusNode = useCallback(
    (nodeId: string) => {
      const flowNode = getNode(nodeId)
      if (flowNode) {
        setCenter(flowNode.position.x + 100, flowNode.position.y + 28, { zoom: 1.2, duration: 300 })
      }
    },
    [getNode, setCenter],
  )

  const selectNode = useCallback(
    async (nodeId: string) => {
      setSelectedNodeId(nodeId)
      focusNode(nodeId)
      const detail = (await fetchNodeDetail(nodeId, { taskId, sessionId, apiBaseUrl })) as NodeDetail | null
      setNodeDetail(detail)
    },
    [apiBaseUrl, focusNode, sessionId, setNodeDetail, setSelectedNodeId, taskId],
  )

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.15, duration: 300 })
    setFitViewTrigger((value) => value + 1)
  }, [fitView])

  const statusLabel = connected
    ? 'Live'
    : serverStatus === 'error'
      ? 'Server unavailable'
      : serverStatus && serverStatus !== 'connected'
        ? `Server ${serverStatus}`
        : 'Connecting…'

  return (
    <div className="graph-explorer-embed">
      <div className="graph-explorer-embed__shell">
        <header className="graph-explorer-embed__header">
          <span className={`status-dot ${connected ? 'connected' : ''}`} />
          <h1>Graph</h1>
          {context ? (
            <div className="context-meta">
              Task: <strong>{context.task_id ?? 'none'}</strong>
              {' · '}
              Nodes: <strong>{context.node_count}</strong>
            </div>
          ) : null}
          <span
            className={`graph-explorer-embed__status${!connected && serverStatus === 'error' ? ' graph-explorer-embed__status--error' : ''}`}
            title={!connected && serverDetail ? serverDetail : undefined}
          >
            {statusLabel}
          </span>
        </header>

        <aside className="graph-explorer-embed__sidebar">
          <SearchBar onFocusNode={selectNode} />
          <FilterBar />
          <AnalysisPanel analysis={analysis} onSelectNode={selectNode} />
        </aside>

        <main className="graph-explorer-embed__canvas">
          <Toolbar onFitView={handleFitView} />
          <GraphCanvas onSelectNode={selectNode} fitViewTrigger={fitViewTrigger} colorMode="light" />
        </main>
      </div>
    </div>
  )
}

export function EmbeddedGraphExplorer(props: EmbeddedGraphExplorerProps) {
  return (
    <ReactFlowProvider>
      <EmbeddedGraphExplorerContent {...props} />
    </ReactFlowProvider>
  )
}
