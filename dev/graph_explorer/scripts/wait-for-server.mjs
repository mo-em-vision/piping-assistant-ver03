import { appendFileSync } from 'node:fs'
import { resolve } from 'node:path'

const host = process.env.GRAPH_EXPLORER_HOST ?? '127.0.0.1'
const port = Number(process.env.GRAPH_EXPLORER_PORT ?? '8765')
const healthUrl = `http://${host}:${port}/health`
const timeoutMs = Number(process.env.GRAPH_EXPLORER_WAIT_MS ?? '60000')
const intervalMs = Number(process.env.GRAPH_EXPLORER_WAIT_INTERVAL_MS ?? '200')
const repoRoot = resolve(import.meta.dirname, '../../..')
const logPath = resolve(repoRoot, 'debug-fd176a.log')

function debugLog(hypothesisId, message, data) {
  // #region agent log
  try {
    appendFileSync(
      logPath,
      `${JSON.stringify({
        sessionId: 'fd176a',
        hypothesisId,
        location: 'wait-for-server.mjs',
        message,
        data,
        timestamp: Date.now(),
        runId: process.env.DEBUG_RUN_ID ?? 'post-fix',
      })}\n`,
    )
  } catch {
    // ignore
  }
  // #endregion
}

async function probe() {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 1500)
  try {
    const response = await fetch(healthUrl, { signal: controller.signal })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

const startedAt = Date.now()
debugLog('K', 'waiting for graph explorer backend', { healthUrl, timeoutMs, intervalMs })

while (Date.now() - startedAt < timeoutMs) {
  if (await probe()) {
    const elapsedMs = Date.now() - startedAt
    debugLog('K', 'backend ready', { healthUrl, elapsedMs })
    console.log(`Graph explorer backend ready at ${healthUrl} (${elapsedMs}ms)`)
    process.exit(0)
  }
  await new Promise((resolveDelay) => setTimeout(resolveDelay, intervalMs))
}

debugLog('K', 'backend wait timed out', { healthUrl, timeoutMs })
console.error(`Timed out waiting for graph explorer backend at ${healthUrl}`)
process.exit(1)
