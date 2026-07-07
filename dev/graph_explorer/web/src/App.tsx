import { ReactFlowProvider, useReactFlow } from '@xyflow/react'
import { useCallback, useState } from 'react'
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
import { readTaskIdFromUrl } from './utils/taskQuery'

function AppContent() {
  const taskId = readTaskIdFromUrl()
  const { refresh } = useWorkflowExpansion({ taskId })
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

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className={`status-dot ${connected ? 'connected' : ''}`} />
        <h1>Developer Graph Explorer</h1>
        {expansionView && (
          <>
            <PhaseBadge phase={expansionView.current_phase} taskStatus={expansionView.task_status} />
            <div className="context-meta">
              Task: <strong>{expansionView.task_id ?? 'none'}</strong>
              {' · '}
              Workflow: <strong>{expansionView.workflow || 'unknown'}</strong>
              {' · '}
              Nodes: <strong>{expansionView.nodes.filter((node) => node.visible).length}</strong>
            </div>
          </>
        )}
      </header>

      <aside className="sidebar">
        <SearchBar onFocusNode={selectNode} />
        <FilterBar />
        {expansionView && (
          <ExpansionTimelinePanel
            timeline={expansionView.timeline}
            currentPhase={expansionView.current_phase}
          />
        )}
        <ExpansionLegend />
      </aside>

      <main className="canvas-area">
        <ExpansionToolbar onFitView={handleFitView} onRefresh={() => void refresh()} />
        <GraphCanvas onSelectNode={selectNode} fitViewTrigger={fitViewTrigger} />
      </main>

      <ExpansionSidePanel node={selectedExpansionNode} />
    </div>
  )
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppContent />
    </ReactFlowProvider>
  )
}
