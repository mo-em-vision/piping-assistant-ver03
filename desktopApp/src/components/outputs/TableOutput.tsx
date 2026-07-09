import { useMemo, useState } from 'react'

import { EngineeringMathText, InlineMath, isEngineeringSymbol } from '@/components/math/engineeringMath'

import type { TableOutputBlock } from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'

interface TableOutputProps {
  block: TableOutputBlock
}

type SortDirection = 'asc' | 'desc'

export function TableOutput({ block }: TableOutputProps) {
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const rows = useMemo(() => {
    let nextRows = [...block.rows]

    if (query.trim()) {
      const needle = query.trim().toLowerCase()
      nextRows = nextRows.filter((row) =>
        Object.values(row).some((value) => String(value ?? '').toLowerCase().includes(needle)),
      )
    }

    if (sortKey) {
      nextRows.sort((left, right) => {
        const a = String(left[sortKey] ?? '')
        const b = String(right[sortKey] ?? '')
        const comparison = a.localeCompare(b, undefined, { numeric: true })
        return sortDirection === 'asc' ? comparison : -comparison
      })
    }

    return nextRows
  }, [block.rows, query, sortDirection, sortKey])

  const toggleSort = (key: string, sortable?: boolean) => {
    if (!sortable) {
      return
    }
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }

  const renderCell = (columnKey: string, value: unknown) => {
    const text = String(value ?? '')
    if (columnKey === 'symbol' && isEngineeringSymbol(text)) {
      return <InlineMath expression={text} />
    }
    return <EngineeringMathText text={text} />
  }

  return (
    <article className={`output-block${block.compact ? ' output-block--compact-table' : ''}`}>
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      {block.summary_text ? (
        <p className="output-block__summary">
          <EngineeringMathText text={block.summary_text} />
        </p>
      ) : null}
      {block.searchable ? (
        <div className="output-table__toolbar">
          <input
            className="output-table__search"
            type="search"
            placeholder="Search table…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search table"
          />
        </div>
      ) : null}
      <table className="output-table">
        <thead>
          <tr>
            {block.columns.map((column) => (
              <th key={column.key}>
                {column.sortable ? (
                  <button type="button" onClick={() => toggleSort(column.key, column.sortable)}>
                    {column.label}
                    {sortKey === column.key ? (sortDirection === 'asc' ? ' ↑' : ' ↓') : ''}
                  </button>
                ) : (
                  column.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const highlight =
              block.highlight_row &&
              String(row[block.highlight_row.column] ?? '') === block.highlight_row.value
            return (
            <tr
              key={`${block.id}-row-${index}`}
              className={highlight ? 'output-table__row--highlight' : undefined}
            >
              {block.columns.map((column) => (
                <td key={column.key}>{renderCell(column.key, row[column.key])}</td>
              ))}
            </tr>
            )
          })}
        </tbody>
      </table>
    </article>
  )
}
