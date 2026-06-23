import { useEffect, useMemo, useState } from 'react'

import { materialApi } from '@/services/api/materialApi'
import { searchMockMaterials } from '@/mock/materials.mock'

import type { MaterialOptionDto } from '@/types/backend/materials'

import { ComposerInput } from './ComposerInput'

import './ComposerInput.css'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'
const MIN_QUERY_LENGTH = 3

interface MaterialSearchInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (value?: string) => void
  disabled?: boolean
  submitting?: boolean
  placeholder?: string
}

export function MaterialSearchInput({
  value,
  onChange,
  onSubmit,
  disabled,
  submitting,
  placeholder = 'Search ASTM materials (e.g. SA-106B)…',
}: MaterialSearchInputProps) {
  const [suggestions, setSuggestions] = useState<MaterialOptionDto[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)

  const query = value.trim()
  const showSuggestions = query.length >= MIN_QUERY_LENGTH && suggestions.length > 0

  useEffect(() => {
    setHighlightIndex(-1)
  }, [suggestions])

  useEffect(() => {
    if (query.length < MIN_QUERY_LENGTH) {
      setSuggestions([])
      return
    }

    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      const run = async () => {
        setLoadingSuggestions(true)
        try {
          if (useMockData) {
            setSuggestions(searchMockMaterials(query))
            return
          }

          const response = await materialApi.search(query)
          if (!controller.signal.aborted) {
            setSuggestions(response.materials)
          }
        } catch {
          if (!controller.signal.aborted) {
            setSuggestions(searchMockMaterials(query))
          }
        } finally {
          if (!controller.signal.aborted) {
            setLoadingSuggestions(false)
          }
        }
      }

      void run()
    }, 180)

    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [query])

  const canSubmit = useMemo(() => value.trim().length > 0, [value])

  const chooseSuggestion = (option: MaterialOptionDto) => {
    onChange(option.value)
    onSubmit(option.value)
    setSuggestions([])
  }

  return (
    <div className="material-search-input">
      {showSuggestions ? (
        <div className="composer-suggestions" role="listbox" aria-label="Material suggestions">
          {suggestions.map((option, index) => (
            <button
              key={`${option.standard}-${option.value}`}
              type="button"
              role="option"
              aria-selected={highlightIndex === index}
              className={`composer-suggestions__item${
                highlightIndex === index ? ' composer-suggestions__item--highlighted' : ''
              }`}
              disabled={disabled || submitting}
              onMouseEnter={() => setHighlightIndex(index)}
              onClick={() => chooseSuggestion(option)}
            >
              <span className="composer-suggestions__value">{option.value}</span>
              <span className="composer-suggestions__meta">
                {option.label} · {option.specification}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      <ComposerInput
        disabled={disabled}
        submitting={submitting || loadingSuggestions}
        canSubmit={canSubmit}
        placeholder={placeholder}
        onSubmit={() => onSubmit()}
      >
        <textarea
          className="composer-input__field"
          value={value}
          placeholder={placeholder}
          disabled={disabled || submitting}
          rows={1}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown' && suggestions.length > 0) {
              event.preventDefault()
              setHighlightIndex((current) => Math.min(current + 1, suggestions.length - 1))
              return
            }

            if (event.key === 'ArrowUp' && suggestions.length > 0) {
              event.preventDefault()
              setHighlightIndex((current) => Math.max(current - 1, 0))
              return
            }

            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              if (highlightIndex >= 0 && suggestions[highlightIndex]) {
                chooseSuggestion(suggestions[highlightIndex])
                return
              }
              if (canSubmit) {
                onSubmit()
              }
            }
          }}
        />
      </ComposerInput>
    </div>
  )
}
