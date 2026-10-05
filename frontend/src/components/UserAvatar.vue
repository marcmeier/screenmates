<script setup>
import { computed, ref, watch } from 'vue'
import { useApp } from '../stores/app'
import { initialen } from '../format'

const props = defineProps({ userId: { type: Number, default: null }, user: { type: Object, default: null } })
const app = useApp()
const u = computed(() => props.user || app.userById(props.userId))
const kaputt = ref(false)
watch(() => u.value?.bild, () => (kaputt.value = false))
</script>

<template>
  <span
    class="avatar"
    :style="{ background: u?.color || '#555' }"
    :title="u?.name || 'Gelöschter Nutzer'"
  >
    <img v-if="u?.bild && !kaputt" :src="u.bild" alt="" loading="lazy" decoding="async" @error="kaputt = true" />
    <template v-else>{{ u ? initialen(u.name) : '?' }}</template>
  </span>
</template>
