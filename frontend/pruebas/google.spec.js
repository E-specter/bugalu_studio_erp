// Segundo servidor (puerto 4322) construido con PUBLIC_ACCESO_GOOGLE: la variable se lee al construir (CA-04).
import { test, expect } from '@playwright/test';
import { SB, silenciarApi, sinViolaciones } from './ayudas-acceso.js';

test.use({ baseURL: 'http://localhost:4322' });
test.beforeEach(async ({ page }) => silenciarApi(page));

for (const ruta of ['/acceso', '/acceso/registro']) {
  test(`${ruta}: ofrece Continuar con Google tras un separador`, async ({ page }) => {
    await page.goto(ruta);
    const boton = page.getByRole('button', { name: 'Continuar con Google' });
    await expect(boton).toBeVisible();
    await expect(boton).toHaveClass(/boton-secundario/);
    await expect(page.getByText('O', { exact: true })).toBeVisible();
    await sinViolaciones(page);
  });
}

test('el acceso interno nunca ofrece Google', async ({ page }) => {
  for (const ruta of ['/acceso/interno', '/acceso/interno/registro']) {
    await page.goto(ruta);
    await expect(page.getByRole('button', { name: /Google/ })).toHaveCount(0);
  }
});

test('Google: signInWithOAuth con redirectTo al destino propio', async ({ page }) => {
  let destino;
  await page.route(`${SB}/authorize*`, (r) => ((destino = new URL(r.request().url())), r.fulfill({ status: 200, contentType: 'text/html', body: 'ok' })));
  await page.goto('/acceso?volver=/app/perfil');
  await page.getByRole('button', { name: 'Continuar con Google' }).click();
  await expect.poll(() => destino?.searchParams.get('provider')).toBe('google');
  expect(destino.searchParams.get('redirect_to')).toBe('http://localhost:4322/app/perfil');
});

test('Google con volver malicioso redirige a /app/', async ({ page }) => {
  let destino;
  await page.route(`${SB}/authorize*`, (r) => ((destino = new URL(r.request().url())), r.fulfill({ status: 200, contentType: 'text/html', body: 'ok' })));
  await page.goto('/acceso?volver=' + encodeURIComponent('//evil.com'));
  await page.getByRole('button', { name: 'Continuar con Google' }).click();
  await expect.poll(() => destino?.searchParams.get('redirect_to')).toBe('http://localhost:4322/app/');
});

test('Google: capturas', async ({ page }) => {
  for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
    await page.setViewportSize({ width: ancho, height: alto });
    await page.goto('/acceso');
    await page.screenshot({ path: `pruebas/capturas/acceso-google-${ancho}.png`, fullPage: true });
  }
});
