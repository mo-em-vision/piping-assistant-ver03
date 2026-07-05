import { useInspectorStore } from '@dev-ui/inspector/inspectorStore'

import { useDevUiActive } from '@/hooks/useDevUiActive'
import { useDevToolsStore } from '@/store/devToolsStore'

import './DevToolsHeaderControls.css'

export function DevToolsHeaderControls() {
  const devUiActive = useDevUiActive()
  const toggleDevMode = useDevToolsStore((state) => state.toggleDevMode)
  const inspectorOpen = useInspectorStore((state) => state.open)
  const toggleInspector = useInspectorStore((state) => state.toggleOpen)

  const openStudio = () => {
    void window.electronAPI?.openStudioWindow?.()
  }

  return (
    <div className="dev-tools-header">
      <label className="dev-tools-header__toggle" title="Enables Inspector, graph explorer, and node editing. Modifies graph sources on disk.">
        <input type="checkbox" checked={devUiActive} onChange={toggleDevMode} />
        <span>Dev Mode</span>
      </label>
      {devUiActive ? (
        <>
          <span className="app-header__badge" title="Modifies graph sources on disk.">
            Dev
          </span>
          <button type="button" className="app-header__inspector-toggle" onClick={toggleInspector}>
            {inspectorOpen ? 'Hide Inspector' : 'Inspector'}
          </button>
          <button type="button" className="dev-tools-header__studio" onClick={openStudio}>
            Node Dev Studio
          </button>
        </>
      ) : null}
    </div>
  )
}
