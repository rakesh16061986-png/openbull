import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// Backend proxy target is overridable via BACKEND_PORT so this same config
// works unmodified for both the production deployment (port 8000, the
// default) and the isolated dev deployment (port 8001, set in that
// deployment's systemd unit) - see openbull-update-runbook.md.
const backendPort = process.env.BACKEND_PORT || "8000"
const backendTarget = `http://127.0.0.1:${backendPort}`
const backendWsTarget = `ws://127.0.0.1:${backendPort}`

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Pre-bundle the Plotly CJS bundles so dev and prod see identical default-
  // export shapes — without this Vite occasionally returns the namespace
  // object instead of the default function and the chart fails to mount.
  optimizeDeps: {
    include: ["react-plotly.js/factory", "plotly.js-cartesian-dist-min"],
  },
  server: {
    host: "127.0.0.1", // force IPv4 loopback — Node on Windows binds "localhost" to ::1-only
    port: 5173,
    strictPort: true,
    proxy: {
      // Trailing slashes prevent accidental prefix matches — e.g. the bare
      // "/web" rule used to swallow "/websocket/test" because it starts with
      // "/web" — causing the browser to hit FastAPI instead of Vite's SPA.
      "/api/": { target: backendTarget, changeOrigin: true },
      "/auth/": { target: backendTarget, changeOrigin: true },
      "/web/": { target: backendTarget, changeOrigin: true },
      "/health": { target: backendTarget, changeOrigin: true },
      "/upstox/": { target: backendTarget, changeOrigin: true },
      "/zerodha/": { target: backendTarget, changeOrigin: true },
      // Strategy module WebSocket — proxied with ws:true so the upgrade
      // handshake is forwarded to the backend. Without this Vite serves
      // the SPA's index.html for /ws/strategy/{id} and the browser sees
      // an immediate close (or just hangs at opening) — which was the
      // whole reason live PnL never streamed in dev.
      "/ws/": {
        target: backendWsTarget,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
