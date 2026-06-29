import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

export function BulkActionBar() {
  const selectedIds = useDevStudioStore((s) => s.selectedIds)
  const bulkDelete = useDevStudioStore((s) => s.bulkDelete)
  const bulkAddTags = useDevStudioStore((s) => s.bulkAddTags)
  const exportSelected = useDevStudioStore((s) => s.exportSelected)
  const count = selectedIds.size

  if (!count) return null

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
      <button
        type="button"
        className="dev-studio__btn"
        onClick={() => {
          const input = document.createElement('input')
          input.type = 'file'
          input.accept = '.json'
          input.onchange = async () => {
            const file = input.files?.[0]
            if (!file) return
            const text = await file.text()
            const data = JSON.parse(text) as unknown
            const nodes = Array.isArray(data) ? data : (data as { nodes?: unknown[] }).nodes ?? []
            const { devStudioApi } = await import('@/dev-studio/api/devStudioApi')
            const { useDevStudioStore } = await import('@/dev-studio/store/devStudioStore')
            const pack = useDevStudioStore.getState().pack
            await devStudioApi.importNodes(pack, { format: 'json', nodes })
            await useDevStudioStore.getState().refreshNodes()
          }
          input.click()
        }}
      >
        Import JSON
      </button>
    </div>
  )
}
