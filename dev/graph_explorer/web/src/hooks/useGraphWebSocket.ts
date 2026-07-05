import { useCallback, useEffect, useRef } from 'react'

import { useGraphStore } from '../store/graphStore'

import type { GraphSnapshot, WebSocketMessage } from '../types'

import { withTaskQuery } from '../utils/taskQuery'



const POLL_INTERVAL_MS = 3000



export interface GraphConnectionOptions {

  taskId?: string | null

  sessionId?: string | null

  apiBaseUrl?: string

}



function normalizeApiBase(apiBaseUrl?: string): string {

  if (!apiBaseUrl) {

    return ''

  }

  return apiBaseUrl.replace(/\/$/, '')

}



function wsUrl(options: GraphConnectionOptions): string {

  if (options.apiBaseUrl) {

    const base = new URL(options.apiBaseUrl)

    const protocol = base.protocol === 'https:' ? 'wss' : 'ws'

    const port = base.port ? `:${base.port}` : ''

    return `${protocol}://${base.hostname}${port}/ws/graph${withTaskQuery({

      taskId: options.taskId,

      sessionId: options.sessionId,

    })}`

  }



  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'

  return `${protocol}://${window.location.host}/ws/graph${withTaskQuery({

    taskId: options.taskId,

    sessionId: options.sessionId,

  })}`

}



function apiPath(path: string, options: GraphConnectionOptions): string {

  const base = normalizeApiBase(options.apiBaseUrl)

  return `${base}${path}`

}



export function useGraphWebSocket(options: GraphConnectionOptions = {}) {

  const { taskId, sessionId, apiBaseUrl } = options

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

      const revision = revisionRef.current

      const query = withTaskQuery({

        taskId,

        sessionId,

        params: revision ? { revision } : {},

      })

      const response = await fetch(apiPath(`/api/graph/snapshot${query}`, { apiBaseUrl }))

      if (!response.ok) return

      const data = await response.json()

      if (data.unchanged) return

      setSnapshot(data.nodes, data.edges, data.context, data.revision)

    } catch {

      setConnected(false)

    }

  }, [apiBaseUrl, sessionId, setConnected, setSnapshot, taskId])



  useEffect(() => {

    let ws: WebSocket | null = null

    let pollTimer: number | null = null

    let closed = false



    const connect = () => {

      ws = new WebSocket(wsUrl({ taskId, sessionId, apiBaseUrl }))



      ws.onopen = () => {

        setConnected(true)

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

        if (!closed) {

          window.setTimeout(connect, 2000)

        }

      }



      ws.onerror = () => {

        ws?.close()

      }

    }



    connect()

    void pollSnapshot()

    pollTimer = window.setInterval(pollSnapshot, POLL_INTERVAL_MS)



    return () => {

      closed = true

      if (pollTimer !== null) window.clearInterval(pollTimer)

      ws?.close()

    }

  }, [apiBaseUrl, handleMessage, pollSnapshot, sessionId, setConnected, taskId])

}



export async function fetchNodeDetail(nodeId: string, options: GraphConnectionOptions = {}) {

  const response = await fetch(

    apiPath(

      `/api/graph/nodes/${encodeURIComponent(nodeId)}${withTaskQuery({

        taskId: options.taskId,

        sessionId: options.sessionId,

      })}`,

      options,

    ),

  )

  if (!response.ok) return null

  return response.json()

}



export async function fetchAnalysis(options: GraphConnectionOptions = {}) {

  const response = await fetch(

    apiPath(

      `/api/graph/analysis${withTaskQuery({

        taskId: options.taskId,

        sessionId: options.sessionId,

      })}`,

      options,

    ),

  )

  if (!response.ok) return null

  return response.json()

}

