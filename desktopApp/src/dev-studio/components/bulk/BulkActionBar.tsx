import { devStudioApi } from '@/dev-studio/api/devStudioApi'
import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

function importFormatFromName(name: string): 'json' | 'markdown' | 'csv' | null {
  const lower = name.toLowerCase()
  if (lower.endsWith('.json')) return 'json'
  if (lower.endsWith('.md') || lower.endsWith('.markdown') || lower.endsWith('.yaml') || lower.endsWith('.yml')) {
    return 'markdown'
  }
  if (lower.endsWith('.csv')) return 'csv'
  return null
}

export function BulkActionBar() {
  const selectedIds = useDevStudioStore((s) => s.selectedIds)
  const bulkDelete = useDevStudioStore((s) => s.bulkDelete)
  const bulkAddTags = useDevStudioStore((s) => s.bulkAddTags)
  const exportSelected = useDevStudioStore((s) => s.exportSelected)
  const refreshNodes = useDevStudioStore((s) => s.refreshNodes)
  const pack = useDevStudioStore((s) => s.pack)
  const count = selectedIds.size

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json,.md,.markdown,.yaml,.yml,.csv'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      const fmt = importFormatFromName(file.name)
      if (!fmt) {
        window.alert('Unsupported file type. Use .json, .md, or .csv')
        return
      }
      const text = await file.text()
      if (fmt === 'json') {
        const data = JSON.parse(text) as unknown
        const nodes = Array.isArray(data) ? data : (data as { nodes?: unknown[] }).nodes ?? []
        await devStudioApi.importNodes(pack, { format: 'json', nodes })
      } else {
        await devStudioApi.importNodes(pack, { format: fmt, content: text })
      }
      await refreshNodes()
    }
    input.click()
  }

  if (!count) {
    return (
      <div className="dev-studio__toolbar">
        <button type="button" className="dev-studio__btn" onClick={handleImport}>
          Import nodes
        </button>
      </div>
    )
  }

  return (
    <div className="dev-studio__toolbar">
      <span className="dev-studio__list-item-meta">{count} selected</span>
      <button type="button" className="dev-studio__btn dev-studio__btn--danger" onClick={() => void bulkDelete()}>
        Delete
      </button>
      <button
        type="button"
        className="dev-studio__btn"
        onClick={() => {
          const tag = window.prompt('Tag to add:')
          if (tag) void bulkAddTags([tag])
        }}
      >
        Add tag
      </button>
      <button type="button" className="dev-studio__btn" onClick={() => void exportSelected('json')}>
        Export JSON
      </button>
      <button type="button" className="dev-studio__btn" onClick={() => void exportSelected('csv')}>
        Export CSV
      </button>
      <button type="button" className="dev-studio__btn" onClick={() => void exportSelected('markdown')}>
        Export Markdown
      </button>
      <button type="button" className="dev-studio__btn" onClick={handleImport}>
        Import
      </button>
    </div>
  )
}
