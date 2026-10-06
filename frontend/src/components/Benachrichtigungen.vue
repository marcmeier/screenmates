<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import { aboHier, ausschalten, einschalten, installiert, istIos, pushMoeglich } from '../push'
import Icon from './Icon.vue'

// Push notifications: switch them on per device, choose the kinds (for all your devices).
const ui = useUi()
const zustand = ref(null) // { schluessel, arten: [{ key, text, an }], geraete }
const hier = ref(false) // this device is subscribed
const busy = ref(false)
const moeglich = pushMoeglich()
const blockiert = ref(moeglich && Notification.permission === 'denied')
// iPhones and iPads only get web notifications in the app added to the home screen.
const iosOhneApp = istIos() && !installiert()

onMounted(async () => {
  zustand.value = await api.get('/api/push')
  hier.value = !!(await aboHier().catch(() => null))
})

async function an() {
  busy.value = true
  try {
    zustand.value = await einschalten(zustand.value.schluessel)
    hier.value = true
    ui.toast(t('benachrichtigungen.benachrichtigungenSindAn'), 'ok')
  } catch (e) {
    blockiert.value = Notification.permission === 'denied'
    if (e.status === undefined) ui.toast(e.message, 'error', 7000)
  } finally {
    busy.value = false
  }
}

async function aus() {
  busy.value = true
  try {
    zustand.value = (await ausschalten()) || zustand.value
    hier.value = false
    ui.toast(t('benachrichtigungen.aufDiesemGeraetGibt'))
  } finally {
    busy.value = false
  }
}

async function waehlen(art, wert) {
  zustand.value = await api.put('/api/push/arten', { arten: { [art.key]: wert } })
}

async function testen() {
  const r = await api.post('/api/push/test')
  const geraete = t('benachrichtigungen.geraete', { n: r.geraete }, r.geraete)
  if (r.geraete < r.von) ui.toast(t('benachrichtigungen.testAbgelehnt', { geraete, x: r.von - r.geraete }), 'error', 6000)
  else ui.toast(t('benachrichtigungen.testZugestellt', { geraete }), 'ok')
}

const geraeteText = computed(() => {
  const n = zustand.value?.geraete ?? 0
  return n ? t('benachrichtigungen.anAuf', { n }, n) : t('benachrichtigungen.nochAufKeinemGeraet')
})
</script>

<template>
  <section class="panel">
    <h2><Icon name="glocke" :size="18" /> {{ $t('benachrichtigungen.benachrichtigungen') }}</h2>
    <p class="muted">
      {{ $t('benachrichtigungen.erfahreAuchBeiGeschlossener') }}
    </p>

    <p v-if="!moeglich && iosOhneApp" class="notice">
      {{ $t('benachrichtigungen.aufDemIphoneUnd') }} <strong>{{ $t('benachrichtigungen.teilenZumHomeBildschirm') }}</strong> {{ $t('benachrichtigungen.undStarteScreenmatesVon') }}
    </p>
    <p v-else-if="!moeglich" class="notice">{{ $t('benachrichtigungen.dieserBrowserKannKeine') }}</p>
    <template v-else-if="zustand">
      <div class="row">
        <span class="chip" :class="{ ok: hier }"><Icon name="glocke" :size="13" /> {{ hier ? $t('benachrichtigungen.aufDiesemGeraetAn') : $t('benachrichtigungen.aufDiesemGeraetAus') }}</span>
        <button v-if="!hier" class="primary small" :disabled="busy || blockiert" @click="an">{{ $t('benachrichtigungen.aufDiesemGeraetEinschalten') }}</button>
        <button v-else class="small" :disabled="busy" @click="aus">{{ $t('benachrichtigungen.ausschalten') }}</button>
        <button v-if="zustand.geraete" class="small ghost" @click="testen">{{ $t('benachrichtigungen.testSchicken') }}</button>
        <span class="spacer"></span>
        <span class="muted klein">{{ geraeteText }}</span>
      </div>
      <p v-if="blockiert" class="notice klein">
        {{ $t('benachrichtigungen.derBrowserBlockiertBenachrichtigungen') }}
      </p>
    </template>

    <template v-if="zustand && moeglich">
      <h3>{{ $t('benachrichtigungen.worueber') }}</h3>
      <ul class="arten">
        <li v-for="a in zustand.arten" :key="a.key">
          <label>
            <input type="checkbox" :checked="a.an" @change="waehlen(a, $event.target.checked)" />
            <span>{{ a.text }}</span>
          </label>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
h3 { margin: 1.1rem 0 0.5rem; font-size: 0.95rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.klein { font-size: 0.8rem; }
.chip.ok { color: var(--ok); border-color: var(--ok); }
.notice.klein { margin-top: 0.8rem; }
.arten { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.35rem 1rem; }
.arten label { display: flex; align-items: center; gap: 0.55rem; font-size: 0.88rem; cursor: pointer; }
.arten input { width: 1.05rem; height: 1.05rem; accent-color: var(--accent); flex: none; }
</style>