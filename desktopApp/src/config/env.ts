import { developmentConfig } from './development'
import { productionConfig } from './production'

export const env = import.meta.env.DEV ? developmentConfig : productionConfig

export type AppEnv = typeof env
