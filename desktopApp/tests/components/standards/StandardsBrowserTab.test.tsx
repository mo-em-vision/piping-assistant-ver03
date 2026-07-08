import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { StandardsBrowserTab } from '@/components/standards/StandardsBrowserTab'
import { standardsApi } from '@/services/api/standardsApi'
import { useUiStore } from '@/store/uiStore'
import type { StandardsBrowseDto } from '@/types/backend/api'

vi.mock('@/services/api/standardsApi', () => ({
  standardsApi: {
    getBrowse: vi.fn(),
    getNode: vi.fn(),
    getNodeSubsection: vi.fn(),
    getTable: vi.fn(),
  },
}))

vi.mock('@/components/standards/NodeReferenceTab', () => ({
  NodeReferenceTab: ({ nodeId }: { nodeId: string }) => <div>Node preview: {nodeId}</div>,
}))

vi.mock('@/components/standards/TableReferenceTab', () => ({
  TableReferenceTab: ({ tableId }: { tableId: string }) => <div>Table preview: {tableId}</div>,
}))

const mockBrowse: StandardsBrowseDto = {
  standard: 'ASME B31.3',
  standard_slug: 'asme_b31.3',
  revision_year: 2024,
  tree: [
    {
      id: 'section:available-tasks',
      kind: 'group',
      label: 'Available tasks',
      children: [
        {
          id: 'workflow:pipe_wall_thickness_design',
          kind: 'workflow',
          label: 'Pipe Wall Thickness Design',
          workflow_id: 'pipe_wall_thickness_design',
          related_workflows: [
            {
              id: 'pipe_wall_thickness_design',
              name: 'Pipe Wall Thickness Design',
              description: 'ASME B31.3 wall thickness design workflow',
              discipline: 'Piping',
              available: true,
            },
          ],
        },
      ],
    },
    {
      id: 'section:304',
      kind: 'group',
      label: 'Section 304',
      children: [
        {
          id: 'B313-304.1.1',
          kind: 'node',
          label: '§304.1.1',
          description: 'Required thickness relationship',
          node_id: 'B313-304.1.1',
          content_kind: 'node',
          related_workflows: [
            {
              id: 'pipe_wall_thickness_design',
              name: 'Pipe Wall Thickness Design',
              description: 'ASME B31.3 wall thickness design workflow',
              discipline: 'Piping',
              available: true,
            },
          ],
        },
      ],
    },
    {
      id: 'section:appendix-a',
      kind: 'group',
      label: 'Appendix A',
      children: [
        {
          id: 'group:appendix-a-tables',
          kind: 'group',
          label: 'tables',
          children: [
            {
              id: 'B313-table-A-1',
              kind: 'table',
              label: 'Table A-1',
              node_id: 'B313-table-A-1',
              table_id: 'asme_b31.3_A-1',
              content_kind: 'table',
              related_workflows: [],
            },
          ],
        },
      ],
    },
  ],
  workflow_index: {},
}

describe('StandardsBrowserTab', () => {
  beforeEach(() => {
    vi.mocked(standardsApi.getBrowse).mockResolvedValue(mockBrowse)
    useUiStore.setState({ createTaskDialog: { open: false } })
  })

  it('shows the current standard label and section tree', async () => {
    render(<StandardsBrowserTab />)

    expect(await screen.findByText('ASME B31.3')).toBeInTheDocument()
    expect(screen.getByText('Available tasks')).toBeInTheDocument()
    expect(screen.getByText('Section 304')).toBeInTheDocument()
  })

  it('renders section tree and loads node preview when a leaf is selected', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    fireEvent.click(screen.getByRole('button', { name: '§304.1.1' }))

    expect(await screen.findByText('Node preview: B313-304.1.1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pipe Wall Thickness Design' })).toBeInTheDocument()
    expect(screen.queryByText('Required thickness relationship')).not.toBeInTheDocument()
  })

  it('opens the create task dialog when a related workflow is clicked', async () => {
    render(<StandardsBrowserTab />)

    fireEvent.click(await screen.findByRole('button', { name: '§304.1.1' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pipe Wall Thickness Design' }))

    await waitFor(() => {
      expect(useUiStore.getState().createTaskDialog).toEqual({
        open: true,
        preselectedWorkflowId: 'pipe_wall_thickness_design',
      })
    })
  })

  it('toggles search from the sidebar toolbar', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('ASME B31.3')
    expect(screen.queryByRole('searchbox', { name: 'Search standards' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Search standards' }))
    expect(screen.getByRole('searchbox', { name: 'Search standards' })).toBeInTheDocument()
  })

  it('collapses and expands the standards sidebar', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    fireEvent.click(screen.getByRole('button', { name: 'Collapse standards sidebar' }))

    expect(screen.queryByText('Section 304')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Expand standards sidebar' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Expand standards sidebar' }))
    expect(await screen.findByText('Section 304')).toBeInTheDocument()
  })

  it('filters the tree by search query', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    fireEvent.click(screen.getByRole('button', { name: 'Search standards' }))
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search standards' }), {
      target: { value: 'B313-304.1.1' },
    })

    expect(screen.getByRole('button', { name: '§304.1.1' })).toBeInTheDocument()
  })

  it('shows a section index when a group heading is selected', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    fireEvent.click(screen.getByRole('button', { name: 'Section 304' }))

    const index = await screen.findByRole('navigation', { name: 'Section 304 index' })
    fireEvent.click(within(index).getByRole('button', { name: '§304.1.1' }))

    expect(await screen.findByText('Node preview: B313-304.1.1')).toBeInTheDocument()
  })

  it('loads table preview using resolved table_id for appendix tables', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Appendix A')
    const tree = screen.getByRole('tree', { name: 'ASME B31.3 standards index' })
    fireEvent.click(within(tree).getByRole('button', { name: 'tables' }))
    fireEvent.click(within(tree).getByRole('button', { name: 'Table A-1' }))

    expect(await screen.findByText('Table preview: asme_b31.3_A-1')).toBeInTheDocument()
  })

  it('toggles subsection visibility when the section header is clicked', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    const tree = screen.getByRole('tree', { name: 'ASME B31.3 standards index' })
    expect(within(tree).getByRole('button', { name: '§304.1.1' })).toBeInTheDocument()

    fireEvent.click(within(tree).getByRole('button', { name: 'Section 304' }))
    expect(within(tree).queryByRole('button', { name: '§304.1.1' })).not.toBeInTheDocument()

    fireEvent.click(within(tree).getByRole('button', { name: 'Section 304' }))
    expect(within(tree).getByRole('button', { name: '§304.1.1' })).toBeInTheDocument()
  })

  it('shows a resize handle between the sidebar and preview', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    expect(screen.getByRole('separator', { name: 'Resize panel' })).toBeInTheDocument()
  })

  it('hides the resize handle when the sidebar is collapsed', async () => {
    render(<StandardsBrowserTab />)

    await screen.findByText('Section 304')
    fireEvent.click(screen.getByRole('button', { name: 'Collapse standards sidebar' }))

    expect(screen.queryByRole('separator', { name: 'Resize panel' })).not.toBeInTheDocument()
  })
})
