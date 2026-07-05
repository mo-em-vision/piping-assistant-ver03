import { constants } from './constants'

export const developmentConfig = {
  backendUrl: import.meta.env.VITE_BACKEND_URL || constants.defaultBackendUrl,
  appName: import.meta.env.VITE_APP_NAME || constants.appName,
  devToolsAvailable: true,
} as const
