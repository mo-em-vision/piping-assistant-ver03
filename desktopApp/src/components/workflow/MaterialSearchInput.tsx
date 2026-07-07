import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'

import { searchMockMaterials } from '@/mock/materials.mock'
import { materialApi } from '@/services/api/materialApi'
import { useMaterialCatalogStore } from '@/store/materialCatalogStore'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useUiStore } from '@/store/uiStore'

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
  onSubmit: (value?: string, displayValue?: string) => void
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
  const [selectedOption, setSelectedOption] = useState<MaterialOptionDto | null>(null)
  const catalogReady = useMaterialCatalogStore((state) => state.ready)
  const catalogWarming = useMaterialCatalogStore((state) => state.warming)
  const catalogError = useMaterialCatalogStore((state) => state.error)
  const warmCatalog = useMaterialCatalogStore((state) => state.warmCatalog)
  const markCatalogReady = useMaterialCatalogStore((state) => state.markCatalogReady)
  const openMaterialTab = useRightPanelStore((state) => state.openMaterialTab)

  const query = value.trim()
  const showSuggestions = query.length >= MIN_QUERY_LENGTH && suggestions.length > 0
  const showNoMatches =
    query.length >= MIN_QUERY_LENGTH && !loadingSuggestions && suggestions.length === 0

  useEffect(() => {
    void warmCatalog()
  }, [warmCatalog])

  useEffect(() => {
    setHighlightIndex(-1)
    setSelectedOption(null)
  }, [suggestions])

  useEffect(() => {
    if (selectedOption === null) {
      return
    }
    const matchesValue =
      query === selectedOption.value.trim() || query === selectedOption.label.trim()
    if (!matchesValue) {
      setSelectedOption(null)
    }
  }, [query, selectedOption])

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
            const materials = response.materials ?? []
            setSuggestions(materials)
            if (materials.length > 0) {
              markCatalogReady()
            }
          }
        } catch {
          if (!controller.signal.aborted) {
            const mockResults = searchMockMaterials(query)
            setSuggestions(mockResults)
            if (mockResults.length > 0) {
              markCatalogReady()
            }
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
  }, [markCatalogReady, query])

  const canSubmit = useMemo(() => selectedOption !== null, [selectedOption])

  const handleValueChange = (nextValue: string) => {
    if (
      selectedOption !== null &&
      nextValue.trim() !== selectedOption.value.trim() &&
      nextValue.trim() !== selectedOption.label.trim()
    ) {
      setSelectedOption(null)
    }
    onChange(nextValue)
  }

  const chooseSuggestion = (option: MaterialOptionDto) => {
    setSelectedOption(option)
    onChange(option.value)
    onSubmit(option.value, option.label)
    setSuggestions([])
  }

  const openMaterialInfo = (option: MaterialOptionDto) => {
    useUiStore.setState({ rightCollapsed: false })
    openMaterialTab(option.value, option.label)
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
        return
      }
      if (suggestions.length === 1) {
        chooseSuggestion(suggestions[0])
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
        <div
          key={`${option.standard}-${option.value}`}
          className={`composer-suggestions__item${
            highlightIndex === index ? ' composer-suggestions__item--highlighted' : ''
          }`}
          onMouseEnter={() => setHighlightIndex(index)}
        >
          <button
            type="button"
            role="option"
            aria-label={option.label}
            aria-selected={highlightIndex === index}
            className="composer-suggestions__select"
            disabled={disabled || submitting}
            onClick={() => chooseSuggestion(option)}
          >
            <span className="composer-suggestions__body">
              <span className="composer-suggestions__value">{option.label}</span>
              <span className="composer-suggestions__meta">{option.specification}</span>
            </span>
          </button>
          <button
            type="button"
            className="composer-suggestions__info"
            disabled={disabled || submitting}
            aria-label={`View details for ${option.label}`}
            onClick={(event) => {
              event.stopPropagation()
              openMaterialInfo(option)
            }}
          >
            ?
          </button>
        </div>
      ))}
    </div>
  ) : null

  const inputHint =
    query.length > 0 && query.length < MIN_QUERY_LENGTH
      ? 'Type at least 3 characters to search materials.'
      : showNoMatches
        ? 'No matching materials. Try a different grade or specification.'
        : query.length >= MIN_QUERY_LENGTH && suggestions.length > 0 && selectedOption === null
          ? 'Select a material from the list.'
          : null

  const input = (
    <ComposerInlineInput
      value={value}
      onChange={handleValueChange}
      placeholder={inline ? 'Search…' : placeholder}
      disabled={disabled}
      submitting={submitting || loadingSuggestions}
      canSubmit={canSubmit}
      onSubmit={() => onSubmit()}
      inputMode="search"
      variant="text"
      layout={inline ? 'compact' : 'fluid'}
      onKeyDown={handleKeyDown}
    />
  )

  return (
    <div className={`material-search-input${inline ? ' material-search-input--inline' : ''}`}>
      {statusHint ? <p className="material-search-input__status">{statusHint}</p> : null}
      <div className="material-search-input__anchor">
        {suggestionsList}
        {input}
      </div>
      {inputHint ? <p className="material-search-input__status">{inputHint}</p> : null}
    </div>
  )
}
