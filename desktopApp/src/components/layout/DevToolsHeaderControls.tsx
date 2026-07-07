import { useDevUiActive } from '@/hooks/useDevUiActive'

import { useDevToolsStore } from '@/store/devToolsStore'



import './DevToolsHeaderControls.css'



export function DevToolsHeaderControls() {

  const devUiActive = useDevUiActive()

  const toggleDevMode = useDevToolsStore((state) => state.toggleDevMode)



  return (

    <div className="dev-tools-header">

      <label

        className="dev-tools-header__toggle"

        title="Enables Planner, Task State, and Operations tabs in the right panel."

      >

        <input type="checkbox" checked={devUiActive} onChange={toggleDevMode} />

        <span>Dev Mode</span>

      </label>

      {devUiActive ? (

        <span className="app-header__badge" title="Development tools active.">

          Dev

        </span>

      ) : null}

    </div>

  )

}

