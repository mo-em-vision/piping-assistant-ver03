import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const desktopAppRoot = path.resolve(__dirname, '..')
const repoRoot = path.resolve(desktopAppRoot, '..')
const targetRoot = path.join(desktopAppRoot, 'resources', 'backend')

const BACKEND_PACKAGES = ['api', 'engine', 'models', 'storage', 'cli', 'config', 'ai']
const BACKEND_DIRS = ['knowledge', 'workflows', 'dev']
const BACKEND_FILES = ['requirements.txt']

function shouldCopy(sourcePath) {
  const normalized = sourcePath.replaceAll('\\', '/')
  return !normalized.includes('/__pycache__/') && !normalized.endsWith('.pyc')
}

function copyTree(source, destination) {
  fs.cpSync(source, destination, {
    recursive: true,
    force: true,
    filter: (src) => shouldCopy(src),
  })
}

function ensureCleanTarget() {
  if (fs.existsSync(targetRoot)) {
    fs.rmSync(targetRoot, { recursive: true, force: true })
  }
  fs.mkdirSync(targetRoot, { recursive: true })
}

function main() {
  ensureCleanTarget()

  for (const packageName of BACKEND_PACKAGES) {
    const source = path.join(repoRoot, packageName)
    if (!fs.existsSync(source)) {
      throw new Error(`Missing backend package: ${packageName}`)
    }
    copyTree(source, path.join(targetRoot, packageName))
  }

  for (const dirName of BACKEND_DIRS) {
    const source = path.join(repoRoot, dirName)
    if (!fs.existsSync(source)) {
      throw new Error(`Missing backend directory: ${dirName}`)
    }
    copyTree(source, path.join(targetRoot, dirName))
  }

  for (const fileName of BACKEND_FILES) {
    const source = path.join(repoRoot, fileName)
    if (!fs.existsSync(source)) {
      throw new Error(`Missing backend file: ${fileName}`)
    }
    fs.copyFileSync(source, path.join(targetRoot, fileName))
  }

  fs.writeFileSync(
    path.join(targetRoot, 'README.txt'),
    [
      'Bundled engineering backend for the desktop installer.',
      'Runtime Python is expected at .venv/Scripts/python.exe after prepare-backend-venv.ps1.',
      '',
    ].join('\n'),
    'utf8',
  )

  console.log(`Staged backend at ${targetRoot}`)
}

main()
