import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'

import { searchMockMaterials } from '@/mock/materials.mock'
import { materialApi } from '@/services/api/materialApi'
import { useMaterialCatalogStore } from '@/store/materialCatalogStore'

import type { MaterialOptionDto } from '@/types/backend/materials'

import { ComposerInlineInput } from './ComposerInlineInput'

import './ComposerInlineInput.css'
import './ComposerInput.css'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'
const MIN_QUERY_LENGTH = 3
const SEARCH_DEBOUNCE_MS = 80

interface MaterialSearchInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (value?: string) => void
  disabled?: boolean
  submitting?: boolean
  placeholder?: string
  inline?: boolean
}

export function MaterialSearchInput({
  value,
  onChange,
  onSubmit,
  disabled,
  submitting,
  placeholder = 'Search materials (e.g. SA-106B, TP316L)…',
  inline = false,
}: MaterialSearchInputProps) {
  const [suggestions, setSuggestions] = useState<MaterialOptionDto[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const catalogReady = useMaterialCatalogStore((state) => state.ready)
  const catalogWarming = useMaterialCatalogStore((state) => state.warming)
  const catalogError = useMaterialCatalogStore((state) => state.error)
  const warmCatalog = useMaterialCatalogStore((state) => state.warmCatalog)

  const query = value.trim()
  const showSuggestions = query.length >= MIN_QUERY_LENGTH && suggestions.length > 0

  useEffect(() => {
    void warmCatalog()
  }, [warmCatalog])

  useEffect(() => {
    setHighlightIndex(-1)
  }, [suggestions])

  useEffect(() => {
    if (query.length < MIN_QUERY_LENGTH) {
      setSuggestions([])
      return
    }

    if (catalogError) {
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
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [catalogError, query])

  const canSubmit = useMemo(() => value.trim().length > 0, [value])

  const chooseSuggestion = (option: MaterialOptionDto) => {
    onChange(option.value)
    onSubmit(option.value)
    setSuggestions([])
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
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
      }
    }
  }

  const statusHint = catalogError
    ? catalogError
    : catalogWarming && !catalogReady
      ? 'Loading material catalog…'
      : null

  const suggestionsList = showSuggestions ? (
    <div className="composer-suggestions" role="listbox" aria-label="Material suggestions">
      {suggestions.map((option, index) => (
        <button
          key={`${option.standard}-${option.value}`}
          type="button"
          role="option"
          aria-label={option.value}
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
  ) : null

  if (inline) {
    return (
      <div className="material-search-input material-search-input--inline">
        {statusHint ? <p className="material-search-input__status">{statusHint}</p> : null}
        <ComposerInlineInput
          value={value}
          onChange={onChange}
          placeholder="Search…"
          disabled={disabled}
          submitting={submitting || loadingSuggestions}
          canSubmit={canSubmit}
          onSubmit={() => onSubmit()}
          inputMode="search"
          variant="text"
          onKeyDown={handleKeyDown}
        />
        {suggestionsList}
      </div>
    )
  }

  return (
    <div className="material-search-input">
      {statusHint ? <p className="material-search-input__status">{statusHint}</p> : null}
      {suggestionsList}
      <ComposerInlineInput
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        submitting={submitting || loadingSuggestions}
        canSubmit={canSubmit}
        onSubmit={() => onSubmit()}
        inputMode="search"
        variant="text"
        onKeyDown={handleKeyDown}
      />
    </div>
  )
}
