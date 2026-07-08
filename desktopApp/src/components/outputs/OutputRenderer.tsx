import { EquationOutput } from './EquationOutput'
import { GraphOutput } from './GraphOutput'
import { NextWorkflowsOutput } from './NextWorkflowsOutput'
import { ReferenceOutput } from './ReferenceOutput'
import { ResultOutput } from './ResultOutput'
import { TableOutput } from './TableOutput'
import { TextOutput } from './TextOutput'

import type { DisplayOutputBlock } from '@/types/backend/outputs'

import './OutputRenderer.css'

interface OutputRendererProps {
  blocks: DisplayOutputBlock[]
  emptyMessage?: string
  variant?: 'card' | 'inline'
}

export function OutputRenderer({
  blocks,
  emptyMessage = 'No engineering outputs yet.',
  variant = 'card',
}: OutputRendererProps) {
  if (blocks.length === 0) {
    return <p className="placeholder__hint">{emptyMessage}</p>
  }

  return (
    <div className={`output-renderer${variant === 'inline' ? ' output-renderer--inline' : ''}`}>
      {blocks.map((block) => {
        switch (block.type) {
          case 'text':
            return <TextOutput key={block.id} block={block} />
          case 'equation':
            return <EquationOutput key={block.id} block={block} />
          case 'table':
            return <TableOutput key={block.id} block={block} />
          case 'graph':
            return <GraphOutput key={block.id} block={block} />
          case 'reference':
            return <ReferenceOutput key={block.id} block={block} />
          case 'result':
            return <ResultOutput key={block.id} block={block} />
          case 'next_workflows':
            return <NextWorkflowsOutput key={block.id} block={block} />
          default:
            return null
        }
      })}
    </div>
  )
}
