import { backendClient } from './backendClient'
import { tracedRequest } from '@/services/performance/tracedRequest'
import { generateTraceId } from '@/services/performance/traceId'

import type {
  DevOperationsSnapshotDto,
  InspectionPayloadDto,
  PerformanceTracesSnapshotDto,
} from '@/types/backend/inspection'

function withSession(path: string, sessionId?: string): string {
  if (!sessionId) {
    return path
  }
  const separator = path.includes('?') ? '&' : '?'
  return `${path}${separator}session_id=${encodeURIComponent(sessionId)}`
}

export const inspectionApi = {
  get(taskId: string, sessionId?: string) {
    return backendClient.get<InspectionPayloadDto>(
      withSession(`/api/v1/tasks/${taskId}/inspection`, sessionId),
    )
  },

  getTraced(taskId: string, traceId: string, sessionId?: string) {
    return tracedRequest<InspectionPayloadDto>(
      withSession(`/api/v1/tasks/${taskId}/inspection`, sessionId),
      { method: 'GET' },
      { traceId, trigger: 'inspection_poll', taskId, preserveActiveTrace: true },
    )
  },

  createInspectionPollTraceId() {
    return generateTraceId()
  },

  setBreakpoint(
    taskId: string,
    payload: { paused?: boolean; step?: boolean },
    sessionId?: string,
  ) {
    return backendClient.post<{ paused: boolean; step_once: boolean; resume: boolean }>(
      withSession(`/api/v1/tasks/${taskId}/inspection/breakpoint`, sessionId),
      payload,
    )
  },

  runIntegrity(taskId: string, sessionId?: string) {
    return backendClient.get<{
      checks: Array<{ check_id: string; name: string; passed: boolean; message: string }>
    }>(withSession(`/api/v1/tasks/${taskId}/inspection/integrity`, sessionId))
  },

  getOperations() {
    return backendClient.get<DevOperationsSnapshotDto>('/api/v1/dev/operations')
  },

  getPerformanceTraces(limit = 40) {
    return backendClient.get<PerformanceTracesSnapshotDto>(
      `/api/v1/dev/performance/traces?limit=${encodeURIComponent(String(limit))}`,
    )
  },
}
