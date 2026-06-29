import { useCallback, useEffect, useRef } from 'react'
import { useGraphStore } from '../store/graphStore'
import type { GraphSnapshot, WebSocketMessage } from '../types'

const POLL_INTERVAL_MS = 3000

function wsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/graph`
}

export function useGraphWebSocket() {
  const setSnapshot = useGraphStore((s) => s.setSnapshot)
  const applyDelta = useGraphStore((s) => s.applyDelta)
  const setConnected = useGraphStore((s) => s.setConnected)
  const revision = useGraphStore((s) => s.revision)
  const revisionRef = useRef(revision)
  revisionRef.current = revision

  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      if (message.type === 'delta') {
        applyDelta(message)
        return
      }
      const snapshot = message as GraphSnapshot & { type: 'snapshot' }
      setSnapshot(snapshot.nodes, snapshot.edges, snapshot.context, snapshot.revision)
    },
    [applyDelta, setSnapshot],
  )

  const pollSnapshot = useCallback(async () => {
    try {
      const query = revisionRef.current ? `?revision=${encodeURIComponent(revisionRef.current)}` : ''
      const response = await fetch(`/api/graph/snapshot${query}`)
      if (!response.ok) return
      const data = await response.json()
      if (data.unchanged) return
      setSnapshot(data.nodes, data.edges, data.context, data.revision)
    } catch {
      setConnected(false)
    }
  }, [setConnected, setSnapshot])

  useEffect(() => {
    let ws: WebSocket | null = null
    let pollTimer: number | null = null
    let closed = false

    const connect = () => {
      ws = new WebSocket(wsUrl())

      ws.onopen = () => {
        setConnected(true)
        if (pollTimer !== null) {
          window.clearInterval(pollTimer)
          pollTimer = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          handleMessage(message)
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!closed && pollTimer === null) {
          pollTimer = window.setInterval(pollSnapshot, POLL_INTERVAL_MS)
        }
        if (!closed) {
          window.setTimeout(connect, 2000)
        }
      }

      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()
    pollSnapshot()

    return () => {
      closed = true
      if (pollTimer !== null) window.clearInterval(pollTimer)
      ws?.close()
    }
  }, [handleMessage, pollSnapshot, setConnected])
}

export async function fetchNodeDetail(nodeId: string) {
  const response = await fetch(`/api/graph/nodes/${encodeURIComponent(nodeId)}`)
  if (!response.ok) return null
  return response.json()
}

export async function fetchAnalysis() {
  const response = await fetch('/api/graph/analysis')
  if (!response.ok) return null
  return response.json()
}

export async function fetchContext() {
  const response = await fetch('/api/graph/context')
  if (!response.ok) return null
  return response.json()
}
