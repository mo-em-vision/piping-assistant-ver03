import type { StandardsBrowseNodeDto } from '@/types/backend/api'

import { StandardsBrowserTree } from './StandardsBrowserTree'

function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M10.25 10.25 14 14"
      />
    </svg>
  )
}

function CollapseSidebarIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M6.5 3.5 10 8l-3.5 4.5M3 3.5v9"
      />
    </svg>
  )
}

interface StandardsBrowserSidebarProps {
  standardLabel: string
  tree: StandardsBrowseNodeDto[]
  searchQuery: string
  searchOpen: boolean
  selectedId: string | null
  onToggleSearch: () => void
  onSearchChange: (value: string) => void
  onCollapse: () => void
  onSelect: (node: StandardsBrowseNodeDto) => void
}

export function StandardsBrowserSidebar({
  standardLabel,
  tree,
  searchQuery,
  searchOpen,
  selectedId,
  onToggleSearch,
  onSearchChange,
  onCollapse,
  onSelect,
}: StandardsBrowserSidebarProps) {
  return (
    <aside className="standards-browser-sidebar">
      <div className="standards-browser-sidebar__toolbar">
        <button
          type="button"
          className={`standards-browser-sidebar__icon-button${searchOpen ? ' standards-browser-sidebar__icon-button--active' : ''}`}
          aria-label="Search standards"
          title="Search standards"
          onClick={onToggleSearch}
        >
          <SearchIcon />
        </button>
        <button
          type="button"
          className="standards-browser-sidebar__icon-button"
          aria-label="Collapse standards sidebar"
          title="Collapse sidebar"
          onClick={onCollapse}
        >
          <CollapseSidebarIcon />
        </button>
      </div>

      <p className="standards-browser-sidebar__standard">{standardLabel}</p>

      {searchOpen ? (
        <input
          type="search"
          className="standards-browser-sidebar__search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search standards…"
          aria-label="Search standards"
        />
      ) : null}

      <div className="standards-browser-sidebar__tree">
        <StandardsBrowserTree
          tree={tree}
          searchQuery={searchQuery}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      </div>
    </aside>
  )
}

function ExpandSidebarIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M9.5 3.5 6 8l3.5 4.5M13 3.5v9"
      />
    </svg>
  )
}

export function StandardsBrowserExpandRail({ onExpand }: { onExpand: () => void }) {
  return (
    <div className="standards-browser-expand-rail">
      <button
        type="button"
        className="standards-browser-sidebar__icon-button"
        aria-label="Expand standards sidebar"
        title="Expand sidebar"
        onClick={onExpand}
      >
        <ExpandSidebarIcon />
      </button>
    </div>
  )
}
