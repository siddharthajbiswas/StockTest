// Typing for the build-time env vars we read via import.meta.env.
interface ImportMetaEnv {
  /** Absolute base URL of the backend API. Empty in dev (Vite proxies
   *  same-origin paths); set to e.g. https://stocktest-api.biswas.net when the
   *  frontend is hosted apart from the backend (GitHub Pages). */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
