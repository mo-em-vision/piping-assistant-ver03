import { useEffect, useMemo, useRef, useState } from 'react'

import { StandardsMarkdownViewer } from '@/components/standards/StandardsMarkdownViewer'
import type { TableSourceColumnDto, TableSourceDto } from '@/types/backend/api'
import type { TableViewerContext } from '@/store/rightPanelStore'

import './StandardsTableViewer.css'

interface StandardsTableViewerProps {
  payload: TableSourceDto
  viewerContext?: TableViewerContext
}

const HIDDEN_DISPLAY_COLUMNS = new Set([
  'material_id',
  'row_id',
  'requires_note_1',
  'requires_note_2_surface',
  'requires_note_3_volume',
])

const MARKDOWN_CELL_COLUMNS = new Set(['supplementary_examination'])

function renderCellValue(columnKey: string, cellValue: unknown) {
  const text = String(cellValue ?? '')
  if (MARKDOWN_CELL_COLUMNS.has(columnKey) && text.includes('](')) {
    return <StandardsMarkdownViewer content={text} />
  }
  return text
}

function displayColumnsForTable(columns: TableSourceColumnDto[]): TableSourceColumnDto[] {
  return columns.filter((column) => !HIDDEN_DISPLAY_COLUMNS.has(column.key))
}

function normalizeFilterValue(value: string): string {
  return value.trim().toLowerCase()
}

function cellMatchesFilter(cellValue: unknown, filterValue: string): boolean {
  const normalizedFilter = normalizeFilterValue(filterValue)
  if (!normalizedFilter) {
    return true
  }

  const cellText = String(cellValue ?? '').toLowerCase()
  if (cellText.includes(normalizedFilter)) {
    return true
  }

  const filterDigits = normalizedFilter.replace(/[^\d.-]/g, '')
  const cellDigits = cellText.replace(/[^\d.-]/g, '')
  if (filterDigits && cellDigits) {
    return cellDigits.includes(filterDigits) || filterDigits.includes(cellDigits)
  }

  return false
}

function rowMatchesColumnFilters(
  row: Record<string, unknown>,
  filters: Record<string, string>,
  columnKeys: Set<string>,
): boolean {
  return Object.entries(filters).every(([key, value]) => {
    if (!columnKeys.has(key)) {
      return true
    }
    return cellMatchesFilter(row[key], value)
  })
}

function rowMatchesHighlight(
  row: Record<string, unknown>,
  highlightKeys: Record<string, string>,
  columnKeys: Set<string>,
): boolean {
  const entries = Object.entries(highlightKeys).filter(([, value]) => value.trim())
  if (entries.length === 0) {
    return false
  }
  return entries.every(([key, value]) => {
    if (!columnKeys.has(key)) {
      return false
    }
    return cellMatchesFilter(row[key], value)
  })
}

function initialColumnFilters(
  columns: TableSourceColumnDto[],
  viewerContext?: TableViewerContext,
): Record<string, string> {
  const columnKeys = new Set(columns.map((column) => column.key))
  const next: Record<string, string> = {}

  for (const [key, value] of Object.entries(viewerContext?.columnFilters ?? {})) {
    if (columnKeys.has(key) && value.trim()) {
      next[key] = value
    }
  }

  return next
}

export function StandardsTableViewer({ payload, viewerContext }: StandardsTableViewerProps) {
  const displayColumns = useMemo(
    () => displayColumnsForTable(payload.columns),
    [payload.columns],
  )
  const columnKeys = useMemo(
    () => new Set(displayColumns.map((column) => column.key)),
    [displayColumns],
  )
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>(() =>
    initialColumnFilters(displayColumns, viewerContext),
  )
  const highlightRowRef = useRef<HTMLTableRowElement | null>(null)

  useEffect(() => {
    setColumnFilters(initialColumnFilters(displayColumns, viewerContext))
  }, [payload.table_id, displayColumns, viewerContext])

  const filteredRows = useMemo(() => {
    return payload.rows.filter((row) => rowMatchesColumnFilters(row, columnFilters, columnKeys))
  }, [payload.rows, columnFilters, columnKeys])

  const highlightKeys = viewerContext?.highlightKeys ?? {}

  const highlightedRowIndex = useMemo(() => {
    if (Object.keys(highlightKeys).length === 0) {
      return -1
    }
    return filteredRows.findIndex((row) =>
      rowMatchesHighlight(row, highlightKeys, columnKeys),
    )
  }, [filteredRows, highlightKeys, columnKeys])

  useEffect(() => {
    highlightRowRef.current?.scrollIntoView({ block: 'nearest' })
  }, [highlightedRowIndex, filteredRows.length])

  const updateColumnFilter = (key: string, value: string) => {
    setColumnFilters((current) => {
      const next = { ...current }
      if (value.trim()) {
        next[key] = value
      } else {
        delete next[key]
      }
      return next
    })
  }

  return (
    <div className="standards-table-viewer">
      <header className="standards-table-viewer__header">
        <h3 className="standards-table-viewer__title">{payload.title}</h3>
        {payload.source_path ? (
          <p className="standards-table-viewer__meta">
            {payload.standard} · {payload.source_path}
          </p>
        ) : null}
        {payload.description ? (
          <div className="standards-table-viewer__description">
            <StandardsMarkdownViewer content={payload.description} />
          </div>
        ) : null}
      </header>

      <p className="standards-table-viewer__count" aria-live="polite">
        {filteredRows.length} of {payload.rows.length} rows
      </p>

      {displayColumns.length === 0 ? (
        <p className="standards-table-viewer__empty">No columns available for this table.</p>
      ) : (
        <div className="standards-table-viewer__table-wrap">
          <table className="standards-table-viewer__table">
            <thead>
              <tr>
                {displayColumns.map((column) => (
                  <th key={column.key}>{column.label}</th>
                ))}
              </tr>
              <tr className="standards-table-viewer__filter-row">
                {displayColumns.map((column) => (
                  <th key={`${column.key}-filter`} className="standards-table-viewer__filter-cell">
                    <input
                      type="search"
                      value={columnFilters[column.key] ?? ''}
                      onChange={(event) => updateColumnFilter(column.key, event.target.value)}
                      placeholder={`Filter ${column.label}…`}
                      className="standards-table-viewer__column-filter"
                      aria-label={`Filter ${column.label}`}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr className="standards-table-viewer__empty-row">
                  <td colSpan={displayColumns.length}>
                    No rows match the current filters.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row, index) => {
                  const isHighlighted = index === highlightedRowIndex
                  return (
                    <tr
                      key={`${payload.table_id}-row-${index}`}
                      ref={isHighlighted ? highlightRowRef : undefined}
                      className={
                        isHighlighted ? 'standards-table-viewer__row--highlighted' : undefined
                      }
                    >
                      {displayColumns.map((column) => (
                        <td key={column.key}>{renderCellValue(column.key, row[column.key])}</td>
                      ))}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
