import { developmentConfig } from './development'
import { productionConfig } from './production'

export const env = import.meta.env.DEV ? developmentConfig : productionConfig

/** @deprecated Use devToolsAvailable + devToolsStore.devModeActive */
export const devMode = env.devToolsAvailable

export type AppEnv = typeof env
