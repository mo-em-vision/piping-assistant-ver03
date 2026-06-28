import { useCallback, useEffect, useRef, useState } from 'react'

import { ResizeHandle } from '@/components/layout/ResizeHandle'
import { standardsApi } from '@/services/api/standardsApi'
import type { StandardsBrowseNodeDto } from '@/types/backend/api'
import { RESIZE_HANDLE_WIDTH } from '@/utils/panelLayout'

import { StandardsBrowserExpandRail, StandardsBrowserSidebar } from './StandardsBrowserSidebar'
import { StandardsBrowserPreview } from './StandardsBrowserPreview'
import { isSelectableBrowseNode } from './standardsBrowseUtils'

import './StandardsBrowserTab.css'

const DEFAULT_STANDARD_LABEL = 'ASME B31.3'
const MIN_SIDEBAR_WIDTH = 136
const MAX_SIDEBAR_WIDTH = 480
const MIN_PREVIEW_WIDTH = 200
const DEFAULT_SIDEBAR_WIDTH = 280

export function StandardsBrowserTab() {
  const [tree, setTree] = useState<StandardsBrowseNodeDto[]>([])
  const [standardLabel, setStandardLabel] = useState(DEFAULT_STANDARD_LABEL)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [treeCollapsed, setTreeCollapsed] = useState(false)
  const [selection, setSelection] = useState<StandardsBrowseNodeDto | null>(null)
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH)
  const splitRef = useRef<HTMLDivElement>(null)

  const clampSidebarWidth = useCallback((width: number) => {
    const containerWidth = splitRef.current?.clientWidth ?? 0
    const maxByPreview =
      containerWidth > 0
        ? containerWidth - MIN_PREVIEW_WIDTH - RESIZE_HANDLE_WIDTH
        : MAX_SIDEBAR_WIDTH
    const maxWidth = Math.min(MAX_SIDEBAR_WIDTH, maxByPreview)
    return Math.min(maxWidth, Math.max(MIN_SIDEBAR_WIDTH, width))
  }, [])

  useEffect(() => {
    const split = splitRef.current
    if (!split || treeCollapsed) {
      return
    }

    const syncSidebarWidth = () => {
      setSidebarWidth((current) => clampSidebarWidth(current))
    }

    syncSidebarWidth()

    const observer = new ResizeObserver(syncSidebarWidth)
    observer.observe(split)

    return () => {
      observer.disconnect()
    }
  }, [clampSidebarWidth, treeCollapsed])

  const handleSidebarResize = useCallback(
    (delta: number) => {
      setSidebarWidth((current) => clampSidebarWidth(current + delta))
    },
    [clampSidebarWidth],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    void standardsApi
      .getBrowse()
      .then((payload) => {
        if (!cancelled) {
          setTree(payload.tree)
          setStandardLabel(payload.standard || DEFAULT_STANDARD_LABEL)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not load standards index.')
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
  }, [])

  const handleSelect = (node: StandardsBrowseNodeDto) => {
    if (!isSelectableBrowseNode(node)) {
      return
    }
    setSelection(node)
  }

  if (loading) {
    return <p className="standards-browser-tab__hint">Loading standards index…</p>
  }

  if (error) {
    return <p className="standards-browser-tab__error">{error}</p>
  }

  return (
    <div
      className={`standards-browser-tab${treeCollapsed ? ' standards-browser-tab--sidebar-collapsed' : ''}`}
    >
      <div ref={splitRef} className="standards-browser-tab__split">
        {treeCollapsed ? (
          <StandardsBrowserExpandRail onExpand={() => setTreeCollapsed(false)} />
        ) : (
          <>
            <div
              className="standards-browser-tab__sidebar-pane"
              style={{ width: sidebarWidth }}
            >
              <StandardsBrowserSidebar
                standardLabel={standardLabel}
                tree={tree}
                searchQuery={searchQuery}
                searchOpen={searchOpen}
                selectedId={selection?.id ?? null}
                onToggleSearch={() => setSearchOpen((open) => !open)}
                onSearchChange={setSearchQuery}
                onCollapse={() => setTreeCollapsed(true)}
                onSelect={handleSelect}
              />
            </div>
            <ResizeHandle onResizeDelta={handleSidebarResize} />
          </>
        )}
        <div className="standards-browser-tab__preview-pane">
          <StandardsBrowserPreview selection={selection} onSelect={handleSelect} />
        </div>
      </div>
    </div>
  )
}
