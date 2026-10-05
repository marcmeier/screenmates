<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { vorWann } from '../format'

// How much the KI search is used and what it cost (as far as the provider reports it).
const app = useApp()
const daten = ref(null)
const zeitraum = ref('30_tage')
const ZEITRAEUME = { heute: 'Heute', '7_tage': '7 Tage', '30_tage': '30 Tage', gesamt: 'Gesamt' }

onMounted(async () => (daten.value = await api.get('/api/admin/ki-nutzung')))
const s = computed(() => daten.value?.summen[zeitraum.value])
const zahl = (n) => (n ?? 0).toLocaleString('de-DE')
const dollar = (k) =>
  k == null ? '–' : k.toLocaleString('de-DE', { style: 'currency', currency: 'USD', maximumFractionDigits: k < 1 ? 4 : 2 })
const name = (id) => app.userById(id)?.name || 'Gelöscht'
</script>

<template>
  <section class="panel">
    <h2>KI-Suche</h2>
    <template v-if="daten">
      <p class="muted">
        <template v-if="daten.aktiv">Modell <code>{{ daten.modell }}</code> über {{ daten.anbieter === 'openrouter' ? 'OpenRouter' : 'Anthropic' }}.</template>
        <template v-else>Nicht eingerichtet (<code>LLM_API_KEY</code> fehlt).</template>
      </p>
      <div class="zeitraum" role="group" aria-label="Zeitraum">
        <button v-for="(label, k) in ZEITRAEUME" :key="k" class="small" :class="{ primary: zeitraum === k }" @click="zeitraum = k">{{ label }}</button>
      </div>
      <div class="kacheln">
        <div><strong>{{ zahl(s.anfragen) }}</strong><span class="muted">Anfragen<template v-if="s.fehler"> · {{ s.fehler }} fehlgeschlagen</template></span></div>
        <div><strong>{{ zahl(s.tokens_ein + s.tokens_aus) }}</strong><span class="muted">Tokens ({{ zahl(s.tokens_ein) }} rein · {{ zahl(s.tokens_aus) }} raus)</span></div>
        <div>
          <strong>{{ dollar(s.kosten) }}</strong>
          <span class="muted">Kosten<template v-if="s.ohne_kosten && s.anfragen"> · {{ s.ohne_kosten }} ohne Preisangabe</template></span>
        </div>
      </div>

      <template v-if="daten.pro_person.length">
        <h3>Pro Person (gesamt)</h3>
        <table>
          <thead><tr><th>Wer</th><th>Anfragen</th><th>Tokens</th><th>Kosten</th></tr></thead>
          <tbody>
            <tr v-for="p in daten.pro_person" :key="p.user_id ?? 'x'">
              <td>{{ name(p.user_id) }}</td><td>{{ zahl(p.anfragen) }}</td><td>{{ zahl(p.tokens_ein + p.tokens_aus) }}</td><td>{{ dollar(p.kosten) }}</td>
            </tr>
          </tbody>
        </table>

        <h3>Letzte Anfragen</h3>
        <table>
          <thead><tr><th>Wann</th><th>Wer</th><th>Tokens</th><th>Kosten</th></tr></thead>
          <tbody>
            <tr v-for="(a, i) in daten.letzte" :key="i" :class="{ fehler: !a.ok }" :title="a.fehler || a.modell">
              <td>{{ vorWann(a.at) }}</td><td>{{ name(a.user_id) }}</td>
              <td>{{ a.ok ? zahl(a.tokens_ein + a.tokens_aus) : 'Fehler' }}</td><td>{{ dollar(a.kosten) }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <p v-else class="muted">Noch keine Anfragen.</p>
      <p class="muted klein">Kosten meldet nur OpenRouter (in US-Dollar). Anfragen von vor diesem Update sind nicht erfasst.</p>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.6rem; font-size: 1.1rem; }
h3 { margin: 1.3rem 0 0.4rem; font-size: 0.95rem; }
p { font-size: 0.9rem; margin: 0 0 0.8rem; }
.zeitraum { display: flex; gap: 0.3rem; flex-wrap: wrap; margin-bottom: 0.8rem; }
.kacheln { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 0.6rem; }
.kacheln > div { display: flex; flex-direction: column; gap: 0.15rem; padding: 0.7rem 0.8rem; border: 1px solid var(--line); border-radius: var(--radius); }
.kacheln strong { font-size: 1.35rem; font-variant-numeric: tabular-nums; }
.kacheln span { font-size: 0.78rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { text-align: left; color: var(--muted); font-weight: 600; padding: 0.3rem 0.4rem; border-bottom: 1px solid var(--line); }
td { padding: 0.3rem 0.4rem; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
tr.fehler td { color: var(--danger, #e66); }
.klein { font-size: 0.78rem; margin-top: 0.9rem; }
</style>
