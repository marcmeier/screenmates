import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

// End-to-end tests run against the real backend serving the built frontend,
// on a throwaway database and without TMDB/LLM keys (seed catalogue).
// With MediaMTX installed (`make kino-install`) the Kino runs for real too,
// on its own ports so it doesn't collide with a running `make dev`.
const PORT = 8765
const MTX = resolve('../.tools/mediamtx')
// E2E_BASE_URL points the suite at an already running stack (e.g. docker compose)
// instead of starting servers; E2E_KINO=1 says that stack has a media server.
const EXTERNAL = process.env.E2E_BASE_URL
export const KINO = EXTERNAL ? process.env.E2E_KINO === '1' : existsSync(MTX)
const db = join(tmpdir(), `screenmates-e2e-${Date.now()}.db`)
const python = process.env.PYTHON || (existsSync('../backend/.venv/bin/python') ? '.venv/bin/python' : 'python')

const backend = {
  command: `${python} -m uvicorn app.main:app --port ${PORT}`,
  cwd: '../backend',
  env: {
    DATABASE_URL: `sqlite:///${db}`,
    TMDB_API_KEY: '',
    LLM_API_KEY: '',
    ...(KINO && { MEDIAMTX_WEBRTC_URL: 'http://127.0.0.1:18889', MEDIAMTX_API_URL: 'http://127.0.0.1:19997' }),
  },
  url: `http://127.0.0.1:${PORT}/api/health`,
  reuseExistingServer: false,
  timeout: 30_000,
}

const mediamtx = {
  command: `${MTX} ../deploy/mediamtx.yml`,
  env: {
    MTX_AUTHHTTPADDRESS: `http://127.0.0.1:${PORT}/api/kino/mtx-auth`,
    MTX_APIADDRESS: '127.0.0.1:19997',
    MTX_WEBRTCADDRESS: '127.0.0.1:18889',
    MTX_WEBRTCLOCALUDPADDRESS: ':18189',
    MTX_WEBRTCLOCALTCPADDRESS: ':18189',
    MTX_WEBRTCADDITIONALHOSTS: '127.0.0.1',
    MTX_WEBRTCICESERVERS2: '[]',
  },
  url: 'http://127.0.0.1:19997/v3/paths/list',
  reuseExistingServer: false,
  timeout: 15_000,
}

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: EXTERNAL || `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1400, height: 900 },
  },
  webServer: EXTERNAL ? [] : KINO ? [backend, mediamtx] : [backend],
})
