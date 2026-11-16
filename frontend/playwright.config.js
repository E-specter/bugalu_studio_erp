import { defineConfig } from '@playwright/test';
import { PUERTO, PUERTO_PROVEEDORES, ORIGEN, ORIGEN_PROVEEDORES } from './pruebas/puertos.js';

export default defineConfig({
  testDir: 'pruebas',
  testIgnore: 'real/**', // el recorrido real tiene su propia config (playwright.real.config.js)
  outputDir: 'pruebas/resultados',
  reporter: 'list',
  use: { baseURL: ORIGEN },
  webServer: [
    {
      command: `npm run build -- --outDir dist-pruebas && npm run preview -- --outDir dist-pruebas --port ${PUERTO}`,
      url: ORIGEN,
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
      // Segundo build con proveedores sociales (PUBLIC_ACCESO_PROVEEDORES se lee al construir); en node_modules para no tocar .gitignore. Se sirve con un servidor propio porque astro preview no admite dos instancias.
      command: `npm run build -- --outDir node_modules/.cache/dist-google && node pruebas/servidor-estatico.mjs node_modules/.cache/dist-google ${PUERTO_PROVEEDORES}`,
      url: ORIGEN_PROVEEDORES,
      env: {
        PUBLIC_ACCESO_PROVEEDORES: 'google,facebook,twitter',
        PUBLIC_URL_API: 'http://api.prueba',
        PUBLIC_URL_SUPABASE: 'http://supabase.prueba',
        PUBLIC_CLAVE_PUBLICABLE_SUPABASE: 'clave-publicable-de-prueba',
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
