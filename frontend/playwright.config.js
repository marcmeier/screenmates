import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

// End-to-end tests run against the real backend serving the built frontend,
// on a throwaway database and without TMDB/LLM keys (seed catalogue).
const PORT = 8765
const db = join(tmpdir(), `screenmates-e2e-${Date.now()}.db`)
const python = process.env.PYTHON || (existsSync('../backend/.venv/bin/python') ? '.venv/bin/python' : 'python')

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1400, height: 900 },
  },
  webServer: {
    command: `${python} -m uvicorn app.main:app --port ${PORT}`,
    cwd: '../backend',
    env: { DATABASE_URL: `sqlite:///${db}`, TMDB_API_KEY: '', LLM_API_KEY: '' },
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
