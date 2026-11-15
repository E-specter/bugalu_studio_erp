import { defineConfig } from '@playwright/test';

// Recorrido real de RF-01 contra el Supabase local, un backend propio y `astro dev` con frontend/.env. Aparte de `npm run test:e2e`.
// Frontend en 4321 (Auth solo redirige a ese origen) y backend en 8010 para no chocar con uno ya escuchando en 8000.
const PUERTO_API = 8010;
export default defineConfig({
  testDir: 'pruebas/real',
  outputDir: 'pruebas/resultados-real',
  reporter: 'list',
  workers: 1,
  timeout: 120_000,
  use: { baseURL: 'http://localhost:4321', viewport: { width: 1440, height: 900 } },
  webServer: [
    {
      command: `uv run uvicorn bugalu.main:crear_app --factory --host 127.0.0.1 --port ${PUERTO_API} --loop bugalu.compartido.bucle:crear_bucle`,
      cwd: '../backend',
      url: `http://127.0.0.1:${PUERTO_API}/api/v1/perfil`, // sin token responde 401: basta para saber que escucha
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npx astro dev --host localhost --port 4321',
      url: 'http://localhost:4321',
      env: { PUBLIC_URL_API: `http://127.0.0.1:${PUERTO_API}` }, // el resto (Supabase) sale de frontend/.env
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
