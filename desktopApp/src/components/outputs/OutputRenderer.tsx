import { EquationOutput } from './EquationOutput'
import { ApplicabilityOutput } from './ApplicabilityOutput'
import { NextWorkflowsOutput } from './NextWorkflowsOutput'
import { ParagraphContextOutput } from './ParagraphContextOutput'
import { ReferenceOutput } from './ReferenceOutput'
import { ResultOutput } from './ResultOutput'
import { ResultSummaryOutput } from './ResultSummaryOutput'
import { TableOutput } from './TableOutput'
import { TextOutput } from './TextOutput'
import { WarningOutput } from './WarningOutput'

import { type DisplayOutputBlock } from '@/types/backend/outputs'
import { isRegisteredCenterPanelBlockType } from '@/utils/centerPanelBlockRegistry'

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
        if (!isRegisteredCenterPanelBlockType(block.type)) {
          if (import.meta.env.DEV) {
            console.warn(
              `OutputRenderer skipped unregistered center-panel block type: ${block.type}`,
            )
          }
          return null
        }
        switch (block.type) {
          case 'text':
            return <TextOutput key={block.id} block={block} />
          case 'warning':
            return <WarningOutput key={block.id} block={block} />
          case 'paragraph_context':
            return <ParagraphContextOutput key={block.id} block={block} />
          case 'result_summary':
            return <ResultSummaryOutput key={block.id} block={block} />
          case 'applicability':
            return <ApplicabilityOutput key={block.id} block={block} />
          case 'equation':
            return <EquationOutput key={block.id} block={block} />
          case 'table':
            return <TableOutput key={block.id} block={block} />
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
