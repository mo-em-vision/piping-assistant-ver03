import { useEffect, useState } from 'react'
import { useGraphStore } from '../store/graphStore'

interface SearchBarProps {
  onFocusNode: (nodeId: string) => void
}

export default function SearchBar({ onFocusNode }: SearchBarProps) {
  const rawNodes = useGraphStore((s) => s.rawNodes)
  const expansionView = useGraphStore((s) => s.expansionView)
  const searchQuery = useGraphStore((s) => s.searchQuery)
  const setSearchQuery = useGraphStore((s) => s.setSearchQuery)
  const setSearchMatchIds = useGraphStore((s) => s.setSearchMatchIds)
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const needle = searchQuery.trim().toLowerCase()
    if (!needle) {
      setSearchMatchIds([])
      setActiveIndex(0)
      return
    }
    const searchable = expansionView
      ? expansionView.nodes.map((node) => ({ id: node.id, name: node.label }))
      : rawNodes.map((node) => ({ id: node.id, name: node.name }))
    const matches = searchable
      .filter(
        (node) =>
          node.id.toLowerCase().includes(needle) ||
          node.name.toLowerCase().includes(needle),
      )
      .map((node) => node.id)
    setSearchMatchIds(matches)
    setActiveIndex(0)
    if (matches.length > 0) {
      onFocusNode(matches[0])
    }
  }, [searchQuery, rawNodes, expansionView, setSearchMatchIds, onFocusNode])

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    const matches = useGraphStore.getState().searchMatchIds
    if (event.key === 'Enter' && matches.length > 0) {
      const nextIndex = (activeIndex + 1) % matches.length
      setActiveIndex(nextIndex)
      onFocusNode(matches[nextIndex])
    }
  }

  return (
    <div>
      <div className="section-title">Search</div>
      <input
        className="search-input"
        placeholder="Search by name or ID…"
        value={searchQuery}
        onChange={(event) => setSearchQuery(event.target.value)}
        onKeyDown={handleKeyDown}
      />
    </div>
  )
}
