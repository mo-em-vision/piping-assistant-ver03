import { execSync } from 'node:child_process'

const ports = (process.argv[2] || '3000,8765').split(',').map((p) => Number(p.trim()))

function listListeningPidsWindows(targetPort) {
  try {
    const output = execSync(`netstat -ano | findstr :${targetPort}`, { encoding: 'utf8' })
    const pids = new Set()
    for (const line of output.split('\n')) {
      if (!line.includes('LISTENING')) continue
      const localAddress = line.trim().split(/\s+/)[1] || ''
      if (!localAddress.endsWith(`:${targetPort}`)) continue
      const parts = line.trim().split(/\s+/)
      const pid = Number(parts[parts.length - 1])
      if (pid > 0) pids.add(pid)
    }
    return [...pids]
  } catch {
    return []
  }
}

function killPidWindows(pid) {
  if (pid === process.pid) return false
  try {
    execSync(`taskkill /PID ${pid} /T /F`, { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

function portIsFreeWindows(targetPort) {
  return listListeningPidsWindows(targetPort).length === 0
}

function freePortWindows(targetPort) {
  const pids = listListeningPidsWindows(targetPort)

  if (pids.length === 0) {
    return
  }

  for (const pid of pids) {
    const killed = killPidWindows(pid)
    if (killed) {
      console.log(`Freed port ${targetPort} (stopped PID ${pid})`)
    }
  }

  for (let attempt = 0; attempt < 5; attempt += 1) {
    if (portIsFreeWindows(targetPort)) {
      return
    }
    execSync('powershell -NoProfile -Command "Start-Sleep -Milliseconds 200"', { stdio: 'ignore' })
  }

  const remaining = listListeningPidsWindows(targetPort)
  if (remaining.length > 0) {
    console.error(
      `Port ${targetPort} is still in use (PID ${remaining.join(', ')}). ` +
        'Close the other process or run: taskkill /PID <pid> /T /F',
    )
    process.exit(1)
  }
}

for (const port of ports) {
  if (process.platform === 'win32') {
    freePortWindows(port)
  } else {
    try {
      execSync(`lsof -ti :${port} | xargs kill -9`, { stdio: 'ignore', shell: true })
    } catch {
      // port free
    }
  }
}
