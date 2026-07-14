import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OutputRenderer } from '@/components/outputs/OutputRenderer'
import { buildCenterPanelTranscript, buildCenterPanelTranscriptParts } from '@/utils/buildCenterPanelTranscript'
import { guidanceTranscriptToDisplayBlocks } from '@/utils/flowGuidanceTranscript'
import {
  assertRegisteredCenterPanelBlockTypes,
  CENTER_PANEL_BLOCK_REGISTRY,
  CENTER_PANEL_BLOCK_TYPES,
  filterRegisteredCenterPanelBlocks,
  isRegisteredCenterPanelBlockType,
  OUTPUT_RENDERER_COMPONENT_BY_TYPE,
} from '@/utils/centerPanelBlockRegistry'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

const here = dirname(fileURLToPath(import.meta.url))
const registryPath = resolve(here, '../../../contracts/center_panel_output_block_types.json')

function minimalBlock(type: (typeof CENTER_PANEL_BLOCK_TYPES)[number]): DisplayOutputBlock {
  switch (type) {
    case 'text':
      return { id: `text-${type}`, type, content: 'Sample text block.' }
    case 'warning':
      return { id: `warning-${type}`, type, content: 'Sample warning.' }
    case 'paragraph_context':
      return { id: `paragraph-${type}`, type, content: 'Paragraph context.' }
    case 'result_summary':
      return { id: `summary-${type}`, type, content: 'Result summary.' }
    case 'equation':
      return {
        id: `equation-${type}`,
        type,
        content: 't = PD / 2(SEW + PY)',
        display: 't = PD / 2(SEW + PY)',
      }
    case 'table':
      return {
        id: `table-${type}`,
        type,
        columns: [{ key: 'symbol', label: 'Symbol' }],
        rows: [{ symbol: 'P' }],
      }
    case 'reference':
      return {
        id: `reference-${type}`,
        type,
        standard: 'ASME B31.3',
        excerpt: 'Reference excerpt.',
      }
    case 'result':
      return {
        id: `result-${type}`,
        type,
        label: 'Minimum thickness',
        value: '2.252',
        unit: 'mm',
      }
    case 'next_workflows':
      return {
        id: `next-${type}`,
        type,
        suggestions: [
          {
            workflow_id: 'mawp_design',
            title: 'MAWP Design',
            available: false,
          },
        ],
      }
    default:
      throw new Error(`missing minimal fixture for ${type}`)
  }
}

describe('centerPanelBlockRegistry', () => {
  it('matches shared contracts/center_panel_output_block_types.json', () => {
    const payload = JSON.parse(readFileSync(registryPath, 'utf-8')) as {
      block_types: Array<{ type: string }>
    }
    expect([...CENTER_PANEL_BLOCK_TYPES]).toEqual(payload.block_types.map((entry) => entry.type))
    expect(CENTER_PANEL_BLOCK_REGISTRY.block_types).toHaveLength(payload.block_types.length)
  })

  it('maps every registered type to an OutputRenderer component name', () => {
    for (const entry of CENTER_PANEL_BLOCK_REGISTRY.block_types) {
      expect(OUTPUT_RENDERER_COMPONENT_BY_TYPE[entry.type as keyof typeof OUTPUT_RENDERER_COMPONENT_BY_TYPE]).toBe(
        entry.desktop_component,
      )
    }
  })

  it('filterRegisteredCenterPanelBlocks keeps only registry types', () => {
    const filtered = filterRegisteredCenterPanelBlocks([
      { id: 'eq', type: 'equation' },
      { id: 'rogue', type: 'internal_debug_blob' },
    ])
    expect(filtered).toHaveLength(1)
    expect(filtered[0]?.id).toBe('eq')
  })

  it('rejects unregistered block types', () => {
    expect(isRegisteredCenterPanelBlockType('equation')).toBe(true)
    expect(isRegisteredCenterPanelBlockType('planner_debug_blob')).toBe(false)
    expect(() =>
      assertRegisteredCenterPanelBlockTypes([{ id: 'rogue', type: 'planner_debug_blob' }]),
    ).toThrow(/unregistered block type/)
  })
})

describe('center panel rendered outputs', () => {
  it('OutputRenderer renders every registered block type', () => {
    for (const blockType of CENTER_PANEL_BLOCK_TYPES) {
      const block = minimalBlock(blockType)
      const { unmount } = render(<OutputRenderer blocks={[block]} />)
      expect(screen.queryByText('No engineering outputs yet.')).not.toBeInTheDocument()
      unmount()
    }
  })

  it('OutputRenderer ignores unregistered block types', () => {
    const { container } = render(
      <OutputRenderer
        blocks={[
          {
            id: 'rogue',
            type: 'planner_json_dump' as DisplayOutputBlock['type'],
            content: 'must not appear',
          } as DisplayOutputBlock,
        ]}
        emptyMessage="No engineering outputs yet."
      />,
    )
    expect(container.querySelector('.output-renderer')?.textContent?.trim()).toBe('')
    expect(screen.queryByText('must not appear')).not.toBeInTheDocument()
  })

  it('buildCenterPanelTranscript drops unregistered engineering block types', () => {
    const items = buildCenterPanelTranscript(
      [
        minimalBlock('equation'),
        {
          id: 'rogue-engineering',
          type: 'planner_json_dump' as DisplayOutputBlock['type'],
          content: 'must not appear',
        } as DisplayOutputBlock,
      ],
      [],
      'pipe_wall_thickness_design',
    )

    assertRegisteredCenterPanelBlockTypes(
      items.map((item) => item.block),
      'buildCenterPanelTranscript filtered',
    )
    expect(items.some((item) => item.block.id.startsWith('equation-'))).toBe(true)
    expect(items.some((item) => item.block.id === 'rogue-engineering')).toBe(false)
  })

  it('buildCenterPanelTranscript only exposes registered block types', () => {
    const parts = buildCenterPanelTranscriptParts(
      CENTER_PANEL_BLOCK_TYPES.map((blockType) => minimalBlock(blockType)),
      [
        {
          block_id: 'guidance-branch',
          kind: 'guidance',
          source: 'guidance',
          text: 'Select internal or external pressure loading.',
        },
        {
          block_id: 'next-workflows-task-1',
          kind: 'next_workflows',
          source: 'workflow_runtime',
          title: 'Suggested next workflows',
          text: 'You may continue with:',
          suggestions: [
            {
              workflow_id: 'mawp_design',
              title: 'MAWP Design',
              available: false,
            },
          ],
        },
      ],
      'pipe_wall_thickness_design',
    )
    const items = parts.historyItems

    assertRegisteredCenterPanelBlockTypes(
      items.map((item) => item.block),
      'buildCenterPanelTranscript',
    )
    expect(items.some((item) => item.block.type === 'equation')).toBe(true)
    expect(items.some((item) => item.block.type === 'text')).toBe(true)
    expect(items.some((item) => item.block.type === 'next_workflows')).toBe(false)
    expect(parts.relatedWorkflowsBlock?.type).toBe('next_workflows')
  })

  it('maps result_summary transcript text to result_summary block type', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'result-summary-pipe_wall_thickness_design',
        kind: 'text',
        source: 'runtime',
        text: 'Calculation complete.',
        payload: { display_role: 'result_summary' },
      },
    ])

    expect(blocks).toHaveLength(1)
    expect(blocks[0]?.type).toBe('result_summary')
  })
})
