// Backward compatibility: always free both explorer dev ports.
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const portsScript = resolve(scriptDir, 'free-dev-ports.mjs')
const result = spawnSync(process.execPath, [portsScript], { stdio: 'inherit' })
process.exit(result.status ?? 1)
