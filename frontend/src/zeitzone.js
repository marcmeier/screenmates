// The group's wall-clock time (a server setting, see backend/app/zeitzone.py): "20:00" means 20:00
// where the group lives, on every device – also on a phone that is travelling.
let zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

export const zeitzone = () => zone

export function zeitzoneSetzen(z) {
  if (z) zone = z
}

/** "Europe/Berlin" -> "Berlin", "America/New_York" -> "New York": for "(Berlin time)". */
export const zeitzoneOrt = () => zone.split('/').at(-1).replaceAll('_', ' ')
