type RequestKey = string

export class RequestManager {
  private readonly inflight = new Map<RequestKey, Promise<unknown>>()

  async run<T>(key: RequestKey, task: () => Promise<T>): Promise<T> {
    const existing = this.inflight.get(key)
    if (existing) {
      return existing as Promise<T>
    }

    const promise = task().finally(() => {
      this.inflight.delete(key)
    })

    this.inflight.set(key, promise)
    return promise
  }

  clear(): void {
    this.inflight.clear()
  }
}

export const requestManager = new RequestManager()
