import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, vi } from 'vitest'

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  HTMLDialogElement.prototype.showModal = vi.fn()
  HTMLDialogElement.prototype.close = vi.fn()
  class ResizeObserverMock {
    observe() {}
    disconnect() {}
    unobserve() {}
  }
  vi.stubGlobal('ResizeObserver', ResizeObserverMock)
})

afterEach(() => {
  cleanup()
})
