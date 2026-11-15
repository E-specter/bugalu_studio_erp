import { test, expect } from '@playwright/test';
import { sinViolaciones } from './ayudas-acceso.js';

const condiciones = [
  { id: 'longitud', texto: 'Al menos 8 caracteres', cumple: 'Abc1!xy', sinCumplir: 'Abc1!xyz', fallaCon: 'Abc1!xy' },
  { id: 'minuscula', texto: 'Una minúscula (a-z)', fallaCon: 'ABCDEFG1!' },
  { id: 'mayuscula', texto: 'Una mayúscula (A-Z)', fallaCon: 'abcdefg1!' },
  { id: 'numero', texto: 'Un número (0-9)', fallaCon: 'Abcdefgh!' },
  { id: 'simbolo', texto: 'Un símbolo, como ! ? # $ % ', fallaCon: 'Abcdefg1' },
];
const valida = 'Abcdefg1!'; // 9 caracteres: nivel media

test.beforeEach(async ({ page }) => {
  await page.goto('/acceso/registro');
});

const fila = (page, id) => page.locator(`[data-condicion="${id}"]`);

test('medidor: sin evaluar y las cinco condiciones pendientes con texto', async ({ page }) => {
  await expect(page.getByText('Robustez: sin evaluar')).toBeVisible();
  for (const c of condiciones) {
    await expect(fila(page, c.id)).toContainText(c.texto.trim());
    await expect(fila(page, c.id)).toContainText(': pendiente');
  }
  // El icono es decorativo.
  await expect(fila(page, 'longitud').locator('svg[aria-hidden="true"]')).toHaveCount(1);
  await sinViolaciones(page);
});

for (const c of condiciones) {
  test(`medidor: la condicion ${c.id} se marca sola y por texto`, async ({ page }) => {
    const campo = page.getByLabel('Contraseña', { exact: true });
    await campo.fill(c.fallaCon);
    await expect(fila(page, c.id)).toContainText(': pendiente');
    for (const otra of condiciones.filter((o) => o.id !== c.id)) await expect(fila(page, otra.id)).toContainText(': cumplida');
    await expect(page.getByText('Robustez: débil')).toBeVisible();
    await campo.fill(valida);
    await expect(fila(page, c.id)).toContainText(': cumplida');
  });
}

test('medidor: la ñ y las tildes no cuentan como minúscula ni mayúscula', async ({ page }) => {
  await page.getByLabel('Contraseña', { exact: true }).fill('ÑÁÉÍ1234!');
  await expect(fila(page, 'minuscula')).toContainText(': pendiente');
  await expect(fila(page, 'mayuscula')).toContainText(': pendiente');
  await page.getByLabel('Contraseña', { exact: true }).fill('ñáéíó1234!');
  await expect(fila(page, 'minuscula')).toContainText(': pendiente');
});

test('medidor: niveles debil, media y fuerte', async ({ page }) => {
  const campo = page.getByLabel('Contraseña', { exact: true });
  await campo.fill('abc');
  await expect(page.getByText('Robustez: débil')).toBeVisible();
  await campo.fill('Abcdefg1!'); // 9
  await expect(page.getByText('Robustez: media')).toBeVisible();
  await campo.fill('Abcdefghijk1!'); // 13
  await expect(page.getByText('Robustez: fuerte')).toBeVisible();
  await campo.fill('');
  await expect(page.getByText('Robustez: sin evaluar')).toBeVisible();
});

test('medidor: el nivel no depende solo del color (texto y tono del indicador)', async ({ page }) => {
  const campo = page.getByLabel('Contraseña', { exact: true });
  await campo.fill('Abcdefghijk1!');
  await expect(page.locator('[data-nivel] .indicador-correcto')).toBeVisible();
  await campo.fill('abc');
  await expect(page.locator('[data-nivel] .indicador-problema')).toBeVisible();
  await sinViolaciones(page);
});

test('medidor: anuncio solo del nivel, tras 1 s sin escribir y nunca en cada pulsacion', async ({ page }) => {
  const vivo = page.locator('[data-anuncio]').first();
  await expect(vivo).toHaveAttribute('role', 'status');
  await expect(vivo).toHaveText('');
  await page.evaluate(() => {
    window.__anuncios = [];
    const v = document.querySelector('[data-anuncio]');
    new MutationObserver(() => v.textContent && window.__anuncios.push(v.textContent)).observe(v, { childList: true, characterData: true, subtree: true });
  });
  const campo = page.getByLabel('Contraseña', { exact: true });
  await campo.click();
  await campo.pressSequentially('Abcdefg1!', { delay: 60 });
  // Sigue tecleando (menos de 1 s desde la ultima pulsacion): ningun anuncio.
  expect(await page.evaluate(() => window.__anuncios)).toEqual([]);
  await expect(vivo).toHaveText('Robustez media', { timeout: 3000 });
  expect(await page.evaluate(() => window.__anuncios)).toEqual(['Robustez media']);
  // Mismo nivel tras otra pulsacion: no se repite.
  await campo.pressSequentially('x', { delay: 60 });
  await page.waitForTimeout(1300);
  expect(await page.evaluate(() => window.__anuncios)).toEqual(['Robustez media']);
  // Cambia a fuerte: se anuncia solo el nivel nuevo.
  await campo.pressSequentially('yzabc', { delay: 60 });
  await expect(vivo).toHaveText('Robustez fuerte', { timeout: 3000 });
  expect(await page.evaluate(() => window.__anuncios)).toEqual(['Robustez media', 'Robustez fuerte']);
});

test('medidor: al salir del campo anuncia sin esperar el segundo', async ({ page }) => {
  const campo = page.getByLabel('Contraseña', { exact: true });
  await campo.fill('Abcdefg1!');
  await page.getByLabel('Nombre', { exact: true }).focus();
  await expect(page.locator('[data-anuncio]').first()).toHaveText('Robustez media', { timeout: 500 });
});

test('medidor: la entrada se describe con la ayuda y no con la lista', async ({ page }) => {
  const campo = page.getByLabel('Contraseña', { exact: true });
  const ids = (await campo.getAttribute('aria-describedby')).split(' ');
  expect(ids.length).toBe(1);
  await expect(page.locator(`#${ids[0]}`)).toContainText('Mínimo 8 caracteres con minúscula, mayúscula, número y símbolo.');
});

test('mostrar contraseña: nombre fijo y aria-pressed', async ({ page }) => {
  const boton = page.getByRole('button', { name: 'Mostrar contraseña' });
  await boton.click();
  await expect(boton).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByLabel('Contraseña', { exact: true })).toHaveAttribute('type', 'text');
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('medidor: la lista se ve como requisitos, sin nivel ni iconos', async ({ page }) => {
    // En las pantallas de acceso el formulario entero se oculta sin JS; el catalogo muestra el campo suelto.
    await page.goto('/catalogo');
    await expect(page.getByText('Al menos 8 caracteres')).toBeVisible();
    await expect(page.locator('[data-nivel]')).toBeHidden();
    await expect(page.locator('[data-condicion] svg')).toHaveCount(0);
  });
});
