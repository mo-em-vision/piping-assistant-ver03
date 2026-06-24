import { useCallback, useState } from 'react'

import { standardsApi } from '@/services/api/standardsApi'
import { useRightPanelStore, type StandardsReferenceKind } from '@/store/rightPanelStore'

import './StandardReferenceLink.css'

interface StandardReferenceLinkProps {
  referenceKind?: StandardsReferenceKind
  referenceId?: string
  nodeId?: string
  label: string
  hoverExcerpt?: string | null
}

export function StandardReferenceLink({
  referenceKind = 'node',
  referenceId,
  nodeId,
  label,
  hoverExcerpt,
}: StandardReferenceLinkProps) {
  const resolvedId = referenceId ?? nodeId ?? ''
  const openReferenceTab = useRightPanelStore((state) => state.openReferenceTab)
  const [excerpt, setExcerpt] = useState<string | null>(hoverExcerpt ?? null)
  const [isHovering, setIsHovering] = useState(false)
  const [loading, setLoading] = useState(false)

  const ensureExcerpt = useCallback(async () => {
    if (excerpt || loading || !resolvedId) {
      return
    }
    setLoading(true)
    try {
      const payload =
        referenceKind === 'table'
          ? await standardsApi.getTable(resolvedId)
          : await standardsApi.getNode(resolvedId)
      setExcerpt(payload.hover_excerpt || payload.title)
    } catch {
      setExcerpt('Reference text unavailable.')
    } finally {
      setLoading(false)
    }
  }, [excerpt, loading, referenceKind, resolvedId])

  return (
    <span
      className="standard-reference-link"
      onMouseEnter={() => {
        setIsHovering(true)
        void ensureExcerpt()
      }}
      onMouseLeave={() => {
        setIsHovering(false)
      }}
    >
      <button
        type="button"
        className="standard-reference-link__button"
        onClick={() => openReferenceTab(resolvedId, label, referenceKind)}
      >
        {label}
      </button>
      {isHovering && excerpt ? (
        <span className="standard-reference-link__tooltip">{excerpt}</span>
      ) : null}
    </span>
  )
}
