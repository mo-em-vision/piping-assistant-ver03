import type { TextOutputBlock } from '@/types/backend/outputs'

interface TextOutputProps {
  block: TextOutputBlock
}

export function TextOutput({ block }: TextOutputProps) {
  const variantClass =
    block.variant === 'warning'
      ? 'output-text output-text--warning'
      : block.variant === 'caption'
        ? 'output-text output-text--caption'
        : 'output-text'

  return (
    <article className="output-block">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <p className={variantClass}>{block.content}</p>
    </article>
  )
}
