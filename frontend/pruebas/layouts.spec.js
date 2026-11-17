import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const paginas = [
  { nombre: 'publico', ruta: '/' },
  { nombre: 'app', ruta: '/app/' },
];
const anchos = [
  { nombre: 'escritorio', width: 1440, height: 900 },
  { nombre: 'movil', width: 390, height: 844 },
];

for (const { nombre, ruta } of paginas) {
  for (const { nombre: dispositivo, ...viewport } of anchos) {
    test.describe(`${nombre} ${viewport.width}px`, () => {
      test.use({ viewport });

      test.beforeEach(({ page }) => page.goto(ruta));

      test('sin violaciones axe WCAG 2.2 AA', async ({ page }) => {
        const { violations } = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
          .analyze();
        expect(violations).toEqual([]);
      });

      // N1: la captura de pagina completa dibujaba el enlace (fijo, solo desplazado) encima de la pagina; sin foco no debe pintarse.
      test('Saltar al contenido sin foco no se pinta y con foco si', async ({ page }) => {
        const saltar = page.getByRole('link', { name: 'Saltar al contenido' });
        const recorte = () => saltar.evaluate((e) => getComputedStyle(e).clipPath);
        expect(await recorte()).toBe('inset(50%)');
        await page.keyboard.press('Tab');
        expect(await recorte()).toBe('none');
      });

      test('Saltar al contenido funciona y el foco es visible', async ({ page }) => {
        await page.keyboard.press('Tab');
        const saltar = page.getByRole('link', { name: 'Saltar al contenido' });
        await expect(saltar).toBeFocused();
        await expect(saltar).toBeInViewport({ ratio: 1 });
        // Foco visible: anillo de 2px (borde-grosor-base) en el primer elemento enfocado.
        const anillo = await saltar.evaluate((e) => getComputedStyle(e).outlineWidth);
        expect(anillo).toBe('2px');
        await page.screenshot({ path: `pruebas/capturas/${nombre}-${dispositivo}-foco.png` });

        await page.keyboard.press('Enter');
        await expect(page.locator('main#contenido')).toBeFocused();
        await page.screenshot({ path: `pruebas/capturas/${nombre}-${dispositivo}.png`, fullPage: true });
      });
    });
  }
}

// N3: el pie y el <main> comparten margen izquierdo del contenido (una sola reticula).
for (const { nombre, ...viewport } of anchos) {
  test(`publico ${viewport.width}px: el contenido del pie empieza donde el del main`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const inicio = (sel) => page.locator(sel).evaluate((e) => e.getBoundingClientRect().left + parseFloat(getComputedStyle(e).paddingLeft));
    expect(await inicio('.pie-contenido')).toBeCloseTo(await inicio('main#contenido'), 0);
  });
}

// N4: al partirse en filas, la altura tactil de cada enlace ya las separa: sin separacion extra entre filas.
test('pie: los enlaces no suman separacion entre filas', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/acceso/');
  const filas = await page.locator('.pie-enlaces').evaluate((e) => getComputedStyle(e).rowGap);
  expect(['0px', 'normal']).toContain(filas);
});

// N5: las tres filas de contacto miden lo mismo (el objetivo tactil esta en la fila, no solo en el enlace).
test('contacto del estudio: filas de igual altura', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/libro-de-reclamaciones/');
  const alturas = await page.locator('.contacto li').evaluateAll((l) => l.map((e) => Math.round(e.getBoundingClientRect().height)));
  expect(alturas.length).toBeGreaterThanOrEqual(3);
  expect(new Set(alturas).size).toBe(1);
});
