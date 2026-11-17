// RF-20 (CA-08, CA-09, CA-10): registro de cambios del Administrador. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const CAMBIOS = [
  { id: 'c1', cambiado_en: '2026-11-16T13:00:00Z', autor: { id: 'a1', nombre: 'Ana Pérez' }, recurso: 'servicio', id_recurso: 's1', nombre_recurso: 'Grabación de voces', campo: 'tarifa_hora', anterior: '120.00', nuevo: '150.00' },
  { id: 'c2', cambiado_en: '2026-11-12T20:30:00Z', autor: { id: 'a1', nombre: 'Ana Pérez' }, recurso: 'impuestos', id_recurso: null, nombre_recurso: 'IGV', campo: 'precios_incluyen_igv', anterior: 'true', nuevo: 'false' },
  { id: 'c3', cambiado_en: '2026-10-20T15:05:00Z', autor: { id: 'a2', nombre: 'Luis Rojas' }, recurso: 'parametros', id_recurso: null, nombre_recurso: 'Parámetros de reserva', campo: 'minutos_tolerancia_inasistencia', anterior: '15', nuevo: '20' },
  { id: 'c4', cambiado_en: '2026-10-19T15:05:00Z', autor: { id: 'a2', nombre: 'Luis Rojas' }, recurso: 'recargos', id_recurso: null, nombre_recurso: 'Recargos', campo: 'noche.porcentaje', anterior: '25.00', nuevo: '30.50' },
  { id: 'c5', cambiado_en: '2026-10-18T15:05:00Z', autor: { id: 'a2', nombre: 'Luis Rojas' }, recurso: 'especialista', id_recurso: 'e1', nombre_recurso: 'Ingeniero de sonido', campo: 'campo_nuevo', anterior: 'a', nuevo: 'b' },
];

async function base(page, respuesta = json(200, CAMBIOS)) {
  await page.clock.setFixedTime(new Date('2026-11-16T15:00:00Z')); // 10:00 en Lima
  await comoAdministrador(page);
  return simular(page, 'GET', '/registro-cambios', respuesta);
}
const sinReintento = (page) => expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);

