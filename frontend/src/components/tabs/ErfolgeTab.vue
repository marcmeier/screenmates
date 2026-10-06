<script setup>
import Geschmack from '../Geschmack.vue'
import { computed, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { navigate, useRoute } from '../../composables/useRoute'
import { vorWann } from '../../format'
import ErfolgKachel from '../ErfolgKachel.vue'
import UserAvatar from '../UserAvatar.vue'

// Achievements: everyone's level and showcase (no ranking), the latest unlocks,
// your own progress – and a profile page per person (#/profil/person/<id>).
// Embedded on your profile page (which has its own heading), or someone else's profile.
defineProps({ eingebettet: { type: Boolean, default: false } })
const app = useApp()
const ui = useUi()
const route = useRoute()

const daten = ref(null)
const profil = ref(null)
const personId = computed(() => (route.value.sub === 'person' ? Number(route.value.id) : null))
const eigenes = computed(() => personId.value != null && personId.value === app.me?.id)

const katalog = computed(() => Object.fromEntries((daten.value?.katalog || []).map((d) => [d.key, d])))
const KATEGORIEN = ['Filmabend', 'Mitreden', 'Kino', 'Profil', 'Geheim']
const nachKategorie = computed(() =>
  KATEGORIEN.map((k) => ({ name: k, erfolge: (daten.value?.katalog || []).filter((d) => d.kategorie === k) })).filter(
    (k) => k.erfolge.length,
  ),
)
const ich = computed(() => daten.value?.ich)
const levelProzent = computed(() => {
  const i = ich.value
  if (!i) return 0
  return Math.round((100 * (i.punkte - i.level_ab)) / Math.max(1, i.naechstes_ab - i.level_ab))
})

async function laden() {
  daten.value = await api.get('/api/erfolge')
  profil.value = personId.value != null ? await api.get(`/api/erfolge/${personId.value}`) : null
}
watch(() => [route.value.sub, route.value.id, ui.changes], laden, { immediate: true })

const profilErfolge = computed(() => Object.fromEntries((profil.value?.freigeschaltet || []).map((e) => [e.key, e])))
const vitrine = computed(() => (profil.value?.vitrine || []).map((k) => profilErfolge.value[k]).filter(Boolean))

async function vitrineUmschalten(key) {
  const jetzt = profil.value.vitrine
  const neu = jetzt.includes(key) ? jetzt.filter((k) => k !== key) : [...jetzt, key]
  if (neu.length > 3) return ui.toast('In die Vitrine passen drei Erfolge – nimm erst einen heraus.')
  await api.put('/api/erfolge/vitrine', { keys: neu })
  await laden()
}

async function entziehen(e) {
  if (!confirm(`„${e.name}“ entziehen? Der Erfolg bleibt entzogen, bis ein Admin ihn zurückgibt.`)) return
  await api.patch(`/api/admin/erfolge/${personId.value}/${e.key}`, { entzogen: true })
  await app.refreshUsers()
  await laden()
  ui.toast('Erfolg entzogen')
}

const name = (id) => app.userById(id)?.name || 'Jemand'
</script>

<template>
  <div class="page">
    <!-- profile of one person -->
    <template v-if="personId != null">
      <a :href="eigenes ? '#/profil' : '#/profil'" class="back muted">← {{ eigenes ? 'Mein Profil' : 'Zu meinem Profil' }}</a>
      <section v-if="profil" class="panel kopf">
        <UserAvatar :user-id="personId" class="gross" />
        <div>
          <h1>{{ name(personId) }}</h1>
          <p class="muted">Level {{ profil.level }} · {{ profil.titel }} · {{ profil.freigeschaltet.length }} Erfolge</p>
        </div>
      </section>
      <Geschmack v-if="app.me" :user-id="personId" />

      <section v-if="profil" class="panel">
        <h2>Vitrine</h2>
        <div v-if="vitrine.length" class="vitrine">
          <div v-for="e in vitrine" :key="e.key" class="pokal" :class="`stufe-${e.stufe}`">
            <span class="medaille">{{ e.emoji }}</span>
            <strong>{{ e.name }}</strong>
            <small class="muted">{{ e.punkte }} P</small>
          </div>
        </div>
        <p v-else class="muted">
          {{ eigenes ? 'Noch leer. Mit ★ an einem Erfolg legst du ihn hier hinein – bis zu drei.' : 'Noch nichts ausgestellt.' }}
        </p>
      </section>

      <section v-if="profil" class="panel">
        <h2>Freigeschaltet</h2>
        <div v-if="profil.freigeschaltet.length" class="raster">
          <div v-for="e in profil.freigeschaltet" :key="e.key" class="mit-aktion">
            <ErfolgKachel
              :erfolg="{ ...e, selten: katalog[e.key]?.selten }"
              :am="e.am"
              :waehlbar="eigenes"
              :vitrine="profil.vitrine.includes(e.key)"
              @vitrine="vitrineUmschalten"
            />
            <button v-if="app.admin" class="ghost small danger" @click="entziehen(e)">Entziehen</button>
          </div>
        </div>
        <p v-else class="muted">Noch keine Erfolge – das kommt mit dem ersten Filmabend.</p>
      </section>
    </template>

    <!-- overview -->
    <template v-else>
      <header v-if="!eingebettet" class="page-head">
        <h1>Erfolge</h1>
        <p>Für Filmabende, Kritiken, Kino und alles, was die Gruppe zusammenbringt. Punkte gibt es nur für Erfolge – Masse allein bringt nichts.</p>
      </header>

      <section v-if="ich" class="panel stand">
        <UserAvatar :user="app.me" class="gross" />
        <div class="levelinfo">
          <div class="row">
            <strong class="lvl">Level {{ ich.level }}</strong>
            <span class="muted">{{ ich.titel }}</span>
            <span class="spacer"></span>
            <span class="score">{{ ich.punkte }} P</span>
          </div>
          <div class="levelbalken" :title="`${ich.punkte} von ${ich.naechstes_ab} Punkten für Level ${ich.level + 1}`">
            <span :style="{ width: `${levelProzent}%` }"></span>
          </div>
          <small class="muted">Noch {{ ich.naechstes_ab - ich.punkte }} P bis Level {{ ich.level + 1 }}</small>
        </div>
        <button class="small" @click="navigate('profil', 'person', app.me.id)">Meine Vitrine</button>
      </section>
      <Geschmack v-if="app.me && !personId" :user-id="app.me.id" />

      <section v-if="daten" class="panel">
        <h2>Die Gruppe</h2>
        <div class="gruppe">
          <a v-for="g in daten.gruppe" :key="g.user_id" :href="`#/profil/person/${g.user_id}`" class="mitglied">
            <UserAvatar :user-id="g.user_id" />
            <span class="wer">
              <strong>{{ name(g.user_id) }}</strong>
              <small class="muted">Level {{ g.level }} · {{ g.titel }}</small>
            </span>
            <span class="mini" :title="g.vitrine.map((k) => katalog[k]?.name).join(', ')">
              <span v-for="k in g.vitrine" :key="k">{{ katalog[k]?.emoji }}</span>
            </span>
          </a>
        </div>
      </section>

      <section v-if="daten?.neueste.length" class="panel">
        <h2>Zuletzt freigeschaltet</h2>
        <ul class="feed">
          <li v-for="(n, i) in daten.neueste" :key="i">
            <UserAvatar :user-id="n.user_id" />
            <span class="was">
              <a :href="`#/profil/person/${n.user_id}`">{{ name(n.user_id) }}</a>:
              {{ katalog[n.key]?.emoji }} {{ katalog[n.key]?.name }}
            </span>
            <time class="muted" :datetime="n.am">{{ vorWann(n.am) }}</time>
          </li>
        </ul>
      </section>

      <section v-for="k in nachKategorie" :key="k.name" class="panel">
        <h2>{{ k.name }}</h2>
        <div class="raster">
          <ErfolgKachel
            v-for="d in k.erfolge"
            :key="d.key"
            :erfolg="d"
            :am="ich?.freigeschaltet[d.key] || null"
            :wert="ich?.fortschritt[d.familie] ?? null"
          />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 980px; display: flex; flex-direction: column; gap: 1.2rem; }
