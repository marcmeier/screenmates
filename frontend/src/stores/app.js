import { defineStore } from 'pinia'
import { api } from '../api'
import { ausschalten } from '../push'

export const useApp = defineStore('app', {
  state: () => ({
    ready: false,
    me: null,
    users: [],
    hier: [], // ids of the names this browser may pick (see NamensWahl)
    admin: false,
    antraege: 0, // open name requests (admins only)
    gruppe: null, // the active group: { id, name, admin, mitglieder: [user ids] }
    gruppen: [], // all my groups
    // Invite-only: closed until this browser came in with an invitation (or has a name).
    zugang: { gesperrt: false, offen: true, einladung: null },
    einladungFehler: '',
    glocke: 0, // unread notifications (comes with the live poll)
    status: { movie_count: 0, canon_count: 0, tmdb: false, ki: false, syncing: false, last_sync: null },
  }),
  getters: {
    userById: (s) => (id) => s.users.find((u) => u.id === id),
    meineNamen: (s) => s.users.filter((u) => s.hier.includes(u.id)),
    dabei: (s) => s.users.filter((u) => u.dabei),
    vielleicht: (s) => s.users.filter((u) => u.rueckmeldung === 'vielleicht'),
    absagen: (s) => s.users.filter((u) => u.rueckmeldung === 'nein'),
    // Members of the active group (the server has more people than any one group).
    mitglieder: (s) => (s.gruppe ? s.users.filter((u) => s.gruppe.mitglieder.includes(u.id)) : []),
    // Movie-night admin rights: group admin, or server admin.
    gruppenAdmin: (s) => s.admin || !!s.gruppe?.admin,
    verwaltetGruppen: (s) => s.admin || s.gruppen.some((g) => g.admin),
    draussen: (s) => s.zugang.gesperrt && !s.zugang.offen,
  },
  actions: {
    async bootstrap() {
      await this.refreshZugang()
      if (!this.draussen) {
        await Promise.all([this.refreshUsers(), this.refreshStatus()])
        await this.refreshGruppen()
      }
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
      this.gruppe = r.gruppe
      this.hier = r.auf_geraet || []
    },
    async refreshGruppen() {
      this.gruppen = this.me ? (await api.get('/api/gruppen')).gruppen : []
    },
    /** Switch the active group; everything on screen belongs to the old one, so start afresh. */
    async wechseln(gruppeId) {
      await api.post('/api/gruppen/aktiv', { gruppe_id: gruppeId })
      window.location.reload()
    },
    async refreshStatus() {
      this.status = await api.get('/api/status')
    },
    /** Come in with an invitation code (from a #/einladung/<code> link). */
    async einlassen(token) {
      await api.post('/api/zugang', { token }, { quiet: true })
      this.einladungFehler = ''
      await this.bootstrap()
    },
    /** A login code (from another device of yours, or an admin): this browser gets that name. */
    async anmelden(code) {
      const r = await api.post('/api/login', { code }, { quiet: true })
      this.me = r.ich
      this.admin = r.admin
      this.einladungFehler = ''
      await this.bootstrap()
    },
    /** Take a name off this browser; it needs a new login code to come back. */
    async vergessen(userId) {
      if (userId === this.me?.id) await ausschalten({ quiet: true }).catch(() => {})
      await api.del(`/api/login/namen/${userId}`)
      if (userId === this.me?.id) {
        this.me = null
        this.admin = false
        this.gruppe = null
        this.gruppen = []
      }
      await this.refreshUsers()
    },
    /** Already have a name: join the invitation's group (or ask to). */
    async annehmen(token) {
      const r = await api.post('/api/einladungen/annehmen', { token }, { quiet: true })
      await this.refreshGruppen()
      return r
    },
    async choose(userId, movieId = null) {
      const r = await api.post('/api/users/waehlen', { user_id: userId, movie_id: movieId }, { quiet: true })
      this.me = r.ich
      this.admin = r.admin
      await this.refreshUsers()
      await this.refreshGruppen()
    },
    /** Create a name. Returns it; `freigegeben: false` means it now waits for an admin. */
    async createUser(name) {
      const u = await api.post('/api/users', { name }, { quiet: true })
      if (u.freigegeben) await this.choose(u.id)
      return u
    },
    async logout() {
      // Notifications on this device were for this person, not for whoever logs in next.
      await ausschalten({ quiet: true }).catch(() => {})
      await api.post('/api/users/waehlen', { user_id: null })
      this.me = null
      this.admin = false
      this.antraege = 0
      this.gruppe = null
      this.gruppen = []
    },
    async toggleDabei() {
      Object.assign(this.me, await api.post('/api/dabei'))
      await this.refreshUsers()
    },
    /** Answer for the next movie night: 'ja', 'vielleicht', 'nein' or null (take it back). */
    async antworten(antwort) {
      Object.assign(this.me, await api.put('/api/dabei', { antwort }))
      await this.refreshUsers()
    },
  },
})
