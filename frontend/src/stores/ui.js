import { defineStore } from 'pinia'

let nextId = 1

export const useUi = defineStore('ui', {
  state: () => ({
    toasts: [],
    loginOpen: false,
    detail: null, // movie shown in the detail sheet
    // Bumped after any change to shared lists, so open tabs know to reload.
    changes: 0,
  }),
  actions: {
    toast(text, kind = 'info', ms = 3500) {
      const id = nextId++
      if (this.toasts.length >= 3) this.toasts.shift()
      this.toasts.push({ id, text, kind })
      setTimeout(() => this.dismiss(id), ms)
    },
    dismiss(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id)
    },
    changed() {
      this.changes++
    },
    open(movie) {
      this.detail = movie
    },
  },
})
