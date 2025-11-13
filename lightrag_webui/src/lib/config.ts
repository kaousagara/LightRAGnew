export const API_CONFIG = {
  baseURL: import.meta.env.VITE_BACKEND_URL || '',
  webuiPrefix: import.meta.env.VITE_WEBUI_PREFIX || '',
  timeout: 30000,
  retryAttempts: 1,
} as const

export const GRAPH_CONFIG = {
  defaultLayout: 'forceAtlas2' as const,
  maxNodes: 10000,
  animationDuration: 300,
  workerEnabled: true,
} as const

export const RAG_CONFIG = {
  streamingEnabled: true,
  defaultMode: 'hybrid' as const,
  maxTokens: 4096,
  temperature: 0.7,
} as const

export const UI_CONFIG = {
  defaultPageSize: 20,
  debounceDelay: 300,
  toastDuration: 3000,
} as const

export type QueryMode = 'local' | 'global' | 'hybrid' | 'naive' | 'mix'
export type AccreditationLevel = number
export type ServiceType = 'DOCT' | 'DRI' | 'DT' | 'DREC' | 'DAF' | 'CABINET' | 'DAP' | ''

export const SERVICE_OPTIONS: ServiceType[] = ['', 'DOCT', 'DRI', 'DT', 'DREC', 'DAF', 'CABINET', 'DAP']
