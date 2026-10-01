import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' permette di pubblicare il sito anche in una sottocartella
// (per esempio GitHub Pages: https://utente.github.io/earthpulse/).
export default defineConfig({
  plugins: [react()],
  base: './',
})
