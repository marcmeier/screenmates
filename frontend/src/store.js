import { defineStore } from 'pinia'
import { api } from './api'

export const useApp = defineStore('app', {
  state: () => ({
    me: null,
    users: [],
    status: { movie_count: 0, canon_count: 0, tmdb: false, ki: false },
    ready: false,
  }),
  actions: {
    async bootstrap() {
      const [status, users] = await Promise.all([api.get('/api/status'), api.get('/api/users')])
      this.status = status
      this.users = users.users
      this.me = users.ich
      this.ready = true
    },
    async refreshUsers() {
      const r = await api.get('/api/users')
      this.users = r.users
      this.me = r.ich
    },
    async choose(user_id, movie_id = null) {
      const r = await api.post('/api/users/waehlen', { user_id, movie_id })
      this.me = r.ich
      await this.refreshUsers()
      return r
    },
    async logout() {
      await api.post('/api/users/waehlen', { user_id: null })
      this.me = null
    },
  },
})
