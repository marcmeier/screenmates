import { t } from './i18n'

// Rarity colours of the case, after Counter-Strike: the less likely a film, the rarer it looks.
export const SELTENHEIT = [
  { ab: 0.5, key: 'standard', farbe: '#4b69ff' },
  { ab: 0.3, key: 'limitiert', farbe: '#8847ff' },
  { ab: 0.18, key: 'geheim', farbe: '#d32ce6' },
  { ab: 0.08, key: 'verdeckt', farbe: '#eb4b4b' },
  { ab: 0, key: 'legendaer', farbe: '#e4ae39' },
].map((s) => Object.defineProperty(s, 'name', { get: () => t(`seltenheit.${s.key}`) }))

export const seltenheitFuer = (chance) => SELTENHEIT.find((s) => chance >= s.ab)
