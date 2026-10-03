import { defineStore } from 'pinia'
import { api } from '../api'

export const useApp = defineStore('app', {
  state: () => ({
    ready: false,
    me: null,
    users: [],
    host: false,
    hostEingerichtet: false,
    status: { movie_count: 0, canon_count: 0, tmdb: false, ki: false, syncing: false, last_sync: null },
  }),
  getters: {
    userById: (s) => (id) => s.users.find((u) => u.id === id),
    dabei: (s) => s.users.filter((u) => u.dabei),
  },
  actions: {
    async bootstrap() {
      await Promise.all([this.refreshUsers(), this.refreshStatus(), this.refreshHost()])
      this.ready = true
    },
    async refreshUsers() {
      const r = await api.get('/api/users')
      this.users = r.users
      this.me = r.ich
      this.host = r.host
    },
    async refreshStatus() {
      this.status = await api.get('/api/status')
    },
    async refreshHost() {
      const r = await api.get('/api/host')
      this.host = r.host
      this.hostEingerichtet = r.eingerichtet
    },
    async choose(userId, movieId = null) {
      const r = await api.post('/api/users/waehlen', { user_id: userId, movie_id: movieId }, { quiet: true })
      this.me = r.ich
      this.host = r.host
      await this.refreshUsers()
    },
    async createUser(name) {
      const u = await api.post('/api/users', { name })
      await this.choose(u.id)
    },
    async logout() {
      await api.post('/api/users/waehlen', { user_id: null })
      this.me = null
      this.host = false
    },
    async toggleDabei() {
      const r = await api.post('/api/dabei')
      this.me.dabei = r.dabei
      await this.refreshUsers()
    },
    async unlockHost(movieId) {
      const r = await api.post('/api/host', { an: true, movie_id: movieId }, { quiet: true })
      this.host = r.host
      this.hostEingerichtet = true
    },
    async lockHost() {
      await api.post('/api/host', { an: false })
      this.host = false
    },
  },
})
