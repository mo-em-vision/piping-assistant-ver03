import { useEffect, useState } from 'react'

import { StandardsTableViewer } from '@/components/standards/StandardsTableViewer'
import { standardsApi } from '@/services/api/standardsApi'
import type { TableViewerContext } from '@/store/rightPanelStore'

import type { TableSourceDto } from '@/types/backend/api'

import './NodeReferenceTab.css'

interface TableReferenceTabProps {
  tableId: string
  viewerContext?: TableViewerContext
}

export function TableReferenceTab({ tableId, viewerContext }: TableReferenceTabProps) {
  const [payload, setPayload] = useState<TableSourceDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    void standardsApi
      .getTable(tableId)
      .then((data) => {
        if (!cancelled) {
          setPayload(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not load standards table.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [tableId])

  if (loading) {
    return <p className="node-reference-tab__hint">Loading table…</p>
  }

  if (error) {
    return <p className="node-reference-tab__error">{error}</p>
  }

  if (!payload) {
    return <p className="node-reference-tab__hint">No table data available.</p>
  }

  return (
    <div className="node-reference-tab node-reference-tab--table-viewer">
      <StandardsTableViewer payload={payload} viewerContext={viewerContext} />
    </div>
  )
}
