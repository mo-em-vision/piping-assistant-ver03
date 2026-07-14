import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'
import { buildCenterPanelTranscriptParts } from '@/utils/buildCenterPanelTranscript'

const here = dirname(fileURLToPath(import.meta.url))
const sharedContractPath = resolve(here, '../../../contracts/center_panel_report_role_order.json')

describe('centerPanelContract sync', () => {
  it('matches shared contracts/center_panel_report_role_order.json', () => {
    const payload = JSON.parse(readFileSync(sharedContractPath, 'utf-8')) as string[]
    expect([...REPORT_ROLE_ORDER]).toEqual(payload)
  })

  it('keeps scroll history ordered while parking next_workflows in the footer slot', () => {
    const parts = buildCenterPanelTranscriptParts(
      [],
      [
        {
          block_id: 'result-summary-pipe_wall_thickness_design',
          kind: 'text',
          source: 'runtime',
          text: 'Done.',
          payload: { display_role: 'result_summary' },
        },
        {
          block_id: 'next-workflows-task-1-pipe_wall_thickness_design',
          kind: 'next_workflows',
          source: 'workflow_runtime',
          related_workflow_label: 'Related Workflows',
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

    const roles = parts.historyItems.map((item) => item.block.display_role)
    expect(roles).toEqual(['result_summary'])
    expect(parts.relatedWorkflowsBlock?.display_role).toBe('next_workflows')
    expect(roles).toEqual(
      [...roles].sort((left, right) => {
        const leftIndex = REPORT_ROLE_ORDER.indexOf(left ?? '')
        const rightIndex = REPORT_ROLE_ORDER.indexOf(right ?? '')
        return (
          (leftIndex === -1 ? REPORT_ROLE_ORDER.length : leftIndex) -
          (rightIndex === -1 ? REPORT_ROLE_ORDER.length : rightIndex)
        )
      }),
    )
  })
})
