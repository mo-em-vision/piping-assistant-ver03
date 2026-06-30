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
      // #region agent log
      fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b5dce6'},body:JSON.stringify({sessionId:'b5dce6',location:'useGraphWebSocket.ts:pollSnapshot',message:'snapshot fetch',data:{ok:response.ok,status:response.status},timestamp:Date.now(),hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      if (!response.ok) return
      const data = await response.json()
      // #region agent log
      fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b5dce6'},body:JSON.stringify({sessionId:'b5dce6',location:'useGraphWebSocket.ts:pollSnapshot',message:'snapshot data',data:{nodeCount:data?.context?.node_count,taskId:data?.context?.task_id,message:data?.context?.message},timestamp:Date.now(),hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      if (data.unchanged) return
      setSnapshot(data.nodes, data.edges, data.context, data.revision)
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b5dce6'},body:JSON.stringify({sessionId:'b5dce6',location:'useGraphWebSocket.ts:pollSnapshot',message:'snapshot fetch failed',data:{error:String(error)},timestamp:Date.now(),hypothesisId:'C'})}).catch(()=>{});
      // #endregion
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
