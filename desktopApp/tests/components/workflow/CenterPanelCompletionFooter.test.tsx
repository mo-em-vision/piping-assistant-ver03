import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CenterPanelCompletionFooter } from '@/components/workflow/CenterPanelCompletionFooter'
import { useReportStore } from '@/store/reportStore'

describe('CenterPanelCompletionFooter', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useReportStore.setState({
      summary: null,
      loading: false,
      generating: false,
      userError: null,
      loadReport: vi.fn().mockResolvedValue(undefined),
      generateReport: vi.fn().mockResolvedValue(undefined),
      downloadReport: vi.fn().mockResolvedValue(undefined),
      clearReport: vi.fn(),
    })
  })

  it('renders related workflows above generate report in the bottom section', () => {
    render(
      <CenterPanelCompletionFooter
        taskId="mock-pipe-thickness"
        relatedWorkflowsBlock={{
          id: 'next-workflows-task-1-pipe_wall_thickness_design',
          type: 'next_workflows',
          related_workflow_label: 'Related Workflows',
          suggestions: [
            {
              workflow_id: 'mawp_design',
              title: 'Maximum Allowable Working Pressure (MAWP)',
              available: true,
              action: { type: 'start_workflow', workflow_id: 'mawp_design' },
            },
          ],
        }}
      />,
    )

    expect(
      screen.getByText('Related Workflows: Maximum Allowable Working Pressure (MAWP)'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()

    const relatedLine = screen.getByText(
      'Related Workflows: Maximum Allowable Working Pressure (MAWP)',
    )
    const generateReport = screen.getByRole('button', { name: 'Generate report' })
    expect(
      relatedLine.compareDocumentPosition(generateReport) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('renders only report actions when no related workflows block is present', () => {
    render(<CenterPanelCompletionFooter taskId="mock-pipe-thickness" relatedWorkflowsBlock={null} />)

    expect(screen.queryByText(/Related Workflows:/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()
  })
})
