import type { ResultOutputBlock } from '@/types/backend/outputs'

interface ResultOutputProps {
  block: ResultOutputBlock
}

export function ResultOutput({ block }: ResultOutputProps) {
  const statusClass = block.status ? ` output-result--${block.status}` : ''

  return (
    <article className={`output-block output-result${statusClass}`}>
      <p className="output-result__label">{block.label}</p>
      <p className="output-result__value">
        {block.value}
        {block.unit ? ` ${block.unit}` : ''}
      </p>
    </article>
  )
}
