import { test, expect } from '@playwright/test';

// TAREA-602: foco y anuncio al reintentar, identificacion coherente, orden de lectura y objetivos tactiles.
const API = 'http://api.prueba/api/v1/perfil';
const json = (estado, cuerpo) => ({ status: estado, contentType: 'application/json', body: JSON.stringify(cuerpo) });
const error = (estado, codigo) => json(estado, { error: { codigo, mensaje: 'x' } });
const perfil = () => json(200, { id: 'u1', nombre: 'Ana Pérez', rol: 'ingeniero', especialidad: null });

const destino = (page) =>
  page.evaluate(() => ({ etiqueta: document.activeElement.tagName, texto: document.activeElement.textContent.trim() }));

for (const [nombre, segunda, texto] of [
  ['503 -> 401', (r) => r.fulfill(error(401, 'no_autenticado')), 'Tu sesión no es válida'],
  ['503 -> 200', (r) => r.fulfill(perfil()), 'Ana Pérez'],
]) {
  test(`reintentar con teclado (${nombre}): el foco no cae en body y el resultado se anuncia`, async ({ page }) => {
    let llamadas = 0;
    await page.route(API, (r) => (++llamadas === 1 ? r.fulfill(error(503, 'autenticacion_no_disponible')) : segunda(r)));
    await page.goto('/app/perfil');
    // La region viva es unica, estable y existe antes de cualquier texto.
    const region = page.locator('bugalu-perfil [data-anuncio][role="status"]');
    await expect(region).toHaveCount(1);
    await expect(page.getByText('Servicio no disponible').first()).toBeVisible();

    const boton = page.getByRole('button', { name: 'Reintentar' });
    await boton.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText(texto).first()).toBeVisible();

    expect(await destino(page)).toEqual({ etiqueta: 'H2', texto: 'Tus datos' });
    await expect(region).toContainText(nombre.endsWith('401') ? texto : 'Perfil cargado');
    // Un solo anunciador: el aviso clonado no duplica su rol vivo.
    await expect(page.locator('bugalu-perfil [data-salida] [role="alert"], bugalu-perfil [data-salida] [role="status"]')).toHaveCount(0);
    expect(llamadas).toBe(2);
  });
}

test('identificacion coherente: navegacion, h1 y title de /app/ dicen Inicio', async ({ page }) => {
  await page.goto('/app/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Inicio');
  expect(await page.title()).toBe('Inicio · Bugalú Studio');
  await expect(page.getByRole('navigation').getByRole('link', { name: 'Inicio' }).first()).toHaveAttribute('href', '/app/');
});

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`orden de lectura del encabezado: titulo, descripcion, acciones (${viewport.width}px)`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/catalogo');
    const orden = await page.evaluate(() => {
      const e = document.querySelector('.encabezado-app');
      const hijos = ['.encabezado-titulo', '.encabezado-descripcion', '.encabezado-acciones'].map((s) => e.querySelector(s));
      return hijos.map((h, i) => (i === 0 ? 0 : hijos[i - 1].compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING ? 1 : -1));
    });
    expect(orden).toEqual([0, 1, 1]);
    // La posicion visual no cambia: las acciones quedan sobre el titulo.
    const y = await page.evaluate(() => {
      const e = document.querySelector('.encabezado-app');
      const t = (s) => e.querySelector(s).getBoundingClientRect().top;
      return { titulo: t('.encabezado-titulo'), acciones: t('.encabezado-acciones') };
    });
    if (viewport.width > 600) expect(y.acciones).toBeLessThan(y.titulo);
  });
}

test.describe('objetivos tactiles (390 px)', () => {
  test.use({ viewport: { width: 390, height: 844 } });
  const minimo = (page) => page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize) * 2.75);

  test('Mi perfil del menu y la accion del aviso miden medida-control-tactil', async ({ page }) => {
    await page.route(API, (r) => r.fulfill(error(401, 'no_autenticado')));
    await page.goto('/app/perfil');
    const accion = page.getByRole('link', { name: 'Ir al acceso' });
    await expect(accion).toBeVisible();
    await page.locator('summary').click();
    const enlace = page.getByRole('link', { name: 'Mi perfil' });
    const min = await minimo(page);
    for (const l of [accion, enlace]) expect((await l.boundingBox()).height).toBeGreaterThanOrEqual(min);
  });
});
