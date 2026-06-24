import { useEffect, useState } from 'react'

import { standardsApi } from '@/services/api/standardsApi'

import type { TableSourceDto } from '@/types/backend/api'

import './NodeReferenceTab.css'
import './TableReferenceTab.css'

interface TableReferenceTabProps {
  tableId: string
}

export function TableReferenceTab({ tableId }: TableReferenceTabProps) {
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
    <div className="node-reference-tab">
      <h3 className="table-reference-tab__title">{payload.title}</h3>
      {payload.source_path ? (
        <p className="table-reference-tab__meta">{payload.standard} · {payload.source_path}</p>
      ) : null}
      <table className="table-reference-tab__table">
        <thead>
          <tr>
            {payload.columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {payload.rows.map((row, index) => (
            <tr key={`${payload.table_id}-row-${index}`}>
              {payload.columns.map((column) => (
                <td key={column.key}>{String(row[column.key] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
