import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const API = 'http://api.prueba/api/v1/perfil';
const json = (estado, cuerpo) => ({ status: estado, contentType: 'application/json', body: JSON.stringify(cuerpo) });
const error = (estado, codigo, mensaje) => json(estado, { error: { codigo, mensaje } });
const perfil = (extra = {}) => json(200, { id: 'u1', nombre: 'Ana Pérez', rol: 'ingeniero', especialidad: null, ...extra });
const etiquetasWcag = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

// Sesion simulada: supabase-js la lee de localStorage (storageKey fijo) mientras no caduque.
const conSesion = (page) =>
  page.addInitScript(() =>
    localStorage.setItem(
      'bugalu-sesion',
      JSON.stringify({
        access_token: 'token-de-prueba',
        refresh_token: 'refresco',
        token_type: 'bearer',
        expires_in: 3600,
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        user: { id: 'u1' },
      }),
    ),
  );

const estados = [
  { nombre: 'datos', ruta: (r) => r.fulfill(perfil()), texto: 'Ana Pérez' },
  { nombre: 'no-autenticado', ruta: (r) => r.fulfill(error(401, 'no_autenticado', 'Falta el token.')), texto: 'Tu sesión no es válida', enlace: '/acceso' },
  { nombre: 'sin-perfil', ruta: (r) => r.fulfill(error(404, 'perfil_no_encontrado', 'Sin perfil.')), texto: 'No encontramos tu perfil' },
  { nombre: 'servicio-no-disponible', ruta: (r) => r.fulfill(error(503, 'autenticacion_no_disponible', 'No disponible.')), texto: 'Servicio no disponible', reintentar: true },
  { nombre: 'sin-conexion', ruta: (r) => r.abort('connectionrefused'), texto: 'Sin conexión', reintentar: true },
  // Formato de error desconocido (p. ej. un proxy): estado genérico, nunca pantalla en blanco.
  { nombre: 'error-generico', ruta: (r) => r.fulfill({ status: 500, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'No pudimos cargar tu perfil', reintentar: true },
];

for (const e of estados) {
  test(`perfil: ${e.nombre} (Review Focus 4)`, async ({ page }) => {
    const consola = [];
    page.on('pageerror', (x) => consola.push(x.message));
    // Los 4xx/5xx y la red caida simulados los registra el navegador como "Failed to load resource": son esperados.
    page.on('console', (m) => m.type() === 'error' && !m.text().includes('Failed to load resource') && consola.push(m.text()));
    await page.route(API, e.ruta);
    await page.goto('/app/perfil');

    await expect(page.getByText(e.texto).first()).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    if (e.enlace) await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', e.enlace);
    if (e.reintentar) await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();

    const { violations } = await new AxeBuilder({ page }).withTags(etiquetasWcag).analyze();
    expect(violations).toEqual([]);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/perfil-${e.nombre}.png`, fullPage: true });
  });
}

test('perfil: cargando mientras la API tarda (aria-busy)', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await page.route(API, async (r) => {
    await llega;
    await r.fulfill(perfil({ especialidad: 'Mezcla' }));
  });
  await page.goto('/app/perfil');
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
  await expect(page.getByText('Cargando…')).toBeVisible();
  const { violations } = await new AxeBuilder({ page }).withTags(etiquetasWcag).analyze();
  expect(violations).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/perfil-cargando.png', fullPage: true });
  soltar();
  await expect(page.getByText('Mezcla')).toBeVisible();
});

test('perfil: Reintentar vuelve a pedir y muestra los datos', async ({ page }) => {
  let llamadas = 0;
  await page.route(API, (r) => (++llamadas === 1 ? r.fulfill(error(503, 'autenticacion_no_disponible', 'x')) : r.fulfill(perfil())));
  await page.goto('/app/perfil');
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByText('Ana Pérez')).toBeVisible();
  expect(llamadas).toBe(2);
});

test('perfil: Reintentar enfoca el título una sola vez y anuncia una sola vez', async ({ page }) => {
  let llamadas = 0;
  await page.route(API, (r) => (++llamadas === 1 ? r.fulfill(error(503, 'autenticacion_no_disponible', 'x')) : r.fulfill(error(401, 'no_autenticado', 'x'))));
  await page.goto('/app/perfil');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  await page.evaluate(() => {
    window.__foco = 0;
    window.__anuncios = 0;
    document.addEventListener('focusin', (e) => e.target.classList?.contains('panel-titulo') && window.__foco++);
    const vivo = document.querySelector('[data-anuncio]');
    new MutationObserver(() => vivo.textContent && window.__anuncios++).observe(vivo, { childList: true, characterData: true });
  });
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByText('Tu sesión no es válida').first()).toBeVisible();
  const foco = await page.evaluate(() => window.__foco);
  expect(foco).toBe(1);
  await expect(page.locator('[data-salida] .panel-titulo')).toBeFocused();
  expect(await page.evaluate(() => window.__anuncios)).toBe(1);
  await expect(page.locator('[data-anuncio]')).toHaveText(/Tu sesión no es válida/);
});

test('api: Authorization Bearer solo con sesion', async ({ page }) => {
  const cabeceras = [];
  await page.route(API, (r) => {
    cabeceras.push(r.request().headers());
    return r.fulfill(perfil());
  });
  await page.goto('/app/perfil');
  await expect(page.getByText('Ana Pérez')).toBeVisible();
  expect(cabeceras[0].authorization).toBeUndefined();
  expect(cabeceras[0].accept).toBe('application/json');

  await conSesion(page);
  await page.reload();
  await expect(page.getByText('Ana Pérez')).toBeVisible();
  expect(cabeceras[1].authorization).toBe('Bearer token-de-prueba');
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('perfil: avisa de que necesita JavaScript y no anuncia carga', async ({ page }) => {
    await page.goto('/app/perfil');
    // Playwright ignora el texto de <noscript>: se comprueba en el HTML y en lo que se ve.
    expect(await page.content()).toContain('Esta página necesita JavaScript');
    await expect(page.locator('bugalu-perfil [data-salida]')).toBeHidden();
    await expect(page.locator('bugalu-perfil noscript .aviso-titulo')).toBeVisible();
    await page.screenshot({ path: 'pruebas/capturas/perfil-sin-js.png', fullPage: true });
  });
});