for (const t of tamanos) {
  test(`registro: tabla con fecha, autor, recurso, campo, antes y despues a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await base(page);
    await page.goto('/app/cambios');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/registro de cambios/i);
    await expect(page.getByText('[A9] CONTROL / CAMBIOS')).toBeVisible();
    await expect(page.getByText('Nadie puede editar ni borrar este registro.')).toBeVisible();
    const tabla = page.getByRole('table', { name: 'Cambios del 17 oct al 16 nov' });
    await expect(tabla.getByRole('row')).toHaveCount(CAMBIOS.length + 1);
    const fila1 = tabla.getByRole('row').nth(1);
    await expect(fila1).toContainText('hace 2 h'); // < 7 dias: relativa, con la absoluta en title
    await expect(fila1.locator('time')).toHaveAttribute('title', '16 nov 2026, 08:00');
    await expect(fila1).toContainText('Ana Pérez');
    await expect(fila1).toContainText('Grabación de voces');
    await expect(fila1).toContainText('SERVICIO');
    await expect(fila1).toContainText('TARIFA POR HORA');
    await expect(fila1).toContainText('S/ 120,00');
    await expect(fila1).toContainText('S/ 150,00');
    await expect(tabla.getByRole('row').nth(2)).toContainText('hace 3 días');
    await expect(tabla.getByRole('row').nth(2)).toContainText('LOS PRECIOS INCLUYEN IGV');
    await expect(tabla.getByRole('row').nth(2)).toContainText('Sí');
    await expect(tabla.getByRole('row').nth(2)).toContainText('No');
    await expect(tabla.getByRole('row').nth(3)).toContainText('20 oct 2026, 10:05'); // >= 7 dias: absoluta
    await expect(tabla.getByRole('row').nth(3)).toContainText('TOLERANCIA DE INASISTENCIA');
    await expect(tabla.getByRole('row').nth(3)).toContainText('15 min');
    await expect(tabla.getByRole('row').nth(3)).toContainText('PARÁMETROS');
    await expect(tabla.getByRole('row').nth(4)).toContainText('NOCHE (%)');
    await expect(tabla.getByRole('row').nth(4)).toContainText('30,5 %');
    await expect(tabla.getByRole('row').nth(5)).toContainText('CAMPO_NUEVO'); // campo desconocido: el nombre tal cual
    await expect(tabla.getByRole('row').nth(5)).toContainText('ESPECIALISTA');
    await expect(page.getByRole('status')).toHaveText('5 cambios del 17 oct al 16 nov');
    expect(vistas[0].url.searchParams.has('recurso')).toBe(false);
    await expect(page.getByRole('link', { name: 'Ver los últimos 30 días' })).toHaveCount(0);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/registro-cambios-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('registro: a 1440 las celdas no repiten el rotulo de tarjeta; a 390 si', async ({ page }) => {
  await base(page);
  for (const [ancho, contenido] of [[1440, 'none'], [390, '"Autor"']]) {
    await page.setViewportSize({ width: ancho, height: 900 });
    await page.goto('/app/cambios');
    const celda = page.getByRole('table').getByRole('row').nth(1).getByRole('cell').first();
    expect(await celda.evaluate((e) => getComputedStyle(e, '::before').content)).toBe(contenido);
  }
});

test('registro: los filtros de la URL llegan a la API y rellenan el formulario', async ({ page }) => {
  const vistas = await base(page);
  await page.goto('/app/cambios?recurso=servicio&desde=2026-11-01&hasta=2026-11-16');
  await expect(page.getByLabel('Desde')).toHaveValue('2026-11-01');
  await expect(page.getByLabel('Hasta')).toHaveValue('2026-11-16');
  await expect(page.getByLabel('Recurso')).toHaveValue('servicio');
  expect(vistas[0].url.searchParams.get('recurso')).toBe('servicio');
  expect(vistas[0].url.searchParams.get('desde')).toBe('2026-11-01');
  expect(vistas[0].url.searchParams.get('hasta')).toBe('2026-11-16');
  await expect(page.getByRole('link', { name: 'Ver los últimos 30 días' })).toHaveAttribute('href', '/app/cambios');
});

test('registro: Filtrar es un formulario GET con teclado y deja el filtro en la URL', async ({ page }) => {
  await base(page);
  await page.goto('/app/cambios');
  await page.getByLabel('Recurso').selectOption('parametros');
  await page.getByLabel('Desde').focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/app\/cambios\?desde=2026-10-17&hasta=2026-11-16&recurso=parametros$/);
  await page.getByLabel('Recurso').focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Filtrar' })).toBeFocused();
});

test('registro: sin cambios en el periodo por defecto', async ({ page }) => {
  await base(page, json(200, []));
  await page.goto('/app/cambios');
  await expect(page.getByText('No hay cambios en los últimos 30 días')).toBeVisible();
  await expect(page.getByText('Aquí aparece cada cambio de impuestos, tarifas, recargos y plazos, con quién lo hizo.')).toBeVisible();
  await expect(page.getByLabel('Desde')).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('0 cambios del 17 oct al 16 nov');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/registro-cambios-vacio-1440.png', fullPage: true });
});

test('registro: sin resultados con filtro ofrece volver a los ultimos 30 dias', async ({ page }) => {
  await base(page, json(200, []));
  await page.goto('/app/cambios?recurso=recargos');
  await expect(page.getByText('No hay cambios con estos filtros.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver los últimos 30 días' })).toHaveAttribute('href', '/app/cambios');
  await sinViolaciones(page);
});

test('registro: filtros desconocidos en la URL se ignoran con un aviso', async ({ page }) => {
  const vistas = await base(page);
  await page.goto('/app/cambios?recurso=zzz&desde=ayer&hasta=2026-11-16');
  await expect(page.getByText('El enlace traía un filtro no válido. Te mostramos los últimos 30 días.')).toBeVisible();
  expect(vistas[0].url.searchParams.has('recurso')).toBe(false);
  expect(vistas[0].url.searchParams.has('desde')).toBe(false);
  await expect(page.getByLabel('Recurso')).toHaveValue('');
  await expect(page.getByLabel('Desde')).toHaveValue('2026-10-17');
  await sinViolaciones(page);
});

test('registro: HASTA anterior a DESDE o mas de 366 dias no se envia y marca el campo', async ({ page }) => {
  const vistas = await base(page);
  await page.goto('/app/cambios');
  await page.getByLabel('Desde').fill('2026-11-10');
  await page.getByLabel('Hasta').fill('2026-11-01');
  await page.getByRole('button', { name: 'Filtrar' }).click();
  const error = 'Elige una fecha final igual o posterior a la inicial, con hasta 366 días de diferencia.';
  await expect(page.getByLabel('Hasta')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText(error)).toHaveCount(1);
  await expect(page.locator('.aviso-error')).toBeFocused();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/registro-cambios-error-rango-1440.png', fullPage: true });
  await page.getByLabel('Desde').fill('2025-01-01');
  await page.getByLabel('Hasta').fill('2026-11-16');
  await page.getByRole('button', { name: 'Filtrar' }).click();
  await expect(page.getByLabel('Hasta')).toHaveAttribute('aria-invalid', 'true');
  expect(vistas).toHaveLength(1); // solo la carga inicial
});

test('registro: 422 rango_invalido de la API se muestra bajo HASTA', async ({ page }) => {
  await base(page, errorApi(422, 'rango_invalido'));
  await page.goto('/app/cambios?desde=2026-11-01&hasta=2026-11-16');
  await expect(page.getByLabel('Hasta')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText('Elige una fecha final igual o posterior a la inicial, con hasta 366 días de diferencia.').first()).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
});

for (const f of fallos) {
  test(`registro: respuesta ${f.n} al cargar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoAdministrador(page);
    await simular(page, 'GET', '/registro-cambios', f.r);
    await page.goto('/app/cambios?recurso=servicio');
    await expect(page.getByRole('main')).toContainText(f.texto);
    if (f.extra) await expect(page.getByRole('main')).toContainText(f.extra);
    if (f.enlace) await expect(page.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1]('/app/cambios?recurso=servicio'));
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/registro-cambios-error-${f.n}-1440.png`, fullPage: true });
  });
}

test('registro: Reintentar vuelve a pedir y pinta la tabla', async ({ page }) => {
  await comoAdministrador(page);
  let n = 0;
  await simular(page, 'GET', '/registro-cambios', (r) => (n++ === 0 ? r.fulfill(errorApi(503, 'x')) : r.fulfill(json(200, CAMBIOS))));
  await page.goto('/app/cambios');
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('table')).toBeVisible();
  await sinReintento(page);
});

test('registro: la carga muestra Cargando con aria-busy', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/registro-cambios', async (r) => { await new Promise((x) => setTimeout(x, 600)); await r.fulfill(json(200, CAMBIOS)); });
  await page.goto('/app/cambios');
  await expect(page.getByText('Cargando…').first()).toBeVisible();
  await expect(page.locator('[aria-busy="true"]').first()).toBeVisible();
  await expect(page.getByRole('table')).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('/app/cambios explica que hace falta JS', async ({ page }) => {
    await page.goto('/app/cambios');
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
    await expect(page.locator('bugalu-registro-cambios [data-salida]')).toBeHidden();
    await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
    await expect(page.getByText('Cargando…')).toBeHidden();
    await page.screenshot({ path: 'pruebas/capturas/registro-cambios-sin-js-1440.png', fullPage: true });
  });
});

test('navegacion: CAMBIOS con icono history, actual en el registro (escritorio)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto('/app/cambios');
  const enlace = page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Cambios' });
  await expect(enlace).toHaveAttribute('href', '/app/cambios/');
  await expect(enlace).toHaveAttribute('aria-current', 'page');
  await expect(enlace.locator('svg path').first()).toHaveAttribute('d', 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8');
});

test('navegacion: CAMBIOS en el menu del movil, con aria-current en su pantalla', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await base(page);
  await page.goto('/app/cambios');
  await page.getByText('Menú', { exact: true }).click();
  const enlace = page.locator('.cabecera-menu-panel').getByRole('link', { name: 'Cambios' });
  await expect(enlace).toHaveAttribute('href', '/app/cambios/');
  await expect(enlace).toHaveAttribute('aria-current', 'page');
  await sinViolaciones(page);
});

test('navegacion: un cliente no ve CAMBIOS', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.route('http://api.prueba/api/v1/perfil', (r) => r.fulfill(json(200, { id: 'u1', correo: 'a@b.com', correo_confirmado: true, nombre: 'Ana', telefono: null, nombre_artistico: null, rol: 'cliente', especialidad: null })));
  await page.goto('/app/');
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Reservas' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Cambios' })).toBeHidden();
});
