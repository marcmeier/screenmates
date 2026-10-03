<script setup>
import { computed } from 'vue'
import { useApp } from '../stores/app'
import { initialen } from '../format'

const props = defineProps({ userId: { type: Number, default: null }, user: { type: Object, default: null } })
const app = useApp()
const u = computed(() => props.user || app.userById(props.userId))
</script>

<template>
  <span
    class="avatar"
    :style="{ background: u?.color || '#555' }"
    :title="u?.name || 'Gelöschter Nutzer'"
  >{{ u ? initialen(u.name) : '?' }}</span>
</template>
