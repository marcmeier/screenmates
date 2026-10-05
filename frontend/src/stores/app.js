import { defineStore } from 'pinia'
import { api } from '../api'

export const useApp = defineStore('app', {
  state: () => ({
    ready: false,
    me: null,
    users: [],
    admin: false,
    antraege: 0, // open name requests (admins only)
    // The access question: closed until this browser has answered it.
    zugang: { gesperrt: false, offen: true, frage: '' },
    status: { movie_count: 0, canon_count: 0, tmdb: false, ki: false, syncing: false, last_sync: null },
  }),
  getters: {
    userById: (s) => (id) => s.users.find((u) => u.id === id),
    dabei: (s) => s.users.filter((u) => u.dabei),
    draussen: (s) => s.zugang.gesperrt && !s.zugang.offen,
  },
  actions: {
    async bootstrap() {
      await this.refreshZugang()
      if (!this.draussen) await Promise.all([this.refreshUsers(), this.refreshStatus()])
      this.ready = true
    },
    async refreshZugang() {
      this.zugang = await api.get('/api/zugang')
    },
    async refreshUsers() {
      const r = await api.get('/api/users')
      this.users = r.users
      this.me = r.ich
      this.admin = r.admin
      this.antraege = r.antraege
    },
    async refreshStatus() {
      this.status = await api.get('/api/status')
    },
    async answer(movieId) {
      await api.post('/api/zugang', { movie_id: movieId }, { quiet: true })
      await this.bootstrap()
    },
    async choose(userId, movieId = null) {
      const r = await api.post('/api/users/waehlen', { user_id: userId, movie_id: movieId }, { quiet: true })
      this.me = r.ich
      this.admin = r.admin
      await this.refreshUsers()
    },
    /** Create a name. Returns it; `freigegeben: false` means it now waits for an admin. */
    async createUser(name) {
      const u = await api.post('/api/users', { name }, { quiet: true })
      if (u.freigegeben) await this.choose(u.id)
      return u
    },
    async logout() {
      await api.post('/api/users/waehlen', { user_id: null })
      this.me = null
      this.admin = false
      this.antraege = 0
    },
    async toggleDabei() {
      const r = await api.post('/api/dabei')
      this.me.dabei = r.dabei
      await this.refreshUsers()
    },
  },
})
