import { appendFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'

let logDirectory: string | null = null

export function initAppLogger(userDataPath: string): string {
  logDirectory = path.join(userDataPath, 'logs')
  mkdirSync(logDirectory, { recursive: true })
  logAppEvent('info', 'Application logger initialized', logDirectory)
  return logDirectory
}

export function getLogDirectory(): string {
  if (!logDirectory) {
    throw new Error('Application logger has not been initialized')
  }
  return logDirectory
}

export function logAppEvent(level: string, message: string, detail?: string): void {
  if (!logDirectory) {
    return
  }

  const suffix = detail ? ` — ${detail}` : ''
  const line = `${new Date().toISOString()} [${level}] ${message}${suffix}\n`
  appendFileSync(path.join(logDirectory, 'desktop.log'), line, { encoding: 'utf8' })
}
