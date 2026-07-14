import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

// #region agent log
fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
  body: JSON.stringify({
    sessionId: 'ed32ea',
    location: 'main.tsx:post-import',
    message: 'main.tsx module loaded (imports succeeded)',
    data: { electronApiPresent: typeof window.electronAPI !== 'undefined' },
    timestamp: Date.now(),
    hypothesisId: 'A',
  }),
}).catch(() => {})
// #endregion

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Root element not found')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// #region agent log
fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
  body: JSON.stringify({
    sessionId: 'ed32ea',
    location: 'main.tsx:post-render',
    message: 'React createRoot.render invoked',
    data: {},
    timestamp: Date.now(),
    hypothesisId: 'D',
  }),
}).catch(() => {})
// #endregion
