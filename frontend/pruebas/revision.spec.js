// TAREA-404: ajustes de la revisión visual de la fase 4 (fichas actualizadas en 4701905).
import { test, expect } from '@playwright/test';
import { ORIGEN } from './puertos.js';

const anchos = [
  { nombre: 'escritorio', width: 1440, height: 900 },
  { nombre: 'movil', width: 390, height: 844 },
];

// Bloqueante 1: la placa móvil lleva el icono; el apilado solo desde 64 em.
test('cabecera: placa con icono en móvil y apilado en escritorio', async ({ page }) => {
  const viewBox = () => page.locator('.cabecera-estudio .cabecera-placa svg:visible').first().getAttribute('viewBox');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/catalogo');
  expect(await viewBox()).toBe('0 0 36 36');
  await page.setViewportSize({ width: 1440, height: 900 });
  expect(await viewBox()).toBe('0 0 94 86');
});

// Ajuste 3: main no muestra anillo; el enlace de salto sí.
for (const ruta of ['/', '/app/']) {
  test(`${ruta}: el foco en main no dibuja anillo`, async ({ page }) => {
    await page.goto(ruta);
    await page.keyboard.press('Tab');
    expect(await page.getByRole('link', { name: 'Saltar al contenido' }).evaluate((e) => getComputedStyle(e).outlineStyle)).toBe('solid');
    await page.keyboard.press('Enter');
    const main = page.locator('main#contenido');
    await expect(main).toBeFocused();
    expect(await main.evaluate((e) => getComputedStyle(e).outlineStyle)).toBe('none');
  });
}

// Ajuste 5: aviso descartable como isla.
test('aviso descartable: sin JS no hay botón; con JS cierra y el foco va a #contenido', async ({ page, browser }) => {
  await page.goto('/catalogo');
  const aviso = page.locator('bugalu-aviso');
  const cerrar = aviso.getByRole('button', { name: 'Cerrar aviso' });
  await expect(cerrar).toBeVisible();
  await cerrar.click();
  await expect(aviso).toHaveCount(0);
  await expect(page.locator('#contenido')).toBeFocused();

  const sinJs = await browser.newContext({ javaScriptEnabled: false });
  const paginaSinJs = await sinJs.newPage();
  await paginaSinJs.goto(`${ORIGEN}/catalogo`);
  await expect(paginaSinJs.getByText('Aviso descartable')).toBeVisible();
  await expect(paginaSinJs.getByRole('button', { name: 'Cerrar aviso' })).toHaveCount(0);
  await sinJs.close();
});

// Ajuste 6: borde parcial del panel técnico del mismo grosor que el contorno.
test('panel técnico: borde izquierdo de borde-grosor-base', async ({ page }) => {
  await page.goto('/catalogo');
  const ancho = await page.locator('.panel-tecnico').evaluate((e) => getComputedStyle(e).borderInlineStartWidth);
  expect(ancho).toBe('2px');
});

for (const { nombre, ...viewport } of anchos) {
  test.describe(`${nombre} ${viewport.width}px`, () => {
    test.use({ viewport });

    // Ajuste 7: un solo menú de perfil, alcanzable con teclado.
    test('menú de perfil: un solo details, se abre con teclado y llega a Mi perfil', async ({ page }) => {
      await page.goto('/app/');
      await expect(page.locator('.cabecera-menu')).toHaveCount(1);
      await expect(page.locator('.cabecera-usuario-escritorio')).toHaveCount(0);
      const resumen = page.locator('.cabecera-menu > summary');
      await resumen.focus();
      await page.keyboard.press('Enter');
      await expect(page.locator('.cabecera-menu')).toHaveAttribute('open', '');
      await page.keyboard.press('Tab');
      const perfil = page.getByRole('link', { name: 'Mi perfil' });
      await expect(perfil).toBeFocused();
      await expect(perfil).toHaveAttribute('href', '/app/perfil');
      await page.screenshot({ path: `pruebas/capturas/app-${nombre}-menu.png` });
    });

    // Ajuste 9: el banner sigue en el árbol (display: contents en móvil).
    test('el banner de la cabecera es visible', async ({ page }) => {
      await page.goto('/app/');
      await expect(page.getByRole('banner')).toBeVisible();
    });

    // Ajuste 11: etiquetas de navegación de 9 caracteres como máximo.
    test('etiquetas de navegación de 9 caracteres como máximo', async ({ page }) => {
      for (const ruta of ['/app/', '/catalogo']) {
        await page.goto(ruta);
        const etiquetas = await page.locator('.tactil-etiqueta, .lateral-etiqueta').allTextContents();
        expect(etiquetas.length).toBeGreaterThan(0);
        for (const e of etiquetas) expect(e.trim().length, e).toBeLessThanOrEqual(9);
      }
    });
  });
}

// Ajuste 7 (escritorio): el summary muestra el nombre y el panel abre a la derecha con sombra plana.
test('escritorio: el summary del perfil muestra el nombre y el panel lleva sombra plana', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/catalogo');
  const menu = page.locator('.cabecera-estudio .cabecera-menu');
  await expect(menu.locator('summary')).toContainText('Marta Quispe');
  await menu.locator('summary').click();
  const panel = menu.locator('.cabecera-menu-panel');
  expect(await panel.evaluate((e) => getComputedStyle(e).boxShadow)).not.toBe('none');
  const [p, m] = await Promise.all([panel.boundingBox(), menu.locator('summary').boundingBox()]);
  expect(p.x + p.width).toBeCloseTo(m.x + m.width, 0); // alineado a la derecha del botón
});

// Ajuste 8: la marca del flujo va a inicio público.
test('cabecera Flujo: la marca enlaza a /', async ({ page }) => {
  await page.goto('/catalogo');
  await expect(page.locator('.cabecera-flujo .cabecera-marca')).toHaveAttribute('href', '/');
  await expect(page.locator('.cabecera-estudio .cabecera-marca')).toHaveAttribute('href', '/app/');
});

// Ajuste 10: la navegación lateral llega al pie de la ventana.
test('escritorio: la regla de la navegación lateral llega al pie', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/app/');
  const pie = await page.locator('.lateral').evaluate((e) => e.getBoundingClientRect().bottom);
  expect(pie).toBeGreaterThanOrEqual(900 - 1);
});
