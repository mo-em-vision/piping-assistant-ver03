export interface BackendDevFlags {
  enableDevInspection: boolean
  enableDevStudio: boolean
}

export const defaultBackendDevFlags: BackendDevFlags = {
  enableDevInspection: true,
  enableDevStudio: true,
}
