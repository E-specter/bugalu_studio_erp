// Segundo servidor (segundo puerto) construido con PUBLIC_ACCESO_PROVEEDORES=google,facebook,twitter: se lee al construir (CA-04).
// "twitter" no es un proveedor conocido y debe ignorarse. El build por defecto no define la lista: cubre la lista vacia.
import { test, expect } from '@playwright/test';
import { SB, silenciarApi, sinViolaciones } from './ayudas-acceso.js';
import { ORIGEN, ORIGEN_PROVEEDORES } from './puertos.js';

test.use({ baseURL: ORIGEN_PROVEEDORES });
test.beforeEach(async ({ page }) => silenciarApi(page));

const botones = (page) => page.locator('bugalu-acceso [data-proveedor]');

for (const ruta of ['/acceso', '/acceso/registro']) {
  test(`${ruta}: un boton secundario por proveedor, en el orden de la lista, tras un separador`, async ({ page }) => {
    await page.goto(ruta);
    await expect(botones(page)).toHaveText(['Continuar con Google', 'Continuar con Facebook']);
    for (const nombre of ['Continuar con Google', 'Continuar con Facebook']) {
      const boton = page.getByRole('button', { name: nombre });
      await expect(boton).toBeVisible();
      await expect(boton).toHaveClass(/boton-secundario/);
    }
    await expect(page.getByText('O', { exact: true })).toHaveCount(1);
    await expect(page.getByRole('button', { name: /Twitter/i })).toHaveCount(0);
    await sinViolaciones(page);
  });
}

test('el acceso interno nunca ofrece proveedores', async ({ page }) => {
  for (const ruta of ['/acceso/interno', '/acceso/interno/registro']) {
    await page.goto(ruta);
    await expect(botones(page)).toHaveCount(0);
  }
});

for (const [proveedor, nombre] of [['google', 'Google'], ['facebook', 'Facebook']]) {
  test(`${nombre}: signInWithOAuth con su proveedor y redirectTo al destino propio`, async ({ page }) => {
    let destino;
    await page.route(`${SB}/authorize*`, (r) => ((destino = new URL(r.request().url())), r.fulfill({ status: 200, contentType: 'text/html', body: 'ok' })));
    await page.goto('/acceso?volver=/app/perfil');
    await page.getByRole('button', { name: `Continuar con ${nombre}` }).click();
    await expect.poll(() => destino?.searchParams.get('provider')).toBe(proveedor);
    expect(destino.searchParams.get('redirect_to')).toBe(`${ORIGEN_PROVEEDORES}/app/perfil`);
  });
}

test('un proveedor con volver malicioso redirige a /app/', async ({ page }) => {
  let destino;
  await page.route(`${SB}/authorize*`, (r) => ((destino = new URL(r.request().url())), r.fulfill({ status: 200, contentType: 'text/html', body: 'ok' })));
  await page.goto('/acceso?volver=' + encodeURIComponent('//evil.com'));
  await page.getByRole('button', { name: 'Continuar con Facebook' }).click();
  await expect.poll(() => destino?.searchParams.get('redirect_to')).toBe(`${ORIGEN_PROVEEDORES}/app/`);
});

test('con la lista vacia (build por defecto) no hay botones ni separador', async ({ page }) => {
  await page.goto(`${ORIGEN}/acceso`);
  await expect(botones(page)).toHaveCount(0);
  await expect(page.getByText('O', { exact: true })).toHaveCount(0);
});

test('proveedores: capturas', async ({ page }) => {
  for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
    await page.setViewportSize({ width: ancho, height: alto });
    await page.goto('/acceso');
    await page.screenshot({ path: `pruebas/capturas/acceso-proveedores-${ancho}.png`, fullPage: true });
  }
});
