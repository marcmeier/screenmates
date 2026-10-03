import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import { ApiError } from './api'

// API errors are already shown as toasts; don't let un-awaited ones spam the console.
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason instanceof ApiError || e.reason?.name === 'AbortError') e.preventDefault()
})

createApp(App).use(createPinia()).mount('#app')
