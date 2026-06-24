import { useEffect, useState } from 'react'

import { StandardsMarkdownViewer } from '@/components/standards/StandardsMarkdownViewer'
import { standardsApi } from '@/services/api/standardsApi'

import type { NodeSourceDto } from '@/types/backend/api'

import './NodeReferenceTab.css'

interface NodeReferenceTabProps {
  nodeId: string
}

export function NodeReferenceTab({ nodeId }: NodeReferenceTabProps) {
  const [payload, setPayload] = useState<NodeSourceDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    void standardsApi
      .getNode(nodeId)
      .then((data) => {
        if (!cancelled) {
          setPayload(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not load standards reference text.')
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
  }, [nodeId])

  if (loading) {
    return <p className="node-reference-tab__hint">Loading reference text…</p>
  }

  if (error) {
    return <p className="node-reference-tab__error">{error}</p>
  }

  if (!payload) {
    return <p className="node-reference-tab__hint">No reference text available.</p>
  }

  return (
    <div className="node-reference-tab">
      <StandardsMarkdownViewer content={payload.body} />
    </div>
  )
}
