/**
 * Browser Web Worker entry point.
 *
 * Loaded by `client.ts` as a module worker. Everything heavy — decoding the
 * price bundle, every backtest, the 100-combo sweep — happens on this thread,
 * so the UI thread stays free to render and respond to input.
 *
 * The data base URL arrives in a `configure` message rather than the worker's
 * query string. That keeps the construction site a bundler-analyzable literal
 * (`new Worker(new URL("./worker.ts", import.meta.url), { type: "module" })`);
 * mutating the URL to append a query param defeats Vite's worker detection and
 * silently produces a build with no worker chunk.
 */

import { serve } from "./handler.js";
import type { PortLike } from "./protocol.js";

/**
 * The worker global. Declared structurally rather than via the "WebWorker" lib,
 * because that lib and "DOM" both define `self`/`location` with incompatible
 * types and cannot be enabled together in one project.
 */
declare const self: {
  postMessage(msg: unknown): void;
  onmessage: ((e: { data: unknown }) => void) | null;
};

let base = "./data";

const port: PortLike = {
  postMessage: (msg) => self.postMessage(msg),
  onMessage: (cb) => {
    self.onmessage = (e: { data: unknown }) => cb(e.data);
  },
};

/**
 * Fetch a bundle artifact, preferring the pre-compressed `.gz` twin.
 *
 * GitHub Pages (and most static hosts) compress by content type and leave
 * `application/octet-stream` alone, so `universe.bin` would transfer at its
 * full 18.66 MB rather than 12.63 MB. Fetching the `.gz` ourselves and
 * inflating with `DecompressionStream` gets the compression back without
 * needing any server configuration — which is the whole point of a static
 * deploy.
 *
 * Falls back to the raw file when `DecompressionStream` is unavailable or no
 * `.gz` twin exists, so a host that *does* negotiate encoding still works.
 */
async function load(path: string): Promise<ArrayBuffer> {
  if (typeof DecompressionStream !== "undefined") {
    const res = await fetch(`${base}/${path}.gz`);
    if (res.ok) {
      const buf = await res.arrayBuffer();
      // Check the gzip magic number rather than trusting the URL. Some hosts
      // serve .gz with `Content-Encoding: gzip`, in which case the browser has
      // ALREADY inflated it and decompressing again would throw. Sniffing the
      // bytes makes this correct either way.
      const head = new Uint8Array(buf, 0, Math.min(2, buf.byteLength));
      if (head.length === 2 && head[0] === 0x1f && head[1] === 0x8b) {
        const stream = new Response(buf).body!.pipeThrough(
          new DecompressionStream("gzip"),
        );
        return new Response(stream).arrayBuffer();
      }
      return buf;
    }
  }
  const res = await fetch(`${base}/${path}`);
  if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
  return res.arrayBuffer();
}

serve(port, {
  onConfigure: (cfg) => {
    base = cfg.dataBase.replace(/\/$/, "");
  },
  loader: load,
});
