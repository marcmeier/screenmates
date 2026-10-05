<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { navigate, useRoute } from '../../composables/useRoute'
import { FILME, TITEL, n, sterne, stunden } from '../../rueckblick'
import Icon from '../Icon.vue'
import Poster from '../Poster.vue'
import UserAvatar from '../UserAvatar.vue'

// The group's film year in numbers – as an overview, and as a story to tap through.
const RueckblickStory = defineAsyncComponent(() => import('./RueckblickStory.vue'))
const app = useApp()
const ui = useUi()
const route = useRoute()
const jahre = ref(null)
const daten = ref(null)
const story = ref(false)

const jahr = computed(() => {
  const gewuenscht = Number(route.value.id)
  return jahre.value?.includes(gewuenscht) ? gewuenscht : jahre.value?.[0]
})

onMounted(async () => (jahre.value = (await api.get('/api/rueckblick')).jahre))
watch(jahr, async (j) => (daten.value = j ? await api.get(`/api/rueckblick/${j}`) : null), { immediate: true })
watch(() => ui.changes, async () => jahr.value && (daten.value = await api.get(`/api/rueckblick/${jahr.value}`)))

const name = (id) => app.userById(id)?.name ?? 'Jemand'
const kacheln = computed(() => {
  const d = daten.value
  if (!d?.filme) return []
  return [
    { wert: n(d.filme), text: d.filme === 1 ? 'Film' : 'Filme' },
    { wert: n(d.abende), text: d.abende === 1 ? 'Filmabend' : 'Filmabende' },
    { wert: n(stunden(d.minuten)), text: 'Stunden Film' },
    { wert: n(d.leute), text: d.leute === 1 ? 'Person dabei' : 'Leute dabei' },
    { wert: n(d.bewertungen), text: 'Bewertungen', klein: d.schnitt ? `Ø ${sterne(d.schnitt)}` : '' },
    { wert: n(d.kommentare), text: 'Kommentare', klein: d.herzen ? `${n(d.herzen)} Herzen` : '' },
    { wert: n(d.serie), text: d.serie === 1 ? 'Woche am Stück' : 'Wochen am Stück' },
    { wert: n(d.kisten), text: d.kisten === 1 ? 'Kiste geöffnet' : 'Kisten geöffnet' },
  ]
})
const filme = computed(() => FILME.filter((f) => daten.value?.[f.key]))
const titel = computed(() => TITEL.filter((t) => daten.value?.titel[t.key]))
const maxGenre = computed(() => Math.max(1, ...(daten.value?.genres ?? []).map((g) => g.anzahl)))
</script>

<template>
  <div class="rueckblick">
    <div v-if="jahre === null" class="skeleton" style="height: 220px"></div>
    <div v-else-if="!jahre.length" class="empty">
      <strong>Noch nichts zurückzublicken</strong>
      Sobald ihr Filme als gesehen eintragt, entsteht hier euer Filmjahr.
    </div>
    <template v-else>
      <nav v-if="jahre.length > 1" class="jahre" aria-label="Jahr">
        <button v-for="j in jahre" :key="j" class="chip" :class="{ on: j === jahr }" @click="navigate('sammlung', 'rueckblick', j)">{{ j }}</button>
      </nav>

      <div v-if="!daten" class="skeleton" style="height: 220px"></div>
      <template v-else-if="daten.filme">
        <header class="hero">
          <div>
            <span class="vorzeile">{{ app.gruppe?.name }} · Rückblick</span>
            <h2>Euer Filmjahr {{ daten.jahr }}</h2>
            <p class="muted">
              Am liebsten {{ daten.wochentag.name }}s, am meisten im {{ daten.monat.name }}<template v-if="daten.jahrzehnt">,
                und am liebsten Filme aus den {{ String(daten.jahrzehnt.jahrzehnt).slice(2) }}ern</template>.
            </p>
          </div>
          <button class="primary" @click="story = true"><Icon name="play" :size="16" /> Als Story ansehen</button>
        </header>

        <div class="kacheln">
          <div v-for="k in kacheln" :key="k.text" class="kachel">
            <strong>{{ k.wert }}</strong>
            <span>{{ k.text }}</span>
            <small v-if="k.klein" class="muted">{{ k.klein }}</small>
          </div>
        </div>

        <div class="spalten">
          <section class="panel">
            <h3>Genres</h3>
            <ol class="genres">
              <li v-for="g in daten.genres" :key="g.name">
                <span class="name">{{ g.name }}</span>
                <span class="balken"><span :style="{ width: `${(100 * g.anzahl) / maxGenre}%` }"></span></span>
                <span class="zahl">{{ g.anzahl }}</span>
              </li>
            </ol>
          </section>
          <section v-if="titel.length" class="panel">
            <h3>Auszeichnungen</h3>
            <ul class="titel">
              <li v-for="t in titel" :key="t.key">
                <span class="emoji" aria-hidden="true">{{ t.emoji }}</span>
                <UserAvatar :user-id="daten.titel[t.key].user_id" link />
                <div>
                  <strong>{{ t.name }}</strong>
                  <span class="muted">{{ name(daten.titel[t.key].user_id) }} · {{ t.einheit(daten.titel[t.key].wert) }}</span>
                </div>
              </li>
            </ul>
          </section>
        </div>

        <h3 class="section-title">Filme des Jahres</h3>
        <div class="filme">
          <button v-for="f in filme" :key="f.key" class="film" @click="ui.open(daten[f.key].movie)">
            <span class="plakat"><Poster :movie="daten[f.key].movie" /></span>
            <span class="was">{{ f.name }}</span>
            <strong>{{ daten[f.key].movie.title }}</strong>
            <span class="muted">{{ f.text(daten[f.key], name) }}</span>
          </button>
        </div>
      </template>
      <div v-else class="empty"><strong>{{ jahr }}</strong> In diesem Jahr habt ihr nichts eingetragen.</div>
    </template>

    <RueckblickStory v-if="story && daten?.filme" :daten="daten" @close="story = false" />
  </div>
