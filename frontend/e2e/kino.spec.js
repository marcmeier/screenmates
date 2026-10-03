import { execFileSync, spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium, expect, test } from '@playwright/test'
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

// Keep a handle on every RTCPeerConnection so tests can read what was negotiated.
function trackPeerConnections() {
  const Orig = window.RTCPeerConnection
  window.__pcs = []
  window.RTCPeerConnection = function (...args) {
    const pc = new Orig(...args)
    window.__pcs.push(pc)
    return pc
  }
  window.RTCPeerConnection.prototype = Orig.prototype
}

// What the newest peer connection is receiving: transport and codecs.
function negotiated(page) {
  return page.evaluate(async () => {
    const all = [...(await window.__pcs.at(-1).getStats()).values()]
    const pair = all.find((s) => s.type === 'candidate-pair' && s.nominated && s.state === 'succeeded')
    const codec = (kind) => {
      const rtp = all.find((s) => s.type === 'inbound-rtp' && s.kind === kind)
      return all.find((s) => s.id === rtp?.codecId)?.mimeType
    }
    return { protocol: all.find((s) => s.id === pair?.localCandidateId)?.protocol, video: codec('video'), audio: codec('audio') }
  })
}

// FFmpeg ≥ 8 speaks WHIP like OBS does: no browser, no cookie, only the stream key.
// Prefers the pinned build from scripts/ffmpeg-whip.sh, else the system one.
const FFMPEG = existsSync(resolve('../.tools/ffmpeg')) ? resolve('../.tools/ffmpeg') : 'ffmpeg'
function ffmpegWithWhip() {
  try {
    return execFileSync(FFMPEG, ['-hide_banner', '-muxers'], { encoding: 'utf8' }).includes('whip')
  } catch {
    return false
  }
}

let host, viewer

async function join(browser, name, ctx = null) {
  ctx ??= await browser.newContext()
  await ctx.addInitScript(fakeScreen)
  await ctx.addInitScript(trackPeerConnections)
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

// The menu entry, not the "Jetzt im Kino" banner that also links there.
const kinoLink = (page) => page.getByRole('navigation', { name: 'Hauptbereiche' }).getByRole('link', { name: /^Kino/ })

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
  await kinoLink(host).click()
  await expect(host.getByText('Gerade läuft nichts.')).toBeVisible()
  await expect(host.getByRole('heading', { name: 'Senden' })).toBeHidden() // not host yet
})

test('the host links a film and goes live', async () => {
  await host.keyboard.press('Control+Shift+H')
  await host.getByPlaceholder('Host-Film suchen').fill('alien')
  await host.locator('.picker .results button', { hasText: 'Alien' }).first().click()
  await expect(host.locator('.host-badge')).toBeVisible()
  await kinoLink(host).click()

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
  // H.264 at the source resolution from the start (VP8 used to start at a fraction of it).
  expect((await negotiated(viewer)).video).toBe('video/H264')
  expect(await viewer.evaluate(() => document.querySelector('.screen video').videoWidth)).toBe(640)
  await expect(host.locator('.onair .stats')).toContainText('640×360')
  await viewer.getByRole('button', { name: 'Ton an' }).first().click()
  expect(await viewer.evaluate(() => document.querySelector('.screen video').muted)).toBe(false)
  await expect(host.locator('.viewers')).toContainText('2 schauen', { timeout: 15_000 })
})

test('the show keeps running while the host browses', async () => {
  await host.getByRole('link', { name: 'Finden' }).click()
  const before = await videoTime(viewer)
  await expect.poll(() => videoTime(viewer), { timeout: 5_000 }).toBeGreaterThan(before + 1)
  await kinoLink(host).click()
})

test('a viewer whose network blocks UDP still gets the picture (TCP fallback)', async () => {
  // Chromium then only uses TCP ICE candidates: the situation in strict company or hotel networks.
  const strict = await chromium.launch({ args: ['--force-webrtc-ip-handling-policy=disable_non_proxied_udp'] })
  try {
    const page = await join(null, 'Strikt', await strict.newContext({ baseURL: host.url().split('/#')[0] }))
    await kinoLink(page).click()
    await expect.poll(() => videoTime(page), { timeout: 20_000 }).toBeGreaterThan(1)
    expect((await negotiated(page)).protocol).toBe('tcp')
    expect(page.errors).toEqual([])
  } finally {
    await strict.close()
  }
})

test('the host ends the show and logs who watched', async () => {
  host.once('dialog', (d) => d.accept())
  await host.getByRole('button', { name: 'Übertragung beenden' }).click()
  await expect(host.getByText('Gerade läuft nichts.')).toBeVisible({ timeout: 10_000 })
  await expect(viewer.getByText('Gerade läuft nichts.')).toBeVisible({ timeout: 15_000 })

  await host.getByRole('button', { name: 'Eintragen' }).click()
  await expect(host.locator('.toast', { hasText: 'mit 3 Zuschauenden' })).toBeVisible()
  const watched = await host.evaluate(() => fetch('/api/watched').then((r) => r.json()))
  const entry = watched.watched.find((w) => w.movie.title === 'Shining')
  expect(entry.participants).toHaveLength(3) // Kim, Lu and the strict-network viewer
})

test('an OBS-style client sends with the stream key and ends cleanly', async () => {
  test.skip(!ffmpegWithWhip(), 'FFmpeg mit WHIP fehlt – `./scripts/ffmpeg-whip.sh` aktiviert diesen OBS-Ersatz')
  const { server, key } = await host.evaluate(() => fetch('/api/kino/obs').then((r) => r.json()))
  // Same formats OBS sends over WHIP: H.264 without B-frames, Opus.
  const obs = spawn(FFMPEG, [
    '-hide_banner', '-loglevel', 'error', '-re',
    '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30',
    '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
    '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency', '-bf', '0', '-g', '30', '-b:v', '2M',
    '-c:a', 'libopus', '-ar', '48000', '-ac', '2',
    // A fixed duration ends the stream like "Stop streaming" in OBS. (Killing FFmpeg
    // with a signal mid-stream sometimes leaves it hanging – an FFmpeg quirk.)
    '-t', '15', '-f', 'whip', '-authorization', key, server,
  ])
  const exited = new Promise((done) => obs.on('exit', done))
  try {
    await expect(viewer.locator('.nav .live')).toBeVisible({ timeout: 15_000 })
    await kinoLink(viewer).click()
    await expect.poll(() => videoTime(viewer), { timeout: 20_000 }).toBeGreaterThan(1)
    expect(await negotiated(viewer)).toMatchObject({ video: 'video/H264', audio: 'audio/opus' })
    expect(await viewer.evaluate(() => document.querySelector('.screen video').videoWidth)).toBe(1280)
    // When it ends, the client sends its WHIP DELETE and the Kino goes dark for everyone.
    await expect(viewer.getByText('Gerade läuft nichts.')).toBeVisible({ timeout: 20_000 })
  } finally {
    const timer = setTimeout(() => obs.kill('SIGKILL'), 20_000)
    await exited
    clearTimeout(timer)
  }
})
