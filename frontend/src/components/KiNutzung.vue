<script setup>
import { locale, t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { vorWann } from '../format'

// How much the KI search is used and what it cost (as far as the provider reports it).
const app = useApp()
const daten = ref(null)
const zeitraum = ref('30_tage')
const ZEITRAEUME = { heute: t('allg.heute'), '7_tage': t('kinutzung.7Tage'), '30_tage': t('kinutzung.30Tage'), gesamt: t('kinutzung.gesamt') }

onMounted(async () => (daten.value = await api.get('/api/admin/ki-nutzung')))
const s = computed(() => daten.value?.summen[zeitraum.value])
const zahl = (n) => (n ?? 0).toLocaleString(locale())
const dollar = (k) =>
  k == null ? '–' : k.toLocaleString(locale(), { style: 'currency', currency: 'USD', maximumFractionDigits: k < 1 ? 4 : 2 })
const name = (id) => app.userById(id)?.name || t('kinutzung.geloescht')
</script>

<template>
  <section class="panel">
    <h2>{{ $t('kinutzung.kiSuche') }}</h2>
    <template v-if="daten">
      <p class="muted">
        <template v-if="daten.aktiv">{{ $t('kinutzung.modell') }} <code>{{ daten.modell }}</code> über {{ daten.anbieter === 'openrouter' ? 'OpenRouter' : 'Anthropic' }}.</template>
        <template v-else>{{ $t('kinutzung.nichtEingerichtet') }}<code>LLM_API_KEY</code> {{ $t('kinutzung.fehlt') }}</template>
      </p>
      <div class="zeitraum" role="group" :aria-label="$t('kinutzung.zeitraum')">
        <button v-for="(label, k) in ZEITRAEUME" :key="k" class="small" :class="{ primary: zeitraum === k }" @click="zeitraum = k">{{ label }}</button>
      </div>
      <div class="kacheln">
        <div><strong>{{ zahl(s.anfragen) }}</strong><span class="muted">{{ $t('kinutzung.anfragen') }}<template v-if="s.fehler"> {{ $t('kinutzung.fehlerFehlgeschlagen', { fehler: s.fehler }) }}</template></span></div>
        <div><strong>{{ zahl(s.tokens_ein + s.tokens_aus) }}</strong><span class="muted">{{ $t('kinutzung.tokensXReinX2', { x: zahl(s.tokens_ein), x2: zahl(s.tokens_aus) }) }}</span></div>
        <div>
          <strong>{{ dollar(s.kosten) }}</strong>
          <span class="muted">{{ $t('kinutzung.kosten') }}<template v-if="s.ohne_kosten && s.anfragen"> {{ $t('kinutzung.ohneKostenOhnePreisangabe', { ohne_kosten: s.ohne_kosten }) }}</template></span>
        </div>
      </div>

      <template v-if="daten.pro_person.length">
        <h3>{{ $t('kinutzung.proPersonGesamt') }}</h3>
        <table>
          <thead><tr><th>{{ $t('kinutzung.wer') }}</th><th>{{ $t('kinutzung.anfragen2') }}</th><th>{{ $t('kinutzung.tokens') }}</th><th>{{ $t('kinutzung.kosten2') }}</th></tr></thead>
          <tbody>
            <tr v-for="p in daten.pro_person" :key="p.user_id ?? 'x'">
              <td>{{ name(p.user_id) }}</td><td>{{ zahl(p.anfragen) }}</td><td>{{ zahl(p.tokens_ein + p.tokens_aus) }}</td><td>{{ dollar(p.kosten) }}</td>
            </tr>
          </tbody>
        </table>

        <h3>{{ $t('kinutzung.letzteAnfragen') }}</h3>
        <table>
          <thead><tr><th>{{ $t('kinutzung.wann') }}</th><th>{{ $t('kinutzung.wer2') }}</th><th>{{ $t('kinutzung.tokens2') }}</th><th>{{ $t('kinutzung.kosten3') }}</th></tr></thead>
          <tbody>
            <tr v-for="(a, i) in daten.letzte" :key="i" :class="{ fehler: !a.ok }" :title="a.fehler || a.modell">
              <td>{{ vorWann(a.at) }}</td><td>{{ name(a.user_id) }}</td>
              <td>{{ a.ok ? zahl(a.tokens_ein + a.tokens_aus) : $t('kinutzung.fehler') }}</td><td>{{ dollar(a.kosten) }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <p v-else class="muted">{{ $t('kinutzung.nochKeineAnfragen') }}</p>
      <p class="muted klein">{{ $t('kinutzung.kostenMeldetNurOpenrouter') }}</p>
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
