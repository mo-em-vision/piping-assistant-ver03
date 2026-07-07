import { useCallback, useEffect, useRef } from 'react'

import { useGraphStore } from '../store/graphStore'
import type { WorkflowExpansionView } from '../types'
import { withTaskQuery } from '../utils/taskQuery'

const POLL_INTERVAL_MS = 3000

export interface WorkflowExpansionOptions {
  taskId?: string | null
  sessionId?: string | null
  apiBaseUrl?: string
}

function normalizeApiBase(apiBaseUrl?: string): string {
  if (!apiBaseUrl) return ''
  return apiBaseUrl.replace(/\/$/, '')
}

function apiPath(path: string, options: WorkflowExpansionOptions): string {
  return `${normalizeApiBase(options.apiBaseUrl)}${path}`
}

export function useWorkflowExpansion(options: WorkflowExpansionOptions = {}) {
  const { taskId, sessionId, apiBaseUrl } = options
  const setExpansionView = useGraphStore((s) => s.setExpansionView)
  const setConnected = useGraphStore((s) => s.setConnected)
  const revision = useGraphStore((s) => s.expansionRevision)
  const autoRefresh = useGraphStore((s) => s.viewToggles.autoRefresh)
  const revisionRef = useRef(revision)
  revisionRef.current = revision

  const fetchExpansion = useCallback(async () => {
    try {
      const query = withTaskQuery({
        taskId,
        sessionId,
        params: revisionRef.current ? { revision: revisionRef.current } : {},
      })
      const response = await fetch(apiPath(`/api/workflow-expansion${query}`, { apiBaseUrl }))
      if (!response.ok) {
        setConnected(false)
        return
      }
      const data = (await response.json()) as WorkflowExpansionView & { unchanged?: boolean }
      if (data.unchanged) return
      setExpansionView(data)
      setConnected(true)
    } catch {
      setConnected(false)
    }
  }, [apiBaseUrl, sessionId, setConnected, setExpansionView, taskId])

  useEffect(() => {
    void fetchExpansion()
    if (!autoRefresh) return undefined
    const timer = window.setInterval(fetchExpansion, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [autoRefresh, fetchExpansion])

  return { refresh: fetchExpansion }
}
