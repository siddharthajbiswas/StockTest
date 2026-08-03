// Typing for the build-time env vars we read via import.meta.env.
interface ImportMetaEnv {
  /** Absolute base URL the engine worker fetches the price bundle from.
   *  Defaults to `data/` relative to the app's base path, which covers both the
   *  dev server and the subfolder deploy. Set this only when the bundle is
   *  hosted somewhere other than alongside the app (a CDN or object store).
   *
   *  Replaces VITE_API_BASE: as of Phase 5 there is no backend to point at —
   *  the engine runs in a Web Worker in the browser. */
  readonly VITE_DATA_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
