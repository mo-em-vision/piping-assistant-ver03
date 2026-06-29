import { describe, expect, it } from 'vitest'

import { useDebouncedValue } from '@/dev-studio/hooks/useDebouncedSearch'
import { renderHook, waitFor } from '@testing-library/react'

describe('useDebouncedValue', () => {
  it('debounces value updates', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebouncedValue(value, delay),
      { initialProps: { value: 'a', delay: 100 } },
    )
    expect(result.current).toBe('a')
    rerender({ value: 'ab', delay: 100 })
    expect(result.current).toBe('a')
    await waitFor(() => expect(result.current).toBe('ab'), { timeout: 500 })
  })
})
