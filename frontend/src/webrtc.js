import { t, t as tr } from './i18n'
// WHIP (send) and WHEP (watch) over plain fetch + RTCPeerConnection.
// Signalling goes through screenmates (/api/kino/...), media straight to MediaMTX.

const ICE = [{ urls: 'stun:stun.l.google.com:19302' }]

// Viewer playout buffer. WebRTC defaults to ~50 ms for calls; for a film a bit of
// delay is free and evens out packet jitter. Measured on a live stream: at 300 ms
// presentation follows the capture cadence (worst deviation 65 ms → 24 ms), more
// buffer didn't help further. Everyone uses the same value, so viewers stay in sync.
export const PUFFER_MS = 300

function smoothPlayout(receiver) {
  try {
    if ('jitterBufferTarget' in receiver) receiver.jitterBufferTarget = PUFFER_MS
    else if ('playoutDelayHint' in receiver) receiver.playoutDelayHint = PUFFER_MS / 1000 // older Chrome
  } catch {
    /* not supported: the browser keeps its own small buffer */
  }
}

function iceGathered(pc, timeoutMs = 2500) {
  // Non-trickle: send the offer once all candidates are in (or after a timeout).
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve()
    const done = () => pc.iceGatheringState === 'complete' && resolve()
    pc.addEventListener('icegatheringstatechange', done)
    setTimeout(resolve, timeoutMs)
  })
}

async function negotiate(pc, url, mungeOffer = (sdp) => sdp) {
  const offer = await pc.createOffer()
  await pc.setLocalDescription({ type: 'offer', sdp: mungeOffer(offer.sdp) })
  await iceGathered(pc)
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/sdp' },
    body: pc.localDescription.sdp,
  })
  if (!res.ok) {
    const err = new Error((await res.json().catch(() => null))?.detail || tr('webrtc.verbindungFehlgeschlagenStatus', { status: res.status }))
    err.status = res.status
    throw err
  }
  await pc.setRemoteDescription({ type: 'answer', sdp: await res.text() })
  return res.headers.get('location')
}

function hangUp(location) {
  // Tell the server right away instead of waiting for the ICE timeout.
  if (location) fetch(location, { method: 'DELETE', credentials: 'same-origin', keepalive: true }).catch(() => {})
}

/**
 * Watch the live stream in `video`. Reconnects on its own when the stream drops
 * or starts later. `onState` receives 'verbinde' | 'live' | 'getrennt'.
 */
export function createViewer(video, onState = () => {}) {
  let pc = null
  let location = null
  let retry = null
  let stopped = false

  async function connect() {
    clearTimeout(retry)
    close()
    if (stopped) return
    onState('verbinde')
    pc = new RTCPeerConnection({ iceServers: ICE })
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })
    const stream = new MediaStream()
    pc.ontrack = (e) => {
      smoothPlayout(e.receiver)
      stream.addTrack(e.track)
      if (video.srcObject !== stream) video.srcObject = stream
    }
    pc.onconnectionstatechange = () => {
      if (pc?.connectionState === 'connected') onState('live')
      if (['failed', 'disconnected', 'closed'].includes(pc?.connectionState)) schedule()
    }
    try {
      // The receiver must ask for stereo, or Chrome mixes the sound down to mono.
      location = await negotiate(pc, '/api/kino/whep', (sdp) => withStereoOpus(sdp))
    } catch (e) {
      if (e.status === 401) return onState('getrennt') // no name chosen: don't hammer the server
      schedule()
    }
  }

  function schedule() {
    onState('getrennt')
    if (!stopped) retry = setTimeout(connect, 3000)
  }

  function close() {
    hangUp(location)
    location = null
    pc?.close()
    pc = null
  }

  return {
    start: connect,
    stop() {
      stopped = true
      clearTimeout(retry)
      close()
      video.srcObject = null
    },
  }
}

// Sending presets, measured with a demanding 1080p source (docs/KINO-QUALITAET.md):
// keeping the resolution and giving Chrome a start bitrate puts 1080p on screen from
// the first second instead of ramping up from 480x270 over ~15 s.
export const QUALITAET = {
  hoch: { key: 'hoch', height: 1080, maxBitrate: 8_000_000, startKbps: 4000, audioKbps: 192 },
  mittel: { key: 'mittel', height: 720, maxBitrate: 4_000_000, startKbps: 2500, audioKbps: 128 },
  sparsam: { key: 'sparsam', height: 480, maxBitrate: 2_000_000, startKbps: 1200, audioKbps: 96 },
}
for (const q of Object.values(QUALITAET)) Object.defineProperty(q, 'label', { get: () => t(`kino.qualitaet.${q.key}`) })
export const INHALT = {
  film: { key: 'film', fps: 30, degradation: 'maintain-resolution' },
  spiel: { key: 'spiel', fps: 60, degradation: 'maintain-framerate' },
}

/** Ask the user what to share. Throws if they cancel. */
export async function pickScreen({ audio = true, inhalt = 'film', leise = false } = {}) {
  const fps = INHALT[inhalt].fps
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: { frameRate: { ideal: fps, max: fps }, width: { ideal: 1920 }, height: { ideal: 1080 } },
    // Film sound, not a phone call: no voice processing, keep both channels.
    audio: audio && {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      channelCount: { ideal: 2 },
      sampleRate: { ideal: 48000 },
      // Chrome: the shared tab stays silent here, the host hears the (delayed) stream instead.
      suppressLocalAudioPlayback: leise,
    },
  })
  const [video] = stream.getVideoTracks()
  if (video) video.contentHint = 'motion' // films and games are moving pictures, not slides
  return stream
}