</template>

<style scoped>
.jahre { display: flex; gap: 0.4rem; margin-bottom: 1rem; flex-wrap: wrap; }
.hero {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  padding: 1.6rem 1.5rem; border-radius: 14px; margin-bottom: 1rem; border: 1px solid var(--line);
  background:
    radial-gradient(90% 140% at 0% 0%, color-mix(in srgb, var(--accent) 35%, transparent), transparent 60%),
    radial-gradient(80% 120% at 100% 100%, color-mix(in srgb, var(--gold) 22%, transparent), transparent 60%),
    var(--bg-soft);
}
.vorzeile { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 700; }
.hero h2 { margin: 0.2rem 0 0.4rem; font-size: clamp(1.6rem, 4vw, 2.4rem); letter-spacing: -0.03em; }
.hero p { margin: 0; max-width: 60ch; }
.kacheln { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.7rem; margin-bottom: 1.2rem; }
.kachel { background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1rem; display: flex; flex-direction: column; gap: 0.1rem; }
.kachel strong { font-size: 1.9rem; letter-spacing: -0.03em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.kachel span { font-size: 0.85rem; }
.kachel small { font-size: 0.75rem; }
.spalten { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
h3 { margin: 0 0 0.8rem; font-size: 0.95rem; }
.genres { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
.genres li { display: grid; grid-template-columns: 8rem 1fr 2rem; align-items: center; gap: 0.6rem; font-size: 0.88rem; }
.genres .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.balken { height: 10px; background: var(--bg-raised); border-radius: 5px; overflow: hidden; }
.balken span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--gold)); border-radius: 5px; }
.genres .zahl { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }
.titel { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.6rem; }
.titel li { display: flex; align-items: center; gap: 0.6rem; }
.titel .emoji { font-size: 1.3rem; width: 1.6rem; text-align: center; }
.titel div { display: flex; flex-direction: column; font-size: 0.88rem; min-width: 0; }
.titel .muted { font-size: 0.8rem; }
.filme { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem; }
.film {
  display: flex; flex-direction: column; align-items: flex-start; gap: 0.15rem; padding: 0; border: none; background: none;
  text-align: left; font-size: 0.85rem;
}
.film:hover { background: none; }
.film:hover .plakat { box-shadow: 0 0 0 2px var(--accent); }
.plakat { width: 100%; aspect-ratio: 2 / 3; border-radius: 9px; overflow: hidden; background: var(--bg-raised); margin-bottom: 0.35rem; transition: box-shadow 0.15s; }
.was { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em; color: var(--accent); font-weight: 700; }
.film strong { font-size: 0.92rem; line-height: 1.2; }
.film .muted { font-size: 0.78rem; }
</style>