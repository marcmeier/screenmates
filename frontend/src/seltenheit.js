// Rarity colours of the case, after Counter-Strike: the less likely a film, the rarer it looks.
export const SELTENHEIT = [
  { ab: 0.5, name: 'Standard', farbe: '#4b69ff' },
  { ab: 0.3, name: 'Limitiert', farbe: '#8847ff' },
  { ab: 0.18, name: 'Geheim', farbe: '#d32ce6' },
  { ab: 0.08, name: 'Verdeckt', farbe: '#eb4b4b' },
  { ab: 0, name: '★ Legendär', farbe: '#e4ae39' },
]

export const seltenheitFuer = (chance) => SELTENHEIT.find((s) => chance >= s.ab)
