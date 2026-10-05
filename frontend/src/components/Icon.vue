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
  profil: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9v-1a7 7 0 0 1 14 0v1',
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
  kino: 'M3 5h18v12H3zM8 21h8M12 17v4M10 8.5v5l4.5-2.5z',
  ton: 'M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11',
  stumm: 'M4 9h4l5-4v14l-5-4H4zM17 9l5 6M22 9l-5 6',
  vollbild: 'M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5',
  kopieren: 'M8 8h12v12H8zM4 16V4h12',
  veto: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM5.6 5.6l12.8 12.8',
  play: 'M8 5v14l11-7z',
  extern: 'M14 4h6v6M20 4l-9 9M18 14v6H4V6h6',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10',
  kiste: 'M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8',
  pokal: 'M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 20h8M10 17h4',
  kalender: 'M4 6h16v14H4zM4 10h16M8 3v5M16 3v5',
  teilen: 'M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm12 7a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4',
  download: 'M12 4v11M7 10l5 5 5-5M5 20h14',
  erinnerung: 'M12 7v5l3 2M3.5 12a8.5 8.5 0 1 0 2.5-6M3 4v4h4',
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
