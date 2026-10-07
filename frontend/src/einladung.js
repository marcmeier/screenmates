// The invitation for the next movie night: a share text and a 1080×1350 card
// (portrait, how messengers show pictures best), drawn on a canvas in the browser.
import { datumFmt } from './format'
import { t } from './i18n'
import { zeitzone } from './zeitzone'

export function terminText(termin) {
  if (!termin?.termin) return null
  const d = new Date(termin.termin)
  const tag = datumFmt({ weekday: 'long', day: 'numeric', month: 'long', timeZone: zeitzone() }).format(d)
  const zeit = datumFmt({ hour: '2-digit', minute: '2-digit', timeZone: zeitzone() }).format(d)
  return { tag, zeit: t('zeit.uhr', { zeit }), notiz: termin.notiz }
}

export function link() {
  return `${location.origin}${location.pathname}#/abend`
}

/** Plain text for messengers: date, the films up for the vote, who's in, the link. */
export function einladungsText({ termin, filme, dabei }) {
  const tt = terminText(termin)
  const zeilen = [
    tt
      ? t('einladung.text.am', { tag: tt.tag, zeit: tt.zeit, notiz: tt.notiz ? ` (${tt.notiz})` : '' })
      : t('einladung.text.folgt'),
  ]
  if (filme.length) zeilen.push(t('einladung.text.zurWahl', { filme: filme.map((m) => m.title).join(', ') }))
  if (dabei.length) zeilen.push(t('einladung.text.dabei', { namen: dabei.map((u) => u.name).join(', ') }))
  zeilen.push(t('einladung.text.frage', { link: link() }))
  return zeilen.join('\n')
}

const W = 1080
const H = 1350
const FONT = "'Inter Variable', system-ui, sans-serif"

function bild(url) {
  return new Promise((resolve) => {
    if (!url) return resolve(null)
    const img = new Image()
    img.crossOrigin = 'anonymous' // without CORS the canvas can't be exported
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    // TMDB only sends the CORS header when asked, and the page's own <img> already
    // cached the poster without it. A URL of our own skips that cached copy.
    img.src = `${url}${url.includes('?') ? '&' : '?'}karte`
  })
}

function rund(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
}

function kuerzen(ctx, text, max) {
  if (ctx.measureText(text).width <= max) return text
  while (text.length > 1 && ctx.measureText(`${text}…`).width > max) text = text.slice(0, -1)
  return `${text.trimEnd()}…`
}

/** Draw the card; resolves to a PNG blob. */
export async function einladungsBild({ termin, filme, dabei }) {
  await Promise.all([document.fonts.load(`800 40px ${FONT}`), document.fonts.load(`500 40px ${FONT}`)]).catch(() => {})
  const poster = await Promise.all(filme.slice(0, 3).map((m) => bild(m.poster_url)))

  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const ctx = c.getContext('2d')

  // Background: near black with a red glow from the top.
  ctx.fillStyle = '#0a0a0c'
  ctx.fillRect(0, 0, W, H)
  const glow = ctx.createRadialGradient(W / 2, -200, 50, W / 2, -200, 1100)
  glow.addColorStop(0, 'rgba(229, 9, 20, 0.55)')
  glow.addColorStop(1, 'rgba(229, 9, 20, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, H)

  const x0 = 80
  ctx.textBaseline = 'alphabetic'
  ctx.font = `800 44px ${FONT}`
  ctx.fillStyle = '#ececf1'
  ctx.fillText('screen', x0, 120)
  ctx.fillStyle = '#e50914'
  ctx.fillText('mates', x0 + ctx.measureText('screen').width, 120)

  ctx.font = `800 30px ${FONT}`
  ctx.fillStyle = '#e50914'
  ctx.letterSpacing = '6px'
  ctx.fillText(t('einladung.karte.filmabend'), x0, 230)
  ctx.letterSpacing = '0px'

  const tt = terminText(termin)
  ctx.fillStyle = '#ffffff'
  ctx.font = `800 76px ${FONT}`
  ctx.fillText(kuerzen(ctx, tt ? tt.tag : t('einladung.karte.terminFolgt'), W - 2 * x0), x0, 320)
  ctx.font = `500 44px ${FONT}`
  ctx.fillStyle = '#b9b9c6'
  const unter = tt ? [tt.zeit, tt.notiz].filter(Boolean).join(' · ') : t('einladung.karte.bescheid')
  ctx.fillText(kuerzen(ctx, unter, W - 2 * x0), x0, 385)

  // The films up for the vote.
  const top = 470
  if (filme.length) {
    ctx.font = `700 28px ${FONT}`
    ctx.fillStyle = '#8b8b99'
    ctx.fillText(t('einladung.karte.zurWahl'), x0, top)
    const n = Math.min(3, filme.length)
    const gap = 36
    const pw = (W - 2 * x0 - gap * 2) / 3
    const ph = pw * 1.5
    const start = x0 + ((3 - n) * (pw + gap)) / 2
    filme.slice(0, 3).forEach((m, i) => {
      const x = start + i * (pw + gap)
      const y = top + 30
      ctx.save()
      rund(ctx, x, y, pw, ph, 18)
      ctx.clip()
      if (poster[i]) ctx.drawImage(poster[i], x, y, pw, ph)
      else {
        ctx.fillStyle = '#1b1b22'
        ctx.fillRect(x, y, pw, ph)
      }
      ctx.restore()
      ctx.font = `600 28px ${FONT}`
      ctx.fillStyle = '#ececf1'
      ctx.fillText(kuerzen(ctx, m.title, pw), x, y + ph + 44)
    })
  } else {
    ctx.font = `500 40px ${FONT}`
    ctx.fillStyle = '#b9b9c6'
    ctx.fillText(t('einladung.karte.keine1'), x0, top + 160)
    ctx.fillText(t('einladung.karte.keine2'), x0, top + 215)
  }

  // Who's in, with their colours.
  const yDabei = 1110
  ctx.font = `700 28px ${FONT}`
  ctx.fillStyle = '#8b8b99'
  ctx.fillText(t('einladung.karte.dabei'), x0, yDabei)
  let x = x0
  ctx.font = `600 34px ${FONT}`
  if (!dabei.length) {
    ctx.fillStyle = '#b9b9c6'
    ctx.fillText(t('einladung.karte.erste'), x0, yDabei + 56)
  }
  for (const u of dabei) {
    const breite = ctx.measureText(u.name).width
    if (x + breite + 40 > W - x0) {
      ctx.fillStyle = '#b9b9c6'
      ctx.fillText('…', x, yDabei + 56)
      break
    }
    ctx.fillStyle = u.color || '#555'
    ctx.beginPath()
    ctx.arc(x + 12, yDabei + 44, 12, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#ececf1'
    ctx.fillText(u.name, x + 34, yDabei + 56)
    x += breite + 70
  }

  // Footer with the call to action.
  ctx.fillStyle = '#e50914'
  rund(ctx, x0, H - 140, W - 2 * x0, 76, 38)
  ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.font = `800 34px ${FONT}`
  ctx.textAlign = 'center'
  ctx.fillText(t('einladung.karte.frage'), W / 2, H - 90)
  ctx.textAlign = 'start'

  return new Promise((resolve) => c.toBlob(resolve, 'image/png'))
}
