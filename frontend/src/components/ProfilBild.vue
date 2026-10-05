<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'

// Upload or remove someone's profile picture (your own, or anyone's for admins).
const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const app = useApp()
const ui = useUi()
const input = ref(null)
const busy = ref(false)
const error = ref('')

// Phone photos are often larger than the server's 5 MB: shrink them here first.
// The server crops and re-encodes anyway, so 1024 px is plenty.
const MAX = 1024

async function verkleinern(file) {
  let bmp
  try {
    bmp = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error('Dieses Bildformat kennt dein Browser nicht – bitte ein JPG oder PNG nehmen.')
  }
  const f = Math.min(1, MAX / Math.max(bmp.width, bmp.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bmp.width * f)
  canvas.height = Math.round(bmp.height * f)
  canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height)
  bmp.close?.()
  const typ = file.type === 'image/png' ? 'image/png' : 'image/jpeg' // keep transparency
  return new Promise((resolve) => canvas.toBlob(resolve, typ, 0.9))
}

async function gewaehlt(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  error.value = ''
  busy.value = true
  try {
    const blob = await verkleinern(file)
    await api.put(`/api/users/${props.user.id}/bild`, blob, { quiet: true })
    await app.refreshUsers()
    emit('changed')
    ui.toast('Profilbild gespeichert', 'ok')
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function entfernen() {
  await api.del(`/api/users/${props.user.id}/bild`)
  await app.refreshUsers()
  emit('changed')
  ui.toast('Profilbild entfernt')
}
</script>

<template>
  <div class="profilbild">
    <UserAvatar :user="user" class="gross" />
    <div class="aktionen">
      <div class="row">
        <button class="small" :disabled="busy" @click="input.click()">
          <Icon name="plus" :size="14" /> {{ busy ? 'Lade hoch …' : user.bild ? 'Bild ändern' : 'Bild hochladen' }}
        </button>
        <button v-if="user.bild && !busy" class="ghost small" @click="entfernen">Entfernen</button>
      </div>
      <p class="muted hint">JPG, PNG, WebP oder GIF. Wird quadratisch zugeschnitten; Ortsangaben aus Handyfotos werden entfernt.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
    <input ref="input" type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden aria-label="Profilbild auswählen" @change="gewaehlt" />
  </div>
</template>

<style scoped>
.profilbild { display: flex; align-items: center; gap: 1rem; }
.gross { width: 64px; height: 64px; font-size: 1.3rem; }
.aktionen { display: flex; flex-direction: column; gap: 0.3rem; min-width: 0; }
.hint { margin: 0; font-size: 0.78rem; }
.error { color: #ff6b6b; margin: 0; font-size: 0.85rem; }
.small { font-size: 0.78rem; }
</style>
