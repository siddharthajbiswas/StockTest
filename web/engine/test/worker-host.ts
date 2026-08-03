/**
 * Node `worker_threads` host for the engine handler.
 *
 * The browser entry (`src/worker/worker.ts`) talks to `self` and `fetch`;
 * neither exists in Node. This adapter serves the SAME handler over a Node
 * worker with a filesystem loader, so `worker.test.ts` exercises real
 * cross-thread messaging rather than calling the dispatcher in-process.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parentPort, workerData } from "node:worker_threads";

import { serve } from "../src/worker/handler.js";
import type { PortLike } from "../src/worker/protocol.js";

const base = (workerData as { base: string }).base;

const port: PortLike = {
  postMessage: (msg) => parentPort!.postMessage(msg),
  onMessage: (cb) => { parentPort!.on("message", cb); },
};

serve(port, {
  loader: async (path: string) => {
    const buf = await readFile(join(base, path));
    return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
  },
});