// H.264 looked cleanest at the same bitrate and every device decodes it (iPhones in
// hardware). VP8 is the fallback; VP9 came through black in our tests, so it goes last.
function preferCodecs(transceiver) {
  const caps = RTCRtpSender.getCapabilities?.('video')?.codecs
  if (!caps || !transceiver.setCodecPreferences) return
  const rank = (c) => ({ 'video/H264': 0, 'video/VP8': 1, 'video/AV1': 2 })[c.mimeType] ?? (c.mimeType === 'video/VP9' ? 9 : 5)
  transceiver.setCodecPreferences([...caps].sort((a, b) => rank(a) - rank(b)))
}

// Opus defaults to mono at ~32 kbit/s, tuned for voice. Asking for stereo with
// a real bitrate makes film sound sound like film.
export function withStereoOpus(sdp, kbps = null) {
  const opus = sdp.match(/a=rtpmap:(\d+) opus\/48000\/2/i)?.[1]
  if (!opus) return sdp
  const extra = ['stereo=1', 'sprop-stereo=1', ...(kbps ? [`maxaveragebitrate=${kbps * 1000}`] : [])]
  return sdp
    .split('\r\n')
    .map((line) => {
      if (!line.startsWith(`a=fmtp:${opus} `)) return line
      const have = new Set(line.slice(line.indexOf(' ') + 1).split(';').map((p) => p.split('=')[0]))
      const add = extra.filter((p) => !have.has(p.split('=')[0]))
      return add.length ? `${line};${add.join(';')}` : line
    })
    .join('\r\n')
}

// Chrome reads start/min/max bitrate hints from the video codecs' fmtp lines
// (other browsers ignore them). RTX lines (apt=…) are left alone.
function withQualityHints(sdp, q) {
  const hint = `x-google-start-bitrate=${q.startKbps};x-google-min-bitrate=${Math.round(q.startKbps / 3)};x-google-max-bitrate=${q.maxBitrate / 1000}`
  let inVideo = false
  const video = sdp
    .split('\r\n')
    .map((line) => {
      if (line.startsWith('m=')) inVideo = line.startsWith('m=video')
      return inVideo && line.startsWith('a=fmtp:') && !line.includes('apt=') ? `${line};${hint}` : line
    })
    .join('\r\n')
  return withStereoOpus(video, q.audioKbps)
}

/**
 * Publish `stream` as the Kino programme. `onEnded` fires when sharing stops for any reason.
 * Returns `{ stop, stats }`; `stats()` reports what is actually being sent.
 */
export async function publish(stream, onEnded = () => {}, { qualitaet = 'hoch', inhalt = 'film' } = {}) {
  const q = QUALITAET[qualitaet]
  const mode = INHALT[inhalt]
  const pc = new RTCPeerConnection({ iceServers: ICE })
  for (const track of stream.getTracks()) {
    const transceiver = pc.addTransceiver(track, { direction: 'sendonly', streams: [stream] })
    if (track.kind === 'audio') {
      const params = transceiver.sender.getParameters()
      params.encodings = [{ maxBitrate: q.audioKbps * 1000 }]
      await transceiver.sender.setParameters(params).catch(() => {})
      continue
    }
    preferCodecs(transceiver)
    const height = track.getSettings().height || q.height
    const params = transceiver.sender.getParameters()
    params.encodings = [
      { maxBitrate: q.maxBitrate, maxFramerate: mode.fps, scaleResolutionDownBy: Math.max(1, height / q.height) },
    ]
    params.degradationPreference = mode.degradation
    await transceiver.sender.setParameters(params).catch(() => {})
  }
  let location = null
  let ended = false
  const end = () => {
    if (ended) return
    ended = true
    hangUp(location)
    pc.close()
    stream.getTracks().forEach((t) => t.stop())
    onEnded()
  }
  // The browser's own "Stop sharing" button ends the track.
  stream.getVideoTracks()[0]?.addEventListener('ended', end)
  pc.onconnectionstatechange = () => ['failed', 'closed'].includes(pc.connectionState) && end()
  try {
    location = await negotiate(pc, '/api/kino/whip', (sdp) => withQualityHints(sdp, q))
  } catch (e) {
    end()
    throw e
  }

  let last = null
  async function stats() {
    const all = [...(await pc.getStats()).values()]
    const rtp = all.find((s) => s.type === 'outbound-rtp' && s.kind === 'video')
    if (!rtp) return null
    const audio = all.find((s) => s.type === 'outbound-rtp' && s.kind === 'audio')
    const now = { t: performance.now(), bytes: rtp.bytesSent, audioBytes: audio?.bytesSent ?? 0 }
    const rate = (key) => (last ? Math.round(((now[key] - last[key]) * 8) / (now.t - last.t)) : null)
    const kbps = rate('bytes')
    const tonKbps = audio ? rate('audioBytes') : null
    last = now
    return {
      breite: rtp.frameWidth,
      hoehe: rtp.frameHeight,
      fps: Math.round(rtp.framesPerSecond || 0),
      kbps,
      codec: all.find((s) => s.id === rtp.codecId)?.mimeType?.replace('video/', ''),
      grenze: rtp.qualityLimitationReason, // none | cpu | bandwidth | other
      tonKbps,
      stereo: /stereo=1/.test(pc.localDescription?.sdp ?? ''),
    }
  }
  return { stop: end, stats }
}
for (const c of Object.values(INHALT)) Object.defineProperty(c, 'label', { get: () => t(`kino.inhalt.${c.key}`) })
