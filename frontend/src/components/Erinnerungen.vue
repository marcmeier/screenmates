<script setup>
import { useUi } from '../stores/ui'
import { datum, dezimal } from '../format'
import { t } from '../i18n'
import Poster from './Poster.vue'
import UserAvatar from './UserAvatar.vue'

// "On this day a year ago": what the group watched around this date in earlier years.
defineProps({ erinnerungen: { type: Array, required: true } })
const ui = useUi()

const wann = (e) => t(e.tage === 0 ? 'erinnerungen.heute' : 'erinnerungen.dieseWoche', { n: e.jahre }, e.jahre)
// The comment people liked most, else the first one.
const zitat = (eintrag) => [...eintrag.notes].sort((a, b) => b.hearts.length - a.hearts.length)[0]
</script>

<template>
  <section class="panel erinnerung">
    <article v-for="e in erinnerungen" :key="e.eintrag.id">
      <h2 class="section-title">{{ wann(e) }}</h2>
      <div class="film">
        <button class="thumb" :aria-label="$t('allg.detailsVon', { title: e.eintrag.movie?.title })" @click="ui.open(e.eintrag.movie)">
          <Poster :movie="e.eintrag.movie" :title="false" />
        </button>
        <div class="was">
          <button class="titel" @click="ui.open(e.eintrag.movie)">{{ e.eintrag.movie?.title }}</button>
          <span class="muted klein">{{ datum(e.eintrag.watched_at) }}<template v-if="e.eintrag.rating_avg"> {{ $t('erinnerungen.ihrX', { x: dezimal(e.eintrag.rating_avg) }) }}</template></span>
          <span class="avatare"><UserAvatar v-for="id in e.eintrag.participants" :key="id" :user-id="id" /></span>
        </div>
      </div>
      <blockquote v-if="zitat(e.eintrag)">
        {{ $t('allg.zitat', { text: zitat(e.eintrag).text }) }}
        <UserAvatar v-if="zitat(e.eintrag).user_id" :user-id="zitat(e.eintrag).user_id" />
      </blockquote>
    </article>
  </section>
</template>

<style scoped>
.erinnerung { margin-top: 1rem; display: flex; flex-direction: column; gap: 1rem; background: linear-gradient(160deg, rgba(245, 166, 35, 0.1), transparent 60%), var(--bg-soft); }
.section-title { margin-top: 0; color: var(--gold); }
.film { display: flex; gap: 0.8rem; align-items: center; }
.thumb { padding: 0; width: 54px; height: 81px; border-radius: 6px; overflow: hidden; flex: none; background: var(--bg-raised); }
.was { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.titel { padding: 0; border: none; background: none; font-weight: 700; font-size: 1rem; text-align: left; }
.titel:hover { background: none; text-decoration: underline; }
.klein { font-size: 0.8rem; }
.avatare .avatar { width: 20px; height: 20px; font-size: 0.55rem; }
blockquote { margin: 0.7rem 0 0; font-size: 0.88rem; font-style: italic; color: var(--text); display: flex; gap: 0.5rem; align-items: flex-start; }
blockquote .avatar { width: 20px; height: 20px; font-size: 0.55rem; flex: none; font-style: normal; }
</style>
