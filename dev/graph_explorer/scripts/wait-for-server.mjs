const host = process.env.GRAPH_EXPLORER_HOST ?? '127.0.0.1'
const port = Number(process.env.GRAPH_EXPLORER_PORT ?? '8765')
const healthUrl = `http://${host}:${port}/health`
const timeoutMs = Number(process.env.GRAPH_EXPLORER_WAIT_MS ?? '60000')
const intervalMs = Number(process.env.GRAPH_EXPLORER_WAIT_INTERVAL_MS ?? '200')

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

while (Date.now() - startedAt < timeoutMs) {
  if (await probe()) {
    const elapsedMs = Date.now() - startedAt
    console.log(`Graph explorer backend ready at ${healthUrl} (${elapsedMs}ms)`)
    process.exit(0)
  }
  await new Promise((resolveDelay) => setTimeout(resolveDelay, intervalMs))
}

console.error(`Timed out waiting for graph explorer backend at ${healthUrl}`)
process.exit(1)
