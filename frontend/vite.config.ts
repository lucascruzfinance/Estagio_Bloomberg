/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const API = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'

// Production-only Content Security Policy (dev HMR relies on inline scripts).
// Only our origin and the basemap host may be contacted; inline styles are needed
// by React style props and MapLibre.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://tiles.openfreemap.org",
  "font-src 'self' data:",
  "connect-src 'self' https://tiles.openfreemap.org",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'none'",
].join('; ')

function contentSecurityPolicy(): Plugin {
  return {
    name: 'content-security-policy',
    apply: 'build',
    transformIndexHtml: (html) =>
      html.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`),
  }
}

// The browser only talks to its own origin; Vite forwards API calls in dev/preview.
const proxy = {
  '/api': { target: API, changeOrigin: false },
  '/ready': { target: API, changeOrigin: false },
  '/health': { target: API, changeOrigin: false },
}

export default defineConfig({
  plugins: [react(), contentSecurityPolicy()],
  server: { port: 5173, strictPort: true, proxy },
  preview: { port: 4173, strictPort: true, proxy },
  // MapLibre is split out by the lazy map route; ECharts only ships the modules it registers.
  build: { chunkSizeWarningLimit: 1200 },
  worker: { format: 'es' },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
