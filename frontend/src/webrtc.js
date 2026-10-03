// WHIP (send) and WHEP (watch) over plain fetch + RTCPeerConnection.
// Signalling goes through screenmates (/api/kino/...), media straight to MediaMTX.

const ICE = [{ urls: 'stun:stun.l.google.com:19302' }]

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
    const err = new Error((await res.json().catch(() => null))?.detail || `Verbindung fehlgeschlagen (${res.status})`)
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
      stream.addTrack(e.track)
      if (video.srcObject !== stream) video.srcObject = stream
    }
    pc.onconnectionstatechange = () => {
      if (pc?.connectionState === 'connected') onState('live')
      if (['failed', 'disconnected', 'closed'].includes(pc?.connectionState)) schedule()
    }
    try {
      location = await negotiate(pc, '/api/kino/whep')
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
  hoch: { label: 'Hoch – 1080p', height: 1080, maxBitrate: 8_000_000, startKbps: 4000 },
  mittel: { label: 'Mittel – 720p', height: 720, maxBitrate: 4_000_000, startKbps: 2500 },
  sparsam: { label: 'Sparsam – 480p', height: 480, maxBitrate: 2_000_000, startKbps: 1200 },
}
export const INHALT = {
  film: { label: 'Film – Schärfe zuerst', fps: 30, degradation: 'maintain-resolution' },
  spiel: { label: 'Spiel – flüssig, bis 60 fps', fps: 60, degradation: 'maintain-framerate' },
}

/** Ask the user what to share. Throws if they cancel. */
export async function pickScreen({ audio = true, inhalt = 'film' } = {}) {
  const fps = INHALT[inhalt].fps
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: { frameRate: { ideal: fps, max: fps }, width: { ideal: 1920 }, height: { ideal: 1080 } },
    audio,
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

// Chrome reads start/min/max bitrate hints from the video codecs' fmtp lines
// (other browsers ignore them). RTX lines (apt=…) are left alone.
function withBitrateHints(sdp, q) {
  const hint = `x-google-start-bitrate=${q.startKbps};x-google-min-bitrate=${Math.round(q.startKbps / 3)};x-google-max-bitrate=${q.maxBitrate / 1000}`
  let inVideo = false
  return sdp
    .split('\r\n')
    .map((line) => {
      if (line.startsWith('m=')) inVideo = line.startsWith('m=video')
      return inVideo && line.startsWith('a=fmtp:') && !line.includes('apt=') ? `${line};${hint}` : line
    })
    .join('\r\n')
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
    if (track.kind !== 'video') continue
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
    location = await negotiate(pc, '/api/kino/whip', (sdp) => withBitrateHints(sdp, q))
  } catch (e) {
    end()
    throw e
  }

  let last = null
  async function stats() {
    const all = [...(await pc.getStats()).values()]
    const rtp = all.find((s) => s.type === 'outbound-rtp' && s.kind === 'video')
    if (!rtp) return null
    const now = { t: performance.now(), bytes: rtp.bytesSent }
    const kbps = last ? Math.round(((now.bytes - last.bytes) * 8) / (now.t - last.t)) : null
    last = now
    return {
      breite: rtp.frameWidth,
      hoehe: rtp.frameHeight,
      fps: Math.round(rtp.framesPerSecond || 0),
      kbps,
      codec: all.find((s) => s.id === rtp.codecId)?.mimeType?.replace('video/', ''),
      grenze: rtp.qualityLimitationReason, // none | cpu | bandwidth | other
    }
  }
  return { stop: end, stats }
}
