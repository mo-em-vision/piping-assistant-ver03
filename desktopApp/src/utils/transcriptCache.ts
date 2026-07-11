import type { DisplayOutputBlock } from '@/types/backend/outputs'

const STORAGE_KEY = 'ver03_workflow_transcript_v2'

type TranscriptCacheStore = Record<string, DisplayOutputBlock[]>

function readStore(): TranscriptCacheStore {
  if (typeof window === 'undefined' || !window.sessionStorage) {
    return {}
  }

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return {}
    }
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') {
      return {}
    }
    return parsed as TranscriptCacheStore
  } catch {
    return {}
  }
}

function writeStore(store: TranscriptCacheStore): void {
  if (typeof window === 'undefined' || !window.sessionStorage) {
    return
  }

  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    // Ignore quota or privacy-mode failures; in-memory merge still applies.
  }
}

/** Load cached workflow transcript blocks for a task (session-scoped). */
export function loadTranscriptCache(taskId: string): DisplayOutputBlock[] {
  if (!taskId) {
    return []
  }
  return readStore()[taskId] ?? []
}

/** Persist merged workflow transcript blocks for a task. */
export function saveTranscriptCache(taskId: string, blocks: DisplayOutputBlock[]): void {
  if (!taskId) {
    return
  }
  const store = readStore()
  store[taskId] = blocks
  writeStore(store)
}

/** Remove cached transcript for one task or clear the entire cache. */
export function clearTranscriptCache(taskId?: string): void {
  if (!taskId) {
    writeStore({})
    return
  }

  const store = readStore()
  delete store[taskId]
  writeStore(store)
}
