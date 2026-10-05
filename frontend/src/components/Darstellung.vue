<script setup>
import { computed } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { SCHRIFTEN, THEMES, anwenden } from '../design'

// Your screenmates: colour theme and font. Stays dark; saved with your profile.
const app = useApp()
const design = computed(() => ({ theme: 'kino', schrift: 'inter', ...(app.me?.design || {}) }))

async function setzen(aenderung) {
  const neu = { ...design.value, ...aenderung }
  anwenden(neu) // at once, before the server answers
  app.me.design = (await api.put('/api/users/me/design', neu)).design
}
</script>

<template>
  <section class="panel">
    <h2>Darstellung</h2>
    <p class="muted">Nur für dich – auf allen Geräten, auf denen du angemeldet bist.</p>
    <h3>Farbschema</h3>
    <div class="themes" role="radiogroup" aria-label="Farbschema">
      <button
        v-for="(t, key) in THEMES"
        :key="key"
        class="theme"
        role="radio"
        :aria-checked="design.theme === key"
        :class="{ aktiv: design.theme === key }"
        :style="{ '--t-bg': t.bg, '--t-raised': t.raised, '--t-accent': t.accent }"
        @click="setzen({ theme: key })"
      >
        <span class="vorschau" aria-hidden="true"><span></span></span>
        {{ t.name }}
      </button>
    </div>
    <h3>Schrift</h3>
    <div class="schriften" role="radiogroup" aria-label="Schrift">
      <button
        v-for="(s, key) in SCHRIFTEN"
        :key="key"
        role="radio"
        :aria-checked="design.schrift === key"
        :class="{ aktiv: design.schrift === key }"
        :style="{ fontFamily: s.familie || 'system-ui' }"
        @mouseenter="s.laden?.()"
        @focus="s.laden?.()"
        @click="setzen({ schrift: key })"
      >
        {{ s.name }}
      </button>
    </div>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; }
h3 { margin: 1.1rem 0 0.5rem; font-size: 0.95rem; }
p { margin: 0; font-size: 0.85rem; }
.themes { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 0.5rem; }
.theme { flex-direction: column; align-items: stretch; gap: 0.35rem; padding: 0.45rem; font-size: 0.8rem; }
.vorschau { display: block; height: 38px; border-radius: 6px; background: var(--t-bg); border: 1px solid var(--t-raised); position: relative; overflow: hidden; }
.vorschau span { position: absolute; left: 8px; right: 40%; bottom: 8px; height: 8px; border-radius: 4px; background: var(--t-accent); }
.schriften { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.aktiv { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
</style>
