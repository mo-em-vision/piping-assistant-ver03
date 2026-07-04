import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './theme/dark.css'

// #region agent log
window.addEventListener('error', (event) => {
  fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fd176a' },
    body: JSON.stringify({
      sessionId: 'fd176a',
      location: 'main.tsx:window.error',
      message: 'uncaught error',
      data: { message: event.message, filename: event.filename, lineno: event.lineno },
      timestamp: Date.now(),
      hypothesisId: 'F',
    }),
  }).catch(() => {})
})
// #endregion

const rootEl = document.getElementById('root')
if (!rootEl) {
  throw new Error('Missing #root element')
}

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// #region agent log
fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fd176a' },
  body: JSON.stringify({
    sessionId: 'fd176a',
    location: 'main.tsx:render',
    message: 'react render invoked',
    data: {},
    timestamp: Date.now(),
    hypothesisId: 'F',
    runId: 'post-fix',
  }),
}).catch(() => {})
// #endregion
