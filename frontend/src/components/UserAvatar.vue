<script setup>
import { t } from '../i18n'
import { computed, ref, watch } from 'vue'
import { useApp } from '../stores/app'
import { initialen } from '../format'

// Picture or initials, with the achievement level as a small badge (from level 2).
// `link` makes it open the person's achievements profile.
const props = defineProps({
  userId: { type: Number, default: null },
  user: { type: Object, default: null },
  link: { type: Boolean, default: false },
})
const app = useApp()
const u = computed(() => props.user || app.userById(props.userId))
// The list entry knows the level; a passed-in user object (e.g. from an admin list) may not.
const level = computed(() => u.value?.level ?? app.userById(u.value?.id)?.level ?? null)
const kaputt = ref(false)
watch(() => u.value?.bild, () => (kaputt.value = false))
const titel = computed(() => (u.value ? `${u.value.name}${level.value > 1 ? ` · Level ${level.value}` : ''}` : t('useravatar.geloeschterNutzer')))
</script>

<template>
  <component
    :is="link && u ? 'a' : 'span'"
    class="avatar"
    :href="link && u ? `#/profil/person/${u.id}` : undefined"
    :style="{ background: u?.color || '#555' }"
    :title="titel"
  >
    <img v-if="u?.bild && !kaputt" :src="u.bild" alt="" loading="lazy" decoding="async" @error="kaputt = true" />
    <template v-else>{{ u ? initialen(u.name) : '?' }}</template>
    <span v-if="level > 1" class="lvl" aria-hidden="true">{{ level }}</span>
  </component>
</template>
