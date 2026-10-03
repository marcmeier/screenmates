<script setup>
// A handful of stroke icons (24px grid), so we don't pull in an icon library.
defineProps({ name: { type: String, required: true }, size: { type: [Number, String], default: 18 } })

const PATHS = {
  abend: 'M3 7h18v12H3zM3 7l3-4h12l3 4M10 11v4l4-2z',
  entdecken: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm3.5 5.5-2 5-5 2 2-5z',
  suche: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-4-4',
  merken: 'M6 3h12v18l-6-4-6 4z',
  gesehen: 'M4 12l5 5L20 6',
  wuensche: 'M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z',
  personen: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-6 10v-1a6 6 0 0 1 12 0v1M16 3.5a4 4 0 0 1 0 7.5M21 21v-1a6 6 0 0 0-4-5.6',
  ki: 'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 8v5m0-8.5v.5',
  verwaltung: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8-3 2-1-1-3-2 .3-1.5-1.5L18 5l-3-1-1 2h-2l-1-2-3 1 .3 2L6.8 8.5 5 8.2 4 11l2 1v2l-2 1 1 3 2-.3 1.5 1.5L8.2 20l3 1 1-2h2l1 2 3-1-.3-2 1.5-1.5 1.8.3 1-3-2-1z',
  plus: 'M12 5v14M5 12h14',
  x: 'M6 6l12 12M18 6 6 18',
  stern: 'M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z',
  herz: 'M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z',
  hand: 'M7 11V6a2 2 0 0 1 4 0v5m0-6a2 2 0 0 1 4 0v6m0-4a2 2 0 0 1 4 0v7a7 7 0 0 1-14 0v-3a2 2 0 0 1 4 0',
  schloss: 'M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4',
  rad: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 0v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4',
  antwort: 'M9 14 4 9l5-5M4 9h10a6 6 0 0 1 6 6v4',
  muell: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13',
  stift: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4',
  sync: 'M20 11a8 8 0 0 0-14.7-4M4 4v4h4M4 13a8 8 0 0 0 14.7 4M20 20v-4h-4',
  pfeil: 'M15 18l-6-6 6-6',
  filter: 'M4 5h16l-6 7v6l-4 2v-8z',
  sammlung: 'M4 8h16v12H4zM6 5h12M8 2h8',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10',
}
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name]" />
  </svg>
</template>
