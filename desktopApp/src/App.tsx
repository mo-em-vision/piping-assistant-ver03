import { env } from '@/config/env'
import { useBackendConnection } from '@/hooks/useBackend'
import './App.css'

function statusLabel(status: string): string {
  switch (status) {
    case 'connected':
      return 'Connected'
    case 'starting':
      return 'Connecting…'
    case 'error':
      return 'Unavailable'
    default:
      return 'Stopped'
  }
}

function App() {
  const { backendStatus, isRetrying, retryConnection } = useBackendConnection()

  return (
    <div className="app">
      <header className="app__header">
        <p className="app__eyebrow">Phase 1 — Desktop Shell</p>
        <h1 className="app__title">{env.appName}</h1>
        <p className="app__subtitle">
          Application window, menu, startup process, and backend connection layer.
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
              <dt>Platform</dt>
              <dd>{window.electronAPI?.platform ?? 'browser'}</dd>
            </div>
            <div>
              <dt>Backend URL</dt>
              <dd>{backendStatus.url}</dd>
            </div>
            <div>
              <dt>Backend</dt>
              <dd>
                <span className={`status-pill status-pill--${backendStatus.status}`}>
                  {statusLabel(backendStatus.status)}
                </span>
              </dd>
            </div>
            {backendStatus.detail ? (
              <div>
                <dt>Detail</dt>
                <dd className="status-detail">{backendStatus.detail}</dd>
              </div>
            ) : null}
          </dl>

          {backendStatus.status === 'error' ? (
            <button
              type="button"
              className="retry-button"
              onClick={() => {
                void retryConnection()
              }}
              disabled={isRetrying}
            >
              {isRetrying ? 'Retrying…' : 'Retry connection'}
            </button>
          ) : null}
        </section>

        <p className="app__hint">
          The three-panel workspace and task flows arrive in Phase 2 and beyond.
        </p>
      </main>
    </div>
  )
}

export default App
