import { env } from '@/config/env'
import { ApiError } from '@/types/backend/apiError'
import type { ApiErrorBody } from '@/types/backend/api'

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  timeoutMs?: number
}

export class BackendClient {
  constructor(private readonly baseUrl: string = env.backendUrl) {}

  getBaseUrl(): string {
    return this.baseUrl.replace(/\/$/, '')
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { body, timeoutMs = 15_000, headers, ...init } = options
    const url = `${this.getBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`

    const response = await fetch(url, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    })

    const payload = await this.parseJson(response)

    if (!response.ok) {
      const errorBody = extractErrorBody(payload)
      throw new ApiError(response.status, errorBody)
    }

    return payload as T
  }

  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body })
  }

  async patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PATCH', body })
  }

  async delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' })
  }

  private async parseJson(response: Response): Promise<unknown> {
    const text = await response.text()
    if (!text) {
      return {}
    }
    try {
      return JSON.parse(text) as unknown
    } catch {
      throw new ApiError(response.status, {
        code: 'invalid_response',
        message: 'Backend returned non-JSON response.',
      })
    }
  }
}

function extractErrorBody(payload: unknown): ApiErrorBody {
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const error = (payload as { error: ApiErrorBody }).error
    if (error?.code && error?.message) {
      return error
    }
  }
  return {
    code: 'unknown_error',
    message: 'Request failed.',
  }
}

export const backendClient = new BackendClient()
