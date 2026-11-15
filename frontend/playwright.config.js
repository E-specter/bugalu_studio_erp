import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'pruebas',
  testIgnore: 'real/**', // el recorrido real tiene su propia config (playwright.real.config.js)
  outputDir: 'pruebas/resultados',
  reporter: 'list',
  use: { baseURL: 'http://localhost:4321' },
  webServer: [
    {
      command: 'npm run build -- --outDir dist-pruebas && npm run preview -- --outDir dist-pruebas --port 4321',
      url: 'http://localhost:4321',
      // El build de pruebas emite /catalogo (PUBLIC_CATALOGO); el de producción no; por eso sale a dist-pruebas y dist/ nunca lo contiene.
      env: {
        PUBLIC_CATALOGO: '1',
        // Valores ficticios: las pruebas simulan la API con page.route y no usan red real.
        PUBLIC_URL_API: 'http://api.prueba',
        PUBLIC_URL_SUPABASE: 'http://supabase.prueba',
        PUBLIC_CLAVE_PUBLICABLE_SUPABASE: 'clave-publicable-de-prueba',
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      // Segundo build con Google activo (PUBLIC_ACCESO_GOOGLE se lee al construir); en node_modules para no tocar .gitignore. Se sirve con un servidor propio porque astro preview no admite dos instancias.
      command: 'npm run build -- --outDir node_modules/.cache/dist-google && node pruebas/servidor-estatico.mjs node_modules/.cache/dist-google 4322',
      url: 'http://localhost:4322',
      env: {
        PUBLIC_ACCESO_GOOGLE: '1',
        PUBLIC_URL_API: 'http://api.prueba',
        PUBLIC_URL_SUPABASE: 'http://supabase.prueba',
        PUBLIC_CLAVE_PUBLICABLE_SUPABASE: 'clave-publicable-de-prueba',
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
