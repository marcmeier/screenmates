import { createApp } from 'vue'
import { createPinia } from 'pinia'
// Shipped with the app so everyone sees the same type, no font CDN involved.
import '@fontsource-variable/inter'
import './style.css'
import App from './App.vue'
import { ApiError } from './api'
import { anwenden, gemerkt } from './design'
import { registrieren } from './push'

// This device's last theme and font right away – no flash of the default look.
anwenden(gemerkt())

// API errors are already shown as toasts; don't let un-awaited ones spam the console.
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason instanceof ApiError || e.reason?.name === 'AbortError') e.preventDefault()
})

createApp(App).use(createPinia()).mount('#app')

// Push notifications and the home-screen app.
registrieren()
