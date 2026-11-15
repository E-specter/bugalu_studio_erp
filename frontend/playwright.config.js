import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'pruebas',
  outputDir: 'pruebas/resultados',
  reporter: 'list',
  use: { baseURL: 'http://localhost:4321' },
  webServer: {
    command: 'npm run build && npm run preview -- --port 4321',
    url: 'http://localhost:4321',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
