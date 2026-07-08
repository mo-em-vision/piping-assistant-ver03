import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ReferenceChipList } from '@/components/outputs/ReferenceChipList'

const openReferenceTab = vi.fn()

vi.mock('@/store/rightPanelStore', () => ({
  useRightPanelStore: (selector: (state: { openReferenceTab: typeof openReferenceTab }) => unknown) =>
    selector({ openReferenceTab }),
}))

vi.mock('@/store/taskStore', () => ({
  useTaskStore: () => null,
}))

vi.mock('@/store/uiStore', () => ({
  useUiStore: {
    setState: vi.fn(),
  },
}))

describe('ReferenceChipList', () => {
  it('renders backend-provided labels without raw ids as primary text', () => {
    render(
      <ReferenceChipList
        chips={[
          {
            ref_type: 'node',
            id: '304.1.2-a',
            label: '§304.1.2',
            target: { node_id: '304.1.2-a' },
          },
        ]}
      />,
    )

    expect(screen.getByRole('button', { name: '§304.1.2' })).toBeTruthy()
    expect(screen.queryByText('304.1.2-a')).toBeNull()
  })

  it('calls openReferenceTab with normalized target on click', () => {
    openReferenceTab.mockClear()

    render(
      <ReferenceChipList
        chips={[
          {
            ref_type: 'equation',
            id: 'asme-b313-required-wall-thickness',
            label: 'Eq. (3a)',
            target: {
              equation_id: 'asme-b313-required-wall-thickness',
              node_id: 'asme-b313-required-wall-thickness',
            },
          },
        ]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Eq. (3a)' }))
    expect(openReferenceTab).toHaveBeenCalledWith(
      'asme-b313-required-wall-thickness',
      'Eq. (3a)',
      'node',
      undefined,
      { activate: true },
    )
  })

  it('deduplicates duplicate chips', () => {
    render(
      <ReferenceChipList
        chips={[
          {
            ref_type: 'node',
            id: '304.1.2-a',
            label: '§304.1.2',
            target: { node_id: '304.1.2-a' },
          },
          {
            ref_type: 'node',
            id: '304.1.2-a',
            label: 'Duplicate',
            target: { node_id: '304.1.2-a' },
          },
        ]}
      />,
    )

    expect(screen.getAllByRole('button')).toHaveLength(1)
  })

  it('renders nothing when chips are absent', () => {
    const { container } = render(<ReferenceChipList chips={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
