/**
 * A small seeded random generator (mulberry32): the same seed gives the same
 * numbers on every device – that's how a shared case opening shows everyone
 * the same strip.
 */
export function zufall(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
