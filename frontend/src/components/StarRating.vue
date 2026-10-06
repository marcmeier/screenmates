<script setup>
import { ref } from 'vue'

// Five buttons in natural order: the n-th star sets n stars.
// (The previous version reversed the DOM for a CSS hover trick and so gave 5 for the first star.)
const props = defineProps({ modelValue: { type: Number, default: 0 }, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const hover = ref(0)
</script>

<template>
  <div class="stars" role="radiogroup" :aria-label="$t('starrating.bewertung')" @mouseleave="hover = 0">
    <button
      v-for="n in 5"
      :key="n"
      type="button"
      role="radio"
      :aria-checked="props.modelValue === n"
      :aria-label="$t('starrating.von5', { n })"
      :disabled="disabled"
      :class="{ lit: n <= (hover || props.modelValue) }"
      @mouseenter="hover = n"
      @click="emit('update:modelValue', n)"
    >★</button>
  </div>
</template>

<style scoped>
.stars { display: inline-flex; }
button {
  border: none; background: none; padding: 0 2px; font-size: 1.25rem; line-height: 1;
  color: #3a3a46;
}
button:hover:not(:disabled) { background: none; }
button.lit { color: var(--gold); }
</style>
