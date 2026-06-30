import { app } from 'electron'
import path from 'node:path'

import { constants } from '../../src/config/constants'
import { BackendProcessService } from './backendProcess'

function resolveBackendUrl(): string {
  return process.env.VITE_BACKEND_URL ?? constants.defaultBackendUrl
}

export function resolveRepoRoot(): string {
  if (app.isPackaged) {
    return path.resolve(process.resourcesPath, 'backend')
  }

  return path.resolve(app.getAppPath(), '..')
}

export async function runStartup(
  onStatusChange: (payload: ReturnType<BackendProcessService['getStatus']>) => void,
): Promise<BackendProcessService> {
  const backendService = new BackendProcessService(
    resolveRepoRoot(),
    resolveBackendUrl(),
    app.getPath('userData'),
    !app.isPackaged,
  )

  backendService.onStatusChange(onStatusChange)

  await backendService.start()

  return backendService
}
