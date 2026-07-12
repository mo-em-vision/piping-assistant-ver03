import { useMemo } from 'react'

import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import type { StandardsReferenceKind } from '@/store/rightPanelStore'
import type { ReferenceChipDto } from '@/types/backend/outputs'

import './ReferenceChipList.css'

interface ReferenceChipListProps {
  chips?: ReferenceChipDto[] | null
  className?: string
}

function chipReferenceKind(chip: ReferenceChipDto): StandardsReferenceKind {
  return chip.ref_type === 'table' ? 'table' : 'node'
}

function chipReferenceId(chip: ReferenceChipDto): string {
  return (
    chip.target.node_id ??
    chip.target.equation_id ??
    chip.target.table_id ??
    chip.target.paragraph_id ??
    chip.id
  )
}

function dedupeChips(chips: ReferenceChipDto[]): ReferenceChipDto[] {
  const seen = new Set<string>()
  const ordered: ReferenceChipDto[] = []
  for (const chip of chips) {
    const key = `${chip.ref_type}:${chip.id}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    ordered.push(chip)
  }
  return ordered
}

export function ReferenceChipList({ chips, className }: ReferenceChipListProps) {
  const visibleChips = useMemo(() => dedupeChips(chips ?? []), [chips])
  const inline = className?.includes('reference-chip-list--inline')

  if (!visibleChips.length) {
    return null
  }

  if (inline) {
    return (
      <span className={className}>
        {visibleChips.map((chip, index) => (
          <span key={`${chip.ref_type}:${chip.id}`}>
            {index > 0 ? ', ' : null}
            <StandardReferenceLink
              referenceKind={chipReferenceKind(chip)}
              referenceId={chipReferenceId(chip)}
              label={chip.label}
              activateTab
              variant="inline"
            />
          </span>
        ))}
      </span>
    )
  }

  return (
    <div className={['reference-chip-list', className].filter(Boolean).join(' ')}>
      {visibleChips.map((chip) => (
        <StandardReferenceLink
          key={`${chip.ref_type}:${chip.id}`}
          referenceKind={chipReferenceKind(chip)}
          referenceId={chipReferenceId(chip)}
          label={chip.label}
          activateTab
          variant="inline"
        />
      ))}
    </div>
  )
}
