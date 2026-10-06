// One Web Audio context for the whole app, unlocked by the first tap or key press.
//
// Safari (iPhone, iPad) only lets a context play if it was started *during* a user gesture.
// The case's sounds start later – after a server answer, or for viewers without any tap –
// so the context is made and resumed at the first interaction anywhere in the app and
// reused from then on. iOS also mutes Web Audio with the ring/silent switch unless the
// page says it plays media (navigator.audioSession, Safari 16.4+).

let kontext = null
// What iOS counts as a gesture that may start sound: the end of a touch or a click, not its start.
const GESTEN = ['touchend', 'click', 'keydown', 'pointerup']

export function audioKontext() {
  return kontext
}

function entsperren() {
  try {
    if (navigator.audioSession) navigator.audioSession.type = 'playback'
    kontext ??= new (window.AudioContext || window.webkitAudioContext)()
    kontext.resume?.()
    // A silent sound inside the gesture: what older iOS versions need to really unlock.
    const quelle = kontext.createBufferSource()
    quelle.buffer = kontext.createBuffer(1, 1, 22050)
    quelle.connect(kontext.destination)
    quelle.start(0)
  } catch {
    /* no Web Audio: the app simply stays silent */
  }
  if (kontext?.state === 'running') {
    for (const typ of GESTEN) window.removeEventListener(typ, entsperren, true)
  }
}

/** Listen for the first interaction (and keep trying until the context really runs). */
export function audioVorbereiten() {
  for (const typ of GESTEN) window.addEventListener(typ, entsperren, true)
}

/** From a click handler: make sure sound can play now (a tap is a gesture). */
export function audioJetzt() {
  entsperren()
  return kontext
}