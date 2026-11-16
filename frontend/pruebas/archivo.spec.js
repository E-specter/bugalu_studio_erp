// Componentes Archivo y CargaArchivos (variante captura) en el catálogo de desarrollo; axe y desbordes los cubre componentes.spec.js.
import { test, expect } from '@playwright/test';
import { sinViolaciones } from './ayudas-acceso.js';

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

test('Archivo: adjunto con icono o miniatura, descarga y lectura', async ({ page }) => {
  await page.goto('/catalogo');
  const grupo = page.locator('section[aria-labelledby="g-archivo"]');
  await expect(grupo.getByRole('heading', { name: 'Archivo', level: 2 })).toBeVisible();
  await expect(grupo.getByRole('button', { name: 'Quitar comprobante-yape.pdf' })).toBeVisible();
  const mini = grupo.getByRole('img', { name: 'Vista previa de captura-de-pago.png' });
  expect(await mini.evaluate((e) => [getComputedStyle(e).objectFit, e.getBoundingClientRect().width])).toEqual(['contain', 96]);
  await expect(grupo.locator('.archivo-adjunto').first().locator('.archivo-visual svg')).toBeVisible(); // PDF: icono de archivo
  expect(await grupo.locator('.archivo-nombre').nth(2).getAttribute('title')).toContain('MUY_LARGO');
  await expect(grupo.getByRole('link', { name: 'Descargar CYBERNETIC_MIX_V3.wav en WAV (54 MB)' })).toHaveAttribute('download', '');
  const abrir = grupo.getByRole('link', { name: 'Abrir comprobante.pdf (pestaña nueva)' });
  await expect(abrir).toHaveAttribute('target', '_blank');
  await expect(abrir).toHaveAttribute('rel', /noopener/);
  expect((await grupo.getByRole('button', { name: /Quitar/ }).first().boundingBox()).width).toBeGreaterThanOrEqual(24);
});

test('CargaArchivos captura: input real en el formulario, botón, adjunto, quitar y foco', async ({ page }) => {
  await page.goto('/catalogo');
  const grupo = page.locator('section[aria-labelledby="g-carga"]');
  const entrada = grupo.locator('input[type="file"][name="captura"]');
  await expect(entrada).toHaveAttribute('accept', 'image/jpeg,image/png,application/pdf');
  await expect(entrada.locator('xpath=ancestor::form')).toHaveAttribute('enctype', 'multipart/form-data');
  await expect(grupo.getByText('Seleccionar archivo')).toBeVisible();
  await expect(grupo.getByText('JPG, PNG o PDF, hasta 5 MB.')).toBeVisible();
  await page.keyboard.press('Tab'); // la primera parada de la página no es el input; se enfoca a mano para ver el anillo
  await entrada.focus();
  expect(await grupo.locator('.carga-boton').evaluate((e) => getComputedStyle(e).outlineStyle)).toBe('solid');
  await entrada.setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await expect(grupo.getByText('Seleccionar archivo')).toBeHidden();
  await expect(grupo.getByRole('img', { name: 'Vista previa de la captura voucher.png' })).toBeVisible();
  await sinViolaciones(page);
  await grupo.getByRole('button', { name: 'Quitar voucher.png' }).click();
  await expect(entrada).toBeFocused();
  await expect(grupo.getByText('Seleccionar archivo')).toBeVisible();
  expect(await entrada.evaluate((e) => e.files.length)).toBe(0);
  await page.screenshot({ path: 'pruebas/capturas/carga-archivos-captura.png', fullPage: false });
});

test('CargaArchivos captura sin JS: queda el input nativo dentro del formulario', async ({ browser }) => {
  const contexto = await browser.newContext({ javaScriptEnabled: false });
  const page = await contexto.newPage();
  await page.goto('/catalogo');
  await expect(page.locator('input[type="file"][name="captura"]')).toBeVisible();
  await contexto.close();
});
