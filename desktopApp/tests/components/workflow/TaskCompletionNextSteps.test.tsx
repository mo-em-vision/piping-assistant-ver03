import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TaskCompletionNextSteps } from '@/components/workflow/TaskCompletionNextSteps'
import { mockReportSummary } from '@/mock/report.mock'
import { useReportStore } from '@/store/reportStore'

describe('TaskCompletionNextSteps', () => {
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

  it('renders generate report button without download buttons before generation', () => {
    render(<TaskCompletionNextSteps taskId="mock-pipe-thickness" />)

    expect(screen.getByText('Next Steps:')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Download HTML' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Download PDF' })).not.toBeInTheDocument()
  })

  it('shows download buttons after report is generated', () => {
    useReportStore.setState({
      summary: {
        ...mockReportSummary,
        generated: true,
        files: {
          html: { available: true, filename: 'mock-pipe-thickness.html', updated_at: null },
          markdown: { available: true, filename: 'mock-pipe-thickness.md', updated_at: null },
          pdf: { available: true, filename: 'mock-pipe-thickness.pdf', updated_at: null },
          json: { available: true, filename: 'mock-pipe-thickness.json', updated_at: null },
        },
      },
    })

    render(<TaskCompletionNextSteps taskId="mock-pipe-thickness" />)

    expect(screen.getByRole('button', { name: 'Download HTML' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download PDF' })).toBeInTheDocument()
  })

  it('generates report with default html format', async () => {
    const generateReport = vi.fn().mockResolvedValue(undefined)
    useReportStore.setState({ generateReport })

    render(<TaskCompletionNextSteps taskId="mock-pipe-thickness" />)

    fireEvent.click(screen.getByRole('button', { name: 'Generate report' }))

    await waitFor(() => {
      expect(generateReport).toHaveBeenCalledWith('mock-pipe-thickness')
    })
  })

  it('loads report status on mount', () => {
    const loadReport = vi.fn().mockResolvedValue(undefined)
    useReportStore.setState({ loadReport })

    render(<TaskCompletionNextSteps taskId="mock-pipe-thickness" />)

    expect(loadReport).toHaveBeenCalledWith('mock-pipe-thickness')
  })

  it('hides and shows report actions with the toolbar toggle', () => {
    render(<TaskCompletionNextSteps taskId="mock-pipe-thickness" />)

    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Hide' }))

    expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Show' }))

    expect(screen.getByRole('button', { name: 'Generate report' })).toBeInTheDocument()
  })
})
