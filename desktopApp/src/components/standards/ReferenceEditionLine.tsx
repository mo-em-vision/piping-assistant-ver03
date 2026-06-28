import './ReferenceEditionLine.css'

interface ReferenceEditionLineProps {
  standard: string
  revisionYear?: number | null
}

export function ReferenceEditionLine({ standard, revisionYear }: ReferenceEditionLineProps) {
  if (revisionYear == null) {
    return null
  }

  return (
    <p className="reference-edition-line">
      Based on {standard}, {revisionYear} edition
    </p>
  )
}
