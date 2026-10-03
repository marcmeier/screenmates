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

async function negotiate(pc, url) {
  await pc.setLocalDescription(await pc.createOffer())
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

/** Ask the user what to share. Throws if they cancel. */
export async function pickScreen({ audio = true } = {}) {
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: { frameRate: { ideal: 30 }, width: { ideal: 1920 }, height: { ideal: 1080 } },
    audio,
  })
  const [video] = stream.getVideoTracks()
  if (video) video.contentHint = 'motion' // films and games: keep motion smooth over sharp text
  return stream
}

/** Publish `stream` as the Kino programme. `onEnded` fires when sharing stops for any reason. */
export async function publish(stream, onEnded = () => {}) {
  const pc = new RTCPeerConnection({ iceServers: ICE })
  for (const track of stream.getTracks()) {
    const sender = pc.addTransceiver(track, { direction: 'sendonly', streams: [stream] }).sender
    if (track.kind === 'video') {
      const params = sender.getParameters()
      params.encodings = [{ maxBitrate: 6_000_000, maxFramerate: 30 }]
      params.degradationPreference = 'maintain-framerate'
      await sender.setParameters(params).catch(() => {})
    }
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
    location = await negotiate(pc, '/api/kino/whip')
  } catch (e) {
    end()
    throw e
  }
  return { stop: end }
}
