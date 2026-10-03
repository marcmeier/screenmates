import { expect, test } from '@playwright/test'
import { KINO } from '../playwright.config.js'

// A host shares "their screen", two friends watch live, the host ends the show
// and logs the film as seen with everyone who watched.
test.skip(!KINO, 'MediaMTX fehlt – `make kino-install` aktiviert die Kino-Tests')
test.describe.configure({ mode: 'serial' })

// Headless Chromium has no screen to pick: stand in an animated canvas plus a tone.
function fakeScreen() {
  navigator.mediaDevices.getDisplayMedia = async () => {
    const c = Object.assign(document.createElement('canvas'), { width: 640, height: 360 })
    const g = c.getContext('2d')
    let f = 0
    setInterval(() => {
      g.fillStyle = `hsl(${f++ % 360} 70% 30%)`
      g.fillRect(0, 0, 640, 360)
    }, 33)
    const stream = c.captureStream(30)
    const ac = new AudioContext()
    const osc = ac.createOscillator()
    const dest = ac.createMediaStreamDestination()
    osc.connect(dest)
    osc.start()
    stream.addTrack(dest.stream.getAudioTracks()[0])
    return stream
  }
}

let host, viewer

async function join(browser, name) {
  const ctx = await browser.newContext()
  await ctx.addInitScript(fakeScreen)
  const page = await ctx.newPage()
  page.errors = []
  page.on('pageerror', (e) => page.errors.push(e.message))
  // The only expected failure: a viewer retrying WHEP right after the show ended.
  page.on('response', (r) => {
    const path = new URL(r.url()).pathname
    if (r.status() >= 400 && !(path === '/api/kino/whep' && r.status() === 404)) page.errors.push(`${r.status()} ${path}`)
  })
  await page.goto('/#/abend')
  await page.getByPlaceholder('Neuer Name').fill(name)
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  return page
}

const videoTime = (page) => page.evaluate(() => document.querySelector('.screen video')?.currentTime ?? 0)

test.beforeAll(async ({ browser }) => {
  host = await join(browser, 'Kim')
  viewer = await join(browser, 'Lu')
})

test.afterAll(() => {
  expect(host.errors, 'host: no errors').toEqual([])
  expect(viewer.errors, 'viewer: no errors').toEqual([])
})

test('the Kino shows up in the navigation, empty at first', async () => {
  await host.getByRole('link', { name: 'Kino' }).click()
  await expect(host.getByText('Gerade läuft nichts.')).toBeVisible()
  await expect(host.getByRole('heading', { name: 'Senden' })).toBeHidden() // not host yet
})

test('the host links a film and goes live', async () => {
  await host.keyboard.press('Control+Shift+H')
  await host.getByPlaceholder('Host-Film suchen').fill('alien')
  await host.locator('.picker .results button', { hasText: 'Alien' }).first().click()
  await expect(host.locator('.host-badge')).toBeVisible()
  await host.getByRole('link', { name: 'Kino' }).click()

  await host.getByRole('button', { name: /Mit Film aus dem Katalog/ }).click()
  await host.locator('.desk').getByPlaceholder('Film suchen').fill('shining')
  await host.locator('.desk .results button', { hasText: 'Shining' }).first().click()
  await host.getByRole('button', { name: 'Übertragung starten' }).click()
  await expect(host.getByText('Du bist live', { exact: true })).toBeVisible({ timeout: 10_000 })
})

test('friends see it everywhere and watch in sync', async () => {
  await expect(viewer.getByText('Jetzt im Kino:')).toBeVisible({ timeout: 10_000 })
  await expect(viewer.locator('.nav .live')).toBeVisible()
  await viewer.getByRole('link', { name: 'Zuschauen' }).click()
  await expect.poll(() => videoTime(viewer), { timeout: 15_000 }).toBeGreaterThan(1)
  const audio = await viewer.evaluate(() => document.querySelector('.screen video').srcObject.getAudioTracks().length)
  expect(audio).toBe(1)
  await viewer.getByRole('button', { name: 'Ton an' }).first().click()
  expect(await viewer.evaluate(() => document.querySelector('.screen video').muted)).toBe(false)
  await expect(host.locator('.viewers')).toContainText('2 schauen', { timeout: 15_000 })
})

test('the show keeps running while the host browses', async () => {
  await host.getByRole('link', { name: 'Finden' }).click()
  const before = await videoTime(viewer)
  await expect.poll(() => videoTime(viewer), { timeout: 5_000 }).toBeGreaterThan(before + 1)
  await host.getByRole('link', { name: 'Kino' }).click()
})

test('the host ends the show and logs who watched', async () => {
  host.once('dialog', (d) => d.accept())
  await host.getByRole('button', { name: 'Übertragung beenden' }).click()
  await expect(host.getByText('Gerade läuft nichts.')).toBeVisible({ timeout: 10_000 })
  await expect(viewer.getByText('Gerade läuft nichts.')).toBeVisible({ timeout: 15_000 })

  await host.getByRole('button', { name: 'Eintragen' }).click()
  await expect(host.locator('.toast', { hasText: 'mit 2 Zuschauenden' })).toBeVisible()
  const watched = await host.evaluate(() => fetch('/api/watched').then((r) => r.json()))
  const entry = watched.watched.find((w) => w.movie.title === 'Shining')
  expect(entry.participants).toHaveLength(2)
})
