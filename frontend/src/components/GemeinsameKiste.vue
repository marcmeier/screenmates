<script setup>
import { computed } from 'vue'
import { useApp } from '../stores/app'
import { useKiste } from '../stores/kiste'
import KistenBuehne from './KistenBuehne.vue'

// Wherever you are in the app: when the host opens the case for everyone, it plays here.
const app = useApp()
const kiste = useKiste()
const von = computed(() => app.userById(kiste.buehne?.von)?.name || '')
</script>

<template>
  <KistenBuehne
    v-if="kiste.buehne && kiste.buehne.gewinner"
    :key="`k${kiste.buehne.id}`"
    :pool="kiste.buehne.pool"
    :gewinner="kiste.buehne.gewinner"
    :seed="kiste.buehne.seed"
    :start="kiste.lokal(kiste.buehne.start)"
    :von="von"
    @fertig="kiste.fertig()"
  />
  <KistenBuehne
    v-else-if="kiste.probe"
    key="probe"
    :pool="kiste.probe.pool"
    :gewinner="kiste.probe.gewinner"
    :seed="kiste.probe.seed"
    :start="kiste.probe.start"
    probe
    @fertig="kiste.probe = null"
  />
</template>
