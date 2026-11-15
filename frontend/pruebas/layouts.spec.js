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
