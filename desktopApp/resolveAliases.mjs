import path from 'node:path'
import { fileURLToPath } from 'node:url'

const desktopAppDir = path.dirname(fileURLToPath(import.meta.url))
export const repoRoot = path.resolve(desktopAppDir, '..')

function pkg(name) {
  return path.resolve(desktopAppDir, 'node_modules', name)
}

/** Shared Vite/Vitest aliases — lets `dev/desktop_ui` resolve desktopApp dependencies. */
export const resolveAliases = {
  '@': path.resolve(desktopAppDir, 'src'),
  '@dev-ui': path.resolve(repoRoot, 'dev/desktop_ui'),
  react: pkg('react'),
  'react/jsx-runtime': path.join(pkg('react'), 'jsx-runtime.js'),
  'react/jsx-dev-runtime': path.join(pkg('react'), 'jsx-dev-runtime.js'),
  'react-dom': pkg('react-dom'),
  '@testing-library/react': pkg('@testing-library/react'),
  '@testing-library/user-event': pkg('@testing-library/user-event'),
}
