<script setup>
import { t } from '../i18n'
import { ref, watch } from 'vue'
import { useMovieList } from '../composables/useMovieList'
import { debounce } from '../format'
import Poster from './Poster.vue'

// Search-and-click a film. Used wherever a film serves as a password
// (access question, name protection), so nothing secret is ever typed or shown.
const props = defineProps({
  placeholder: { type: String, default: t('filmpicker.filmSuchen') },
  busy: Boolean,
  endpoint: { type: String, default: '/api/search' },
})
const emit = defineEmits(['pick'])
const q = ref('')
const { items, loading, load, reset } = useMovieList(props.endpoint, 8)

const run = debounce((v) => (v.trim() ? load({ q: v.trim() }) : reset()), 250)
watch(q, run)
</script>

<template>
  <div class="picker">
    <input v-model="q" :placeholder="placeholder" autofocus :aria-label="$t('filmpicker.filmSuchen2')" />
    <ul v-if="items.length" class="results">
      <li v-for="m in items" :key="m.id">
        <button :disabled="busy" @click="emit('pick', m)">
          <span class="thumb"><Poster :movie="m" :title="false" /></span>
          <span class="t">{{ m.title }}</span>
          <span class="muted">{{ m.year }}</span>
        </button>
      </li>
    </ul>
    <p v-else-if="q && !loading" class="muted hint">{{ $t('filmpicker.keinTreffer') }}</p>
  </div>
</template>

<style scoped>
.results { list-style: none; margin: 0.6rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 4px; max-height: 300px; overflow: auto; }
.results button { width: 100%; justify-content: flex-start; text-align: left; border-color: transparent; background: transparent; }
.results button:hover { background: var(--bg-raised); }
.thumb { width: 30px; height: 45px; border-radius: 4px; overflow: hidden; flex: none; }
.t { flex: 1; }
.hint { margin: 0.6rem 0 0; font-size: 0.85rem; }
</style>
