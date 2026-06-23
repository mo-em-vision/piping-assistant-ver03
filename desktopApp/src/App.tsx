import { env } from '@/config/env'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="app__header">
        <p className="app__eyebrow">Phase 0 — Foundation</p>
        <h1 className="app__title">{env.appName}</h1>
        <p className="app__subtitle">
          Desktop engineering workspace — presentation layer for the Ver03 backend.
        </p>
      </header>

      <main className="app__main">
        <section className="status-card">
          <h2>Application status</h2>
          <dl>
            <div>
              <dt>Environment</dt>
              <dd>{env.devMode ? 'Development' : 'Production'}</dd>
            </div>
            <div>
              <dt>Backend URL</dt>
              <dd>{env.backendUrl}</dd>
            </div>
            <div>
              <dt>Platform</dt>
              <dd>{window.electronAPI?.platform ?? 'browser'}</dd>
            </div>
          </dl>
        </section>

        <p className="app__hint">
          The three-panel workspace, backend connection, and task flows arrive in later phases.
        </p>
      </main>
    </div>
  )
}

export default App
