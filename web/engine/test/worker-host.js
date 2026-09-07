/**
 * Node `worker_threads` host for the engine handler.
 *
 * The browser entry (`src/worker/worker.js`) talks to `self` and `fetch`;
 * neither exists in Node. This adapter serves the SAME handler over a Node
 * worker with a filesystem loader, so `worker.test.js` exercises real
 * cross-thread messaging rather than calling the dispatcher in-process.
 */
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parentPort, workerData } from "node:worker_threads";
import { serve } from "../src/worker/handler.js";
const base = workerData.base;
const port = {
  postMessage: (msg) => parentPort.postMessage(msg),
  onMessage: (cb) => {
    parentPort.on("message", cb);
  },
};
serve(port, {
  loader: async (path) => {
    const buf = await readFile(join(base, path));
    return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  },
});