h2 { margin: 0 0 1rem; font-size: 1.1rem; }
.back { text-decoration: none; font-size: 0.85rem; }
.kopf, .stand { display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap; }
.kopf h1 { margin: 0; }
.kopf p { margin: 0.2rem 0 0; }
.gross { width: 64px; height: 64px; font-size: 1.3rem; }
.levelinfo { flex: 1; min-width: 220px; display: flex; flex-direction: column; gap: 0.35rem; }
.lvl { font-size: 1.15rem; }
.score { font-weight: 800; color: var(--gold); }
.levelbalken { height: 10px; border-radius: 5px; background: var(--bg-raised); overflow: hidden; }
.levelbalken span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--gold)); }
.raster { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.7rem; }
.mit-aktion { display: flex; flex-direction: column; gap: 0.2rem; }
.mit-aktion > button { align-self: flex-end; }
.gruppe { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.5rem; }
.mitglied {
  display: flex; align-items: center; gap: 0.7rem; padding: 0.6rem 0.7rem; border-radius: var(--radius);
  border: 1px solid var(--line); text-decoration: none; color: inherit;
}
.mitglied:hover { background: var(--bg-raised); }
.mitglied .avatar { width: 36px; height: 36px; font-size: 0.8rem; }
.wer { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.wer strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wer small { font-size: 0.74rem; }
.mini { display: flex; gap: 2px; font-size: 1rem; }
.vitrine { display: flex; gap: 1rem; flex-wrap: wrap; }
.pokal {
  display: flex; flex-direction: column; align-items: center; gap: 0.3rem; text-align: center; width: 140px;
  padding: 1rem 0.6rem; border-radius: var(--radius); background: var(--bg-raised); border: 1px solid var(--line);
}
.pokal .medaille {
  width: 64px; height: 64px; border-radius: 50%; display: grid; place-items: center; font-size: 1.9rem;
  background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--m) 70%, white), var(--m));
  box-shadow: 0 0 22px color-mix(in srgb, var(--m) 55%, transparent);
}
.pokal strong { font-size: 0.85rem; }
.stufe-1 { --m: #b0703c; }
.stufe-2 { --m: #a9b3bd; }
.stufe-3 { --m: #e0a82e; }
.stufe-4 { --m: #7fd3e6; }
.feed { list-style: none; padding: 0; margin: 0; }
.feed li { display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0; border-top: 1px solid var(--line); font-size: 0.88rem; }
.feed li .was { flex: 1; }
.feed a { color: var(--text); }
.feed time { font-size: 0.76rem; }
</style>
