import { ReactFlowProvider, useReactFlow } from '@xyflow/react'
import { useCallback, useEffect, useState } from 'react'
import AnalysisPanel from './components/AnalysisPanel'
import FilterBar from './components/FilterBar'
import GraphCanvas from './components/GraphCanvas'
import SearchBar from './components/SearchBar'
import SidePanel from './components/SidePanel'
import Toolbar from './components/Toolbar'
import { fetchAnalysis, fetchNodeDetail, useGraphWebSocket } from './hooks/useGraphWebSocket'
import { useGraphStore } from './store/graphStore'
import type { NodeDetail } from './types'

function AppContent() {
  useGraphWebSocket()
  const connected = useGraphStore((s) => s.connected)
  const context = useGraphStore((s) => s.context)
  const nodeDetail = useGraphStore((s) => s.nodeDetail)
  const setSelectedNodeId = useGraphStore((s) => s.setSelectedNodeId)
  const setNodeDetail = useGraphStore((s) => s.setNodeDetail)
  const setAnalysis = useGraphStore((s) => s.setAnalysis)
  const analysis = useGraphStore((s) => s.analysis)
  const revision = useGraphStore((s) => s.revision)
  const { setCenter, getNode, fitView } = useReactFlow()
  const [fitViewTrigger, setFitViewTrigger] = useState(0)

  useEffect(() => {
    if (!revision) return
    fetchAnalysis().then((data) => {
      if (data) setAnalysis(data)
    })
  }, [revision, setAnalysis])

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
      const detail = (await fetchNodeDetail(nodeId)) as NodeDetail | null
      setNodeDetail(detail)
    },
    [focusNode, setNodeDetail, setSelectedNodeId],
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
        {context && (
          <div className="context-meta">
            Task: <strong>{context.task_id ?? 'none'}</strong>
            {' · '}
            Nodes: <strong>{context.node_count}</strong>
            {' · '}
            Edges: <strong>{context.edge_count}</strong>
          </div>
        )}
      </header>

      <aside className="sidebar">
        <SearchBar onFocusNode={selectNode} />
        <FilterBar />
        <AnalysisPanel analysis={analysis} onSelectNode={selectNode} />
      </aside>

      <main className="canvas-area">
        <Toolbar onFitView={handleFitView} />
        <GraphCanvas onSelectNode={selectNode} fitViewTrigger={fitViewTrigger} />
      </main>

      <SidePanel detail={nodeDetail} onSelectPeer={selectNode} />
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
