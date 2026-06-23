import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import { getLogDirectory, initAppLogger, logAppEvent } from '../../electron/services/appLogger'

describe('appLogger', () => {
  let userDataPath = ''

  afterEach(() => {
    if (userDataPath) {
      rmSync(userDataPath, { recursive: true, force: true })
      userDataPath = ''
    }
  })

  it('writes events to desktop.log under userData/logs', () => {
    userDataPath = mkdtempSync(join(tmpdir(), 'desktop-logs-'))
    const logDir = initAppLogger(userDataPath)
    logAppEvent('info', 'Test event', 'details')

    const logFile = join(logDir, 'desktop.log')
    const contents = readFileSync(logFile, 'utf8')
    expect(contents).toContain('[info] Test event — details')
    expect(getLogDirectory()).toBe(logDir)
  })
})
