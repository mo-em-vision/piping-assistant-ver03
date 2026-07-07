import '@xyflow/react/dist/style.css'

import { ReactFlowProvider, useReactFlow } from '@xyflow/react'
import { useCallback, useEffect, useState } from 'react'

import ExpansionLegend from './components/ExpansionLegend'
import ExpansionSidePanel from './components/ExpansionSidePanel'
import ExpansionTimelinePanel from './components/ExpansionTimelinePanel'
import ExpansionToolbar from './components/ExpansionToolbar'
import FilterBar from './components/FilterBar'
import GraphCanvas from './components/GraphCanvas'
import PhaseBadge from './components/PhaseBadge'
import SearchBar from './components/SearchBar'
import { useWorkflowExpansion } from './hooks/useWorkflowExpansion'
import { useGraphStore } from './store/graphStore'

import './theme/embed-theme.css'

export interface EmbeddedGraphExplorerProps {
  taskId?: string | null
  sessionId?: string | null
  apiBaseUrl: string
  serverStatus?: string
  serverDetail?: string
  /** When set, focuses and selects this node on the canvas (e.g. from inspector trace). */
  focusNodeId?: string | null
}

function EmbeddedGraphExplorerContent({
  taskId,
  sessionId,
  apiBaseUrl,
  serverStatus,
  serverDetail,
  focusNodeId,
}: EmbeddedGraphExplorerProps) {
  const { refresh } = useWorkflowExpansion({ taskId, sessionId, apiBaseUrl })
  const connected = useGraphStore((s) => s.connected)
  const expansionView = useGraphStore((s) => s.expansionView)
  const selectedExpansionNode = useGraphStore((s) => s.selectedExpansionNode)
  const setSelectedExpansionNode = useGraphStore((s) => s.setSelectedExpansionNode)
  const setSelectedNodeId = useGraphStore((s) => s.setSelectedNodeId)
  const { setCenter, getNode, fitView } = useReactFlow()
  const [fitViewTrigger, setFitViewTrigger] = useState(0)

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
    (nodeId: string) => {
      setSelectedNodeId(nodeId)
      focusNode(nodeId)
      const node = expansionView?.nodes.find((item) => item.id === nodeId) ?? null
      setSelectedExpansionNode(node)
    },
    [expansionView?.nodes, focusNode, setSelectedExpansionNode, setSelectedNodeId],
  )

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.15, duration: 300 })
    setFitViewTrigger((value) => value + 1)
  }, [fitView])

  useEffect(() => {
    if (!focusNodeId) {
      return
    }
    selectNode(focusNodeId)
  }, [focusNodeId, selectNode])

  const statusLabel = connected
    ? 'Live'
    : serverStatus === 'error'
      ? 'Server unavailable'
      : serverStatus && serverStatus !== 'connected'
        ? `Server ${serverStatus}`
        : 'Connecting…'

  return (
    <div className="graph-explorer-embed">
      <div className="graph-explorer-embed__shell graph-explorer-embed__shell--with-panel">
        <header className="graph-explorer-embed__header">
          <span className={`status-dot ${connected ? 'connected' : ''}`} />
          <h1>Graph</h1>
          {expansionView ? (
            <>
              <PhaseBadge phase={expansionView.current_phase} taskStatus={expansionView.task_status} />
              <div className="context-meta">
                Task: <strong>{expansionView.task_id ?? 'none'}</strong>
              </div>
            </>
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
          {expansionView ? (
            <ExpansionTimelinePanel
              timeline={expansionView.timeline}
              currentPhase={expansionView.current_phase}
            />
          ) : null}
          <ExpansionLegend />
        </aside>

        <main className="graph-explorer-embed__canvas">
          <ExpansionToolbar onFitView={handleFitView} onRefresh={() => void refresh()} />
          <GraphCanvas onSelectNode={selectNode} fitViewTrigger={fitViewTrigger} colorMode="light" />
        </main>

        <ExpansionSidePanel node={selectedExpansionNode} />
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
