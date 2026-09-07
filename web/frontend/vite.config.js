import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { createReadStream, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

// Public base path. "/" for local dev; set to "/sid/stocktest/" for the
// GitHub Pages build so bundled asset URLs resolve under that subfolder.
const BASE = process.env.VITE_BASE ?? "/";

// Phase 5: there is no backend. The engine runs in a Web Worker in the browser,
// so the old dev proxy to FastAPI is gone. What the app needs instead is the
// binary price bundle from tools/build_web_data.py, served at /data. In dev we
// stream it straight out of build/webdata rather than copying ~119 MB into
// public/ on every build.
const DATA_DIR = resolve(HERE, "../../build/webdata");
// Golden oracle outputs, served in DEV ONLY for verify.html (the in-browser
// parity harness). Never part of a production build.
const GOLDEN_DIR = resolve(HERE, "../../golden");

export default defineConfig({
  base: BASE,
  plugins: [
    react(),
    {
      name: "stocktest-serve-data",
      configureServer(server) {
        const mount = (prefix, dir) =>
          server.middlewares.use(prefix, (req, res, next) => {
            const rel = decodeURIComponent((req.url ?? "/").split("?")[0]);
            const target = resolve(dir, "." + rel);
            // Reject path traversal before touching the filesystem.
            if (!target.startsWith(dir)) {
              res.statusCode = 403;
              res.end("Forbidden");
              return;
            }
            try {
              if (!statSync(target).isFile()) return next();
            } catch {
              return next();
            }
            res.setHeader(
              "Content-Type",
              target.endsWith(".json")
                ? "application/json"
                : "application/octet-stream",
            );
            createReadStream(target).pipe(res);
          });
        mount("/data", DATA_DIR);
        mount("/golden", GOLDEN_DIR);
      },
    },
  ],
  // The engine worker uses static ES imports.
  worker: { format: "es" },
  server: {
    port: 5173,
    fs: {
      // The engine package lives at web/engine, outside this Vite root. The
      // production build inlines it via Rollup, but the dev server refuses to
      // serve files outside the root unless they are allow-listed — without
      // this the worker module 404s and the app reports "Engine worker
      // crashed" with no further detail.
      allow: [resolve(HERE, "..")],
    },
  },
});
