import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy API calls to the FastAPI backend (default http://localhost:8000) during
// dev, so the frontend can call same-origin paths like /pickers, /backtest, etc.
const BACKEND = process.env.VITE_BACKEND ?? "http://localhost:8000";
const apiPaths = ["/pickers", "/timers", "/universe", "/tickers", "/backtest", "/strategies", "/validate", "/health"];

// Public base path. "/" for local dev; set to "/sid/stocktest/" for the
// GitHub Pages build so bundled asset URLs resolve under that subfolder.
const BASE = process.env.VITE_BASE ?? "/";

export default defineConfig({
  base: BASE,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      apiPaths.map((p) => [p, { target: BACKEND, changeOrigin: true }]),
    ),
  },
});
