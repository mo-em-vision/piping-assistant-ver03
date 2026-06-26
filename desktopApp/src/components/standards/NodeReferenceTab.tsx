import { useEffect, useState } from 'react'

import { StandardsMarkdownViewer } from '@/components/standards/StandardsMarkdownViewer'
import { standardsApi } from '@/services/api/standardsApi'

import type { NodeSourceDto } from '@/types/backend/api'

import './NodeReferenceTab.css'

interface NodeReferenceTabProps {
  nodeId: string
  subsectionId?: string
}

function subsectionHeader(payload: NodeSourceDto): string | null {
  const parts: string[] = []
  const paragraph = payload.subsection_paragraph ?? payload.paragraph
  const subsectionTitle = payload.subsection_title?.trim()

  if (paragraph) {
    parts.push(`§${paragraph}`)
  }
  if (subsectionTitle) {
    parts.push(subsectionTitle)
  }
  if (parts.length === 0) {
    return null
  }
  return parts.join(' — ')
}

export function NodeReferenceTab({ nodeId, subsectionId }: NodeReferenceTabProps) {
  const [payload, setPayload] = useState<NodeSourceDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const request = subsectionId
      ? standardsApi.getNodeSubsection(nodeId, subsectionId)
      : standardsApi.getNode(nodeId)

    void request
      .then((data) => {
        if (!cancelled) {
          setPayload(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            subsectionId
              ? 'Could not load standards subsection text.'
              : 'Could not load standards reference text.',
          )
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
  }, [nodeId, subsectionId])

  if (loading) {
    return (
      <p className="node-reference-tab__hint">
        {subsectionId ? 'Loading subsection…' : 'Loading reference text…'}
      </p>
    )
  }

  if (error) {
    return <p className="node-reference-tab__error">{error}</p>
  }

  if (!payload) {
    return <p className="node-reference-tab__hint">No reference text available.</p>
  }

  const header = subsectionId ? subsectionHeader(payload) : null
  const body = payload.body.trim()
  const fallbackText = payload.subsection_title ?? payload.hover_excerpt

  return (
    <div className="node-reference-tab">
      {subsectionId ? (
        <header className="node-reference-tab__subsection-header">
          <p className="node-reference-tab__parent-title">{payload.title}</p>
          {header ? <h3 className="node-reference-tab__subsection-title">{header}</h3> : null}
        </header>
      ) : null}
      {body ? (
        <StandardsMarkdownViewer content={body} />
      ) : fallbackText ? (
        <p className="node-reference-tab__hint">{fallbackText}</p>
      ) : (
        <p className="node-reference-tab__hint">No subsection text available.</p>
      )}
    </div>
  )
}
