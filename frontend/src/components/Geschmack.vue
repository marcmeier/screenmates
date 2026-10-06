<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import UserAvatar from './UserAvatar.vue'

// "Lena tickt zu 87 % wie du": whose stars are closest, from films both rated.
const props = defineProps({ userId: { type: Number, required: true } })
const app = useApp()
const daten = ref(null)
watch(
  () => props.userId,
  async (id) => (daten.value = await api.get(`/api/users/${id}/geschmack`, { quiet: true }).catch(() => null)),
  { immediate: true },
)
const ich = computed(() => props.userId === app.me?.id)
const name = (id) => app.userById(id)?.name ?? 'Jemand'
const mitMir = computed(() => (ich.value ? null : daten.value?.vergleiche.find((v) => v.user_id === app.me?.id)))
const liste = computed(() => (daten.value?.vergleiche ?? []).filter((v) => v.user_id !== app.me?.id || ich.value).slice(0, 4))
</script>

<template>
  <section v-if="daten" class="panel geschmack">
    <h2>Geschmacksverwandte</h2>
    <p v-if="mitMir" class="mitmir">
      Du und {{ name(userId) }}: <strong>{{ mitMir.prozent }} %</strong>
      <small class="muted">aus {{ mitMir.gemeinsam }} gemeinsam bewerteten Filmen</small>
    </p>
    <ul v-if="liste.length">
      <li v-for="v in liste" :key="v.user_id">
        <UserAvatar :user-id="v.user_id" link />
        <span class="wer">{{ name(v.user_id) }} <small class="muted">tickt zu</small></span>
        <span class="balken"><span :style="{ width: `${v.prozent}%` }"></span></span>
        <strong>{{ v.prozent }} %</strong>
        <small class="muted">{{ ich ? 'wie du' : `wie ${name(userId)}` }}</small>
      </li>
    </ul>
    <p v-else-if="!mitMir" class="muted">
      Sobald {{ ich ? 'du' : name(userId) }} und andere mindestens {{ daten.min }} gleiche Filme bewertet habt, steht hier, wer ähnlich tickt.
    </p>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.8rem; font-size: 1.05rem; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
li { display: grid; grid-template-columns: 28px 9rem 1fr 3rem auto; align-items: center; gap: 0.6rem; font-size: 0.88rem; }
li .avatar { width: 28px; height: 28px; font-size: 0.65rem; }
.wer { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.balken { height: 8px; border-radius: 4px; background: var(--bg-raised); overflow: hidden; }
.balken span { display: block; height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--gold)); }
li strong { text-align: right; font-variant-numeric: tabular-nums; }
.mitmir { margin: 0 0 0.8rem; }
p { font-size: 0.9rem; margin: 0; }
@media (max-width: 600px) { li { grid-template-columns: 28px 1fr 3rem; } li .balken, li > small { display: none; } }
</style>