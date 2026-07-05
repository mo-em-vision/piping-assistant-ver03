import { constants } from './constants'

export const productionConfig = {
  backendUrl: import.meta.env.VITE_BACKEND_URL || constants.defaultBackendUrl,
  appName: import.meta.env.VITE_APP_NAME || constants.appName,
  devToolsAvailable: import.meta.env.VITE_ENABLE_DEV_TOOLS === 'true',
} as const
