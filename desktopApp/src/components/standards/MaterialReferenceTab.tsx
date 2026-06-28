import { useEffect, useState } from 'react'

import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { getMockMaterialDetail } from '@/mock/materials.mock'
import { materialApi } from '@/services/api/materialApi'

import type { MaterialDetailDto, MaterialMechanicalRowDto } from '@/types/backend/materials'

import './MaterialReferenceTab.css'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface MaterialReferenceTabProps {
  materialId: string
}

function formatStrength(entry: MaterialMechanicalRowDto['tensile_strength_min']): string {
  if (!entry) {
    return '—'
  }
  if (entry.ksi != null) {
    return `${entry.ksi} ksi`
  }
  if (entry.pa != null) {
    return `${Math.round(entry.pa / 1_000_000)} MPa`
  }
  if (entry.value != null) {
    return String(entry.value)
  }
  return '—'
}

function MechanicalTable({ detail }: { detail: MaterialDetailDto }) {
  const room = detail.mechanical_properties.room_temperature
  const elevated = detail.mechanical_properties.elevated_temperature ?? []
  const rows = room ? [room, ...elevated] : elevated

  if (rows.length === 0) {
    return <p className="material-reference-tab__hint">No mechanical property data available.</p>
  }

  return (
    <table className="material-reference-tab__table">
      <thead>
        <tr>
          <th scope="col">Test temp (°F)</th>
          <th scope="col">Tensile min</th>
          <th scope="col">Yield min</th>
          <th scope="col">Elongation min (%)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={`${row.test_temperature_f ?? 'room'}-${index}`}>
            <td>{row.test_temperature_f ?? '—'}</td>
            <td>{formatStrength(row.tensile_strength_min)}</td>
            <td>{formatStrength(row.yield_strength_min)}</td>
            <td>{row.elongation_min_percent ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ChemicalLimits({ composition }: { composition: Record<string, unknown> }) {
  const limits = composition.limits
  if (!limits || typeof limits !== 'object') {
    return <p className="material-reference-tab__hint">No chemical composition data available.</p>
  }

  const entries = Object.entries(limits as Record<string, Record<string, number>>)
  if (entries.length === 0) {
    return <p className="material-reference-tab__hint">No chemical composition data available.</p>
  }

  return (
    <table className="material-reference-tab__table">
      <thead>
        <tr>
          <th scope="col">Element</th>
          <th scope="col">Min (%)</th>
          <th scope="col">Max (%)</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([element, bounds]) => (
          <tr key={element}>
            <td>{element}</td>
            <td>{bounds.min ?? '—'}</td>
            <td>{bounds.max ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PhysicalProperties({ properties }: { properties: Record<string, unknown> }) {
  const entries = Object.entries(properties).filter(([, value]) => value != null && value !== '')
  if (entries.length === 0) {
    return <p className="material-reference-tab__hint">No physical property data available.</p>
  }

  return (
    <dl className="material-reference-tab__properties">
      {entries.map(([key, value]) => (
        <div key={key} className="material-reference-tab__property">
          <dt>{key.replace(/_/g, ' ')}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

export function MaterialReferenceTab({ materialId }: MaterialReferenceTabProps) {
  const [detail, setDetail] = useState<MaterialDetailDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const request = useMockData
      ? Promise.resolve(getMockMaterialDetail(materialId))
      : materialApi.getDetail(materialId)

    void request
      .then((data) => {
        if (!cancelled) {
          setDetail(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not load material details.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [materialId])

  if (loading) {
    return <p className="material-reference-tab__hint">Loading material details…</p>
  }

  if (error) {
    return <p className="material-reference-tab__error">{error}</p>
  }

  if (!detail) {
    return <p className="material-reference-tab__hint">No material details available.</p>
  }

  return (
    <div className="material-reference-tab">
      <header className="material-reference-tab__header">
        <h2 className="material-reference-tab__title">{detail.display_name}</h2>
        <p className="material-reference-tab__spec">{detail.specification}</p>
        {detail.uns_number ? (
          <p className="material-reference-tab__meta">UNS {detail.uns_number}</p>
        ) : null}
        {detail.product_form ? (
          <p className="material-reference-tab__meta">Product form: {detail.product_form.replace(/_/g, ' ')}</p>
        ) : null}
      </header>

      <section className="material-reference-tab__section">
        <h3 className="material-reference-tab__section-title">Mechanical properties</h3>
        <MechanicalTable detail={detail} />
      </section>

      <section className="material-reference-tab__section">
        <h3 className="material-reference-tab__section-title">Chemical composition</h3>
        <ChemicalLimits composition={detail.chemical_composition} />
      </section>

      <section className="material-reference-tab__section">
        <h3 className="material-reference-tab__section-title">Physical properties</h3>
        <PhysicalProperties properties={detail.physical_properties} />
      </section>

      {detail.aliases.length > 0 ? (
        <section className="material-reference-tab__section">
          <h3 className="material-reference-tab__section-title">Aliases</h3>
          <p className="material-reference-tab__aliases">{detail.aliases.join(', ')}</p>
        </section>
      ) : null}

      {detail.notes.length > 0 ? (
        <section className="material-reference-tab__section">
          <h3 className="material-reference-tab__section-title">Notes</h3>
          <ul className="material-reference-tab__notes">
            {detail.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {detail.source_node ? (
        <footer className="material-reference-tab__footer">
          <StandardReferenceLink
            referenceKind="node"
            referenceId={detail.source_node}
            label="View standards reference"
          />
        </footer>
      ) : null}
    </div>
  )
}
