import { constants } from './constants'

export const productionConfig = {
  backendUrl: import.meta.env.VITE_BACKEND_URL || constants.defaultBackendUrl,
  appName: import.meta.env.VITE_APP_NAME || constants.appName,
  devMode: false,
} as const
