import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { DevStudioApp } from '@/dev-studio/DevStudioApp'
import '@/dev-studio/styles/dev-studio.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DevStudioApp />
  </StrictMode>,
)
