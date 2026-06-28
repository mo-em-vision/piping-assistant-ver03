import { useState } from 'react'

import type { StandardsBrowseNodeDto } from '@/types/backend/api'

import { filterBrowseTree, isSelectableBrowseNode } from './standardsBrowseUtils'

interface StandardsBrowserTreeProps {
  tree: StandardsBrowseNodeDto[]
  searchQuery: string
  selectedId: string | null
  onSelect: (node: StandardsBrowseNodeDto) => void
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      width="12"
      height="12"
      aria-hidden="true"
      className={`standards-browser-tree__chevron${open ? ' standards-browser-tree__chevron--open' : ''}`}
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 4.25 9.75 8 6 11.75"
      />
    </svg>
  )
}

function depthClass(depth: number, kind: 'group' | 'leaf'): string {
  if (kind === 'leaf') {
    return 'standards-browser-tree__depth-leaf'
  }
  if (depth <= 0) {
    return 'standards-browser-tree__depth-0'
  }
  if (depth === 1) {
    return 'standards-browser-tree__depth-1'
  }
  return 'standards-browser-tree__depth-2'
}

function TreeNode({
  node,
  searchQuery,
  selectedId,
  onSelect,
  forceOpen,
  depth,
}: {
  node: StandardsBrowseNodeDto
  searchQuery: string
  selectedId: string | null
  onSelect: (node: StandardsBrowseNodeDto) => void
  forceOpen: boolean
  depth: number
}) {
  const [open, setOpen] = useState(depth === 0)

  if (node.kind === 'group') {
    const children = node.children ?? []
    const isOpen = forceOpen || open
    const isSelected = selectedId === node.id

    const handleHeaderClick = () => {
      if (!forceOpen) {
        setOpen((value) => !value)
      }
      onSelect(node)
    }

    return (
      <div className="standards-browser-tree__group">
        <button
          type="button"
          className={`standards-browser-tree__group-header ${depthClass(depth, 'group')}${isSelected ? ' standards-browser-tree__group-header--active' : ''}`}
          aria-expanded={isOpen}
          onClick={handleHeaderClick}
        >
          <ChevronIcon open={isOpen} />
          <span className="standards-browser-tree__group-label">{node.label}</span>
        </button>
        {isOpen ? (
          <div className="standards-browser-tree__children">
            {children.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                searchQuery={searchQuery}
                selectedId={selectedId}
                onSelect={onSelect}
                forceOpen={forceOpen}
                depth={depth + 1}
              />
            ))}
          </div>
        ) : null}
      </div>
    )
  }

  if (!isSelectableBrowseNode(node)) {
    return null
  }

  const isActive = selectedId === node.id

  return (
    <button
      type="button"
      className={`standards-browser-tree__leaf ${depthClass(depth, 'leaf')}${isActive ? ' standards-browser-tree__leaf--active' : ''}`}
      onClick={() => onSelect(node)}
    >
      {node.label}
    </button>
  )
}

export function StandardsBrowserTree({
  tree,
  searchQuery,
  selectedId,
  onSelect,
}: StandardsBrowserTreeProps) {
  const filteredTree = filterBrowseTree(tree, searchQuery)
  const forceOpen = searchQuery.trim().length > 0

  if (filteredTree.length === 0) {
    return <p className="standards-browser-tab__hint">No standards nodes match your search.</p>
  }

  return (
    <div className="standards-browser-tree" role="tree" aria-label="ASME B31.3 standards index">
      {filteredTree.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          searchQuery={searchQuery}
          selectedId={selectedId}
          onSelect={onSelect}
          forceOpen={forceOpen}
          depth={0}
        />
      ))}
    </div>
  )
}
