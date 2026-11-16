// RF-05 (CA-05, CA-06, CA-08, CA-09, CA-10): pagos del Administrador, datos para pagar y destino PAGOS. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos, API } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const ID1 = '3f2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e6f';
const ID2 = '4a2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e70';
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const pago = (extra = {}) => ({
  id: ID1, estado: 'pendiente_validacion', metodo: 'yape', monto: '225.00', numero_operacion: 'ABC123', motivo_rechazo: null,
  registrado_en: '2026-11-15T12:00:00Z', validado_en: null, monto_coincide: true,
  cuota: { id: 'c1', hito: 'al_reservar', monto: '225.00' },
  reserva: { id: 'r1', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'pre_reservada' },
  cliente: { id: 'u9', nombre: 'Ana Pérez' }, ...extra,
});
const POR_VALIDAR = [pago(), pago({ id: ID2, metodo: 'plin', monto: '100.00', monto_coincide: false, numero_operacion: 'XYZ-9', reserva: { id: 'r2', folio: 'R-2026-00043', inicio: '2026-11-21T15:00:00Z', estado: 'pre_reservada' }, cliente: { id: 'u8', nombre: null }, registrado_en: '2026-11-01T12:00:00Z' })];

async function base(page, { lista = POR_VALIDAR, aprobados = [], rechazados = [], detalle = pago(), captura } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  await comoAdministrador(page);
  const vistas = await simular(page, 'GET', '/pagos', (r) => {
    const estado = new URL(r.request().url()).searchParams.get('estado');
    return r.fulfill(json(200, estado === 'aprobado' ? aprobados : estado === 'rechazado' ? rechazados : lista));
  });
  await page.route('http://captura.prueba/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }));
  const capturas = await simular(page, 'GET', `/pagos/${ID1}/captura`, captura ?? json(200, { url: 'http://captura.prueba/c.png', expira_en: '2026-11-15T15:10:00Z', tipo: 'imagen' }));
  await simular(page, 'GET', `/pagos/${ID1}`, typeof detalle === 'function' ? detalle : json(200, detalle));
  return { vistas, capturas };
}
const tabla = (page) => page.getByRole('table', { name: 'Pagos' }).getByRole('row');

// --- 1. Lista ---
for (const t of tamanos) {
  test(`lista: por validar por defecto, con NO COINCIDE y enlaces, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const { vistas } = await base(page);
    await page.goto('/app/pagos/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('PAGOS');
    await expect(page.getByRole('link', { name: 'Editar datos para pagar' })).toHaveAttribute('href', '/app/pagos/datos');
    await expect(page.getByRole('main').getByRole('link', { name: 'POR VALIDAR', exact: true })).toHaveAttribute('aria-current', 'true');
    await expect(page.getByRole('main').getByRole('link', { name: 'APROBADOS', exact: true })).toHaveAttribute('href', '/app/pagos/?estado=aprobado');
    await expect(page.getByRole('main').getByRole('link', { name: 'RECHAZADOS', exact: true })).toHaveAttribute('href', '/app/pagos/?estado=rechazado');
    await expect(tabla(page)).toHaveCount(3);
    const f1 = tabla(page).nth(1);
    await expect(f1.getByRole('rowheader')).toContainText('R-2026-00042');
    await expect(f1.getByRole('rowheader')).toContainText('Al reservar');
    await expect(f1).toContainText('Ana Pérez');
    await expect(f1).toContainText('Yape');
    await expect(f1).toContainText('S/ 225,00');
    await expect(f1).toContainText('ABC123');
    await expect(f1).toContainText('hace 3 h');
    await expect(f1).not.toContainText('NO COINCIDE');
    const f2 = tabla(page).nth(2);
    await expect(f2).toContainText('Sin nombre');
    await expect(f2).toContainText('NO COINCIDE');
    await expect(f2).toContainText('1 nov, 07:00');
    await expect(page.getByRole('link', { name: 'Revisar pago de R-2026-00042' })).toHaveAttribute('href', `/app/pagos/revisar?id=${ID1}`);
    await expect(page.locator('bugalu-pagos [data-anuncio]')).toHaveText('2 pagos por validar');
    expect(vistas.every((v) => !v.url.searchParams.has('estado'))).toBe(true);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/pagos-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('lista: aprobados y rechazados piden su estado y muestran VALIDADO', async ({ page }) => {
  const { vistas } = await base(page, { aprobados: [pago({ estado: 'aprobado', validado_en: '2026-11-15T13:00:00Z' })] });
  await page.goto('/app/pagos/?estado=aprobado');
  await expect(page.getByRole('main').getByRole('link', { name: 'APROBADOS', exact: true })).toHaveAttribute('aria-current', 'true');
  await expect(vistas.some((v) => v.url.searchParams.get('estado') === 'aprobado')).toBe(true);
  await expect(tabla(page)).toHaveCount(2);
  await expect(page.getByRole('columnheader', { name: 'Validado' })).toHaveCount(1);
  await expect(page.locator('bugalu-pagos [data-anuncio]')).toHaveText('1 pago aprobado');
  await expect(page.getByRole('link', { name: 'Revisar pago de R-2026-00042' })).toBeVisible();
  await page.goto('/app/pagos/?estado=lo-que-sea');
  await expect(page.getByRole('main').getByRole('link', { name: 'POR VALIDAR', exact: true })).toHaveAttribute('aria-current', 'true');
});

test('lista: vacio por validar explica y no ofrece accion; aprobados ofrece volver', async ({ page }) => {
  await base(page, { lista: [] });
  await page.goto('/app/pagos/');
  await expect(page.locator('bugalu-pagos [data-salida]').getByText('No hay pagos por validar')).toBeVisible();
  await expect(page.locator('bugalu-pagos [data-salida]').getByText('Cuando un cliente registre un pago, aparecerá aquí.')).toBeVisible();
  await expect(page.getByRole('main').getByRole('link', { name: 'Ver pagos por validar' })).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pagos-lista-vacia-1440.png', fullPage: true });
  await page.goto('/app/pagos/?estado=aprobado');
  await expect(page.locator('bugalu-pagos [data-salida]').getByText('Aún no hay pagos aprobados.')).toBeVisible();
  await expect(page.getByRole('main').getByRole('link', { name: 'Ver pagos por validar' })).toHaveAttribute('href', '/app/pagos/');
});

test('lista: avisos por URL solo de la lista cerrada y se quitan de la URL', async ({ page }) => {
  await base(page);
  await page.goto('/app/pagos/?aviso=pago-rechazado');
  await expect(page.getByText('Pago rechazado. Avisamos al cliente con el motivo.')).toBeVisible();
  await expect(page.locator('.aviso-exito')).toBeFocused();
  await expect(page).not.toHaveURL(/aviso/);
  await page.goto('/app/pagos/?aviso=lo-que-sea');
  await expect(page.locator('.aviso-exito')).toHaveCount(0);
});

for (const f of fallos) {
  test(`lista: respuesta ${f.n} al cargar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await base(page);
    await simular(page, 'GET', '/pagos', f.r);
    await page.goto('/app/pagos/');
    await expect(page.getByRole('main')).toContainText(f.texto);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/app/pagos/', '/app/pagos/revisar', '/app/pagos/datos']) {
    test(`${ruta} explica que hace falta JS`, async ({ page }) => {
      await page.goto(ruta);
      expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-pagos [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await expect(page.getByText('Cargando…')).toBeHidden();
      if (ruta === '/app/pagos/') await page.screenshot({ path: 'pruebas/capturas/pagos-sin-js-1440.png', fullPage: true });
    });
  }
});

test('lista: carga con aria-busy mientras la API tarda', async ({ page }) => {
  await base(page);
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'GET', '/pagos', async (r) => { await llega; await r.fulfill(json(200, POR_VALIDAR)); });
  await page.goto('/app/pagos/');
  await expect(page.getByText('Cargando…')).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
  soltar();
  await expect(tabla(page)).toHaveCount(3);
});

// --- 2. Revisar ---
const REVISAR = `/app/pagos/revisar?id=${ID1}`;

for (const t of tamanos) {
  test(`revisar: captura, pago, reserva y decision a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await base(page, { detalle: pago({ monto: '200.00', monto_coincide: false }) });
    await page.goto(REVISAR);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('REVISAR PAGO');
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Ana Pérez · Al reservar de la reserva R-2026-00042');
    const img = page.getByRole('img', { name: 'Captura del comprobante de Ana Pérez, Yape, S/ 200,00' });
    await expect(img).toBeVisible();
    await expect(img).toHaveAttribute('src', 'http://captura.prueba/c.png');
    const abrir = page.getByRole('link', { name: 'Abrir en una pestaña nueva' });
    await expect(abrir).toHaveAttribute('target', '_blank');
    await expect(abrir).toHaveAttribute('rel', /noopener/);
    await expect(abrir).toHaveAttribute('href', 'http://captura.prueba/c.png');
    const pagoSec = page.getByRole('region', { name: /Pago$/ });
    await expect(pagoSec).toContainText('S/ 200,00');
    await expect(pagoSec).toContainText('NO COINCIDE');
    await expect(pagoSec).toContainText('La cuota es de S/ 225,00.');
    await expect(pagoSec).toContainText('ABC123');
    const reserva = page.getByRole('region', { name: /Reserva$/ });
    await expect(reserva.getByRole('link', { name: 'R-2026-00042' })).toHaveAttribute('href', '/app/reservas/detalle?id=r1');
    await expect(reserva).toContainText('Pre-reservada');
    await expect(reserva).toContainText('Al reservar');
    await expect(page.getByText('Al aprobar, la cuota queda pagada, la reserva se confirma y avisamos al cliente. No se puede deshacer.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Aprobar pago' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Rechazar pago' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/pagos-revisar-${t.nombre}.png`, fullPage: true });
  });
}

test('revisar: orden de foco, abrir captura, folio, rechazar, aprobar', async ({ page }) => {
  await base(page);
  await page.goto(REVISAR);
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toBeVisible();
  await page.getByRole('link', { name: 'Abrir en una pestaña nueva' }).focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'R-2026-00042' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Rechazar pago' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toBeFocused();
});

test('revisar: aprobar en un clic envia POST, avisa a la navegacion y vuelve con aviso', async ({ page }) => {
  await page.addInitScript(() => document.addEventListener('bugalu:pagos-por-validar', (e) => sessionStorage.setItem('evento', JSON.stringify(e.detail))));
  await base(page);
  const aprobar = await simular(page, 'POST', `/pagos/${ID1}/aprobar`, json(200, pago({ estado: 'aprobado', reserva: { id: 'r1', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'confirmada' } })));
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(page).toHaveURL(/\/app\/pagos\/\?aviso=reserva-confirmada/);
  expect(aprobar).toHaveLength(1);
  await expect(page.getByText('Pago aprobado. La reserva quedó confirmada y avisamos al cliente.')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('evento'))).toBe('2');
});

test('revisar: aprobar una cuota que no es la de reservar usa pago-aprobado', async ({ page }) => {
  await base(page, { detalle: pago({ cuota: { id: 'c2', hito: 'al_terminar', monto: '225.00' }, reserva: { id: 'r1', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'finalizada' } }) });
  await simular(page, 'POST', `/pagos/${ID1}/aprobar`, json(200, pago({ estado: 'aprobado' })));
  await page.goto(REVISAR);
  await expect(page.getByText('Al aprobar, la cuota queda pagada y avisamos al cliente. No se puede deshacer.')).toBeVisible();
  await page.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(page).toHaveURL(/aviso=pago-aprobado/);
});

test('revisar: 409 pago_ya_validado se explica y la ficha se recarga con el resultado', async ({ page }) => {
  let n = 0;
  await base(page, { detalle: (r) => r.fulfill(json(200, ++n === 1 ? pago() : pago({ estado: 'aprobado', validado_en: '2026-11-15T14:30:00Z' }))) });
  await simular(page, 'POST', `/pagos/${ID1}/aprobar`, json(409, { error: { codigo: 'pago_ya_validado', mensaje: 'x' } }));
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(page.getByText('Este pago ya se validó, quizá desde otra sesión.')).toBeVisible();
  await expect(page.getByText('APROBADO', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toHaveCount(0);
  await sinViolaciones(page);
});

test('revisar: rechazar abre el panel con el foco en su titulo; Volver y Escape lo devuelven a Rechazar pago', async ({ page }) => {
  await base(page);
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Rechazar pago' }).click();
  const titulo = page.getByRole('heading', { name: /Rechazar pago de R-2026-00042/ });
  await expect(titulo).toBeFocused();
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Volver' }).click();
  await expect(page.getByRole('button', { name: 'Rechazar pago' }).first()).toBeFocused();
  await page.getByRole('button', { name: 'Rechazar pago' }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Rechazar pago' })).toBeFocused();
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toBeVisible();
});

test('revisar: el motivo es obligatorio, las sugerencias lo escriben y rechazar envia {motivo}', async ({ page }) => {
  await base(page);
  const rechazar = await simular(page, 'POST', `/pagos/${ID1}/rechazar`, json(200, pago({ estado: 'rechazado' })));
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Rechazar pago' }).click();
  await page.getByRole('button', { name: 'Rechazar pago' }).last().click();
  await expect(page.getByText('Escribe el motivo del rechazo.')).toBeVisible();
  await expect(page.getByLabel(/Motivo del rechazo/)).toBeFocused();
  expect(rechazar).toHaveLength(0);
  await expect(page.getByLabel(/Motivo del rechazo/)).toHaveAttribute('maxlength', '300');
  await page.getByRole('button', { name: 'Captura ilegible' }).click();
  await expect(page.getByLabel(/Motivo del rechazo/)).toHaveValue('Captura ilegible');
  await expect(page.getByLabel(/Motivo del rechazo/)).toBeFocused();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pagos-rechazar-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Rechazar pago' }).last().click();
  await expect(page).toHaveURL(/aviso=pago-rechazado/);
  expect(rechazar[0].cuerpo).toEqual({ motivo: 'Captura ilegible' });
});

test('revisar: 422 al rechazar se muestra bajo el campo y conserva el texto', async ({ page }) => {
  await base(page);
  await simular(page, 'POST', `/pagos/${ID1}/rechazar`, json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'motivo' } } }));
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Rechazar pago' }).click();
  await page.getByLabel(/Motivo del rechazo/).fill('No lo veo');
  await page.getByRole('button', { name: 'Rechazar pago' }).last().click();
  await expect(page.getByText('El motivo admite hasta 300 caracteres.')).toBeVisible();
  await expect(page.getByLabel(/Motivo del rechazo/)).toHaveValue('No lo veo');
});

for (const [estado, texto] of [['aprobado', 'APROBADO'], ['rechazado', 'RECHAZADO']]) {
  test(`revisar: pago ${estado} no ofrece acciones`, async ({ page }) => {
    await base(page, { detalle: pago({ estado, validado_en: '2026-11-15T14:30:00Z', motivo_rechazo: estado === 'rechazado' ? 'No coincide el monto' : null }) });
    await page.goto(REVISAR);
    await expect(page.getByText(texto, { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /Aprobar pago|Rechazar pago/ })).toHaveCount(0);
    if (estado === 'rechazado') await expect(page.getByText('No coincide el monto')).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/pagos-revisar-${estado}-1440.png`, fullPage: true });
  });
}

test('revisar: captura PDF con enlace a pestaña nueva', async ({ page }) => {
  await base(page, { captura: json(200, { url: 'http://captura.prueba/c.pdf', expira_en: '2026-11-15T15:10:00Z', tipo: 'pdf' }) });
  await page.goto(REVISAR);
  const enlace = page.getByRole('link', { name: /Abrir comprobante\.pdf/ });
  await expect(enlace).toHaveAttribute('href', 'http://captura.prueba/c.pdf');
  await expect(enlace).toHaveAttribute('target', '_blank');
  await expect(page.getByRole('img', { name: /Captura del comprobante/ })).toHaveCount(0);
  await sinViolaciones(page);
});

test('revisar: la captura caducada se pide de nuevo', async ({ page }) => {
  let n = 0;
  await base(page, { captura: (r) => r.fulfill(json(200, { url: 'http://captura.prueba/c.png', expira_en: ++n === 1 ? '2026-11-15T15:00:01Z' : '2026-11-15T15:10:00Z', tipo: 'imagen' })) });
  await page.goto(REVISAR);
  await expect(page.getByText('La vista de la captura caducó.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Abrir en una pestaña nueva' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Cargar captura de nuevo' }).click();
  await expect(page.getByRole('img', { name: /Captura del comprobante/ })).toBeVisible();
});

test('revisar: si la captura da 503 la decision sigue disponible', async ({ page }) => {
  await base(page, { captura: json(503, { error: { codigo: 'servicio_no_disponible', mensaje: 'x' } }) });
  await page.goto(REVISAR);
  await expect(page.getByText('No pudimos cargar la captura.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Aprobar pago' })).toBeVisible();
  await sinViolaciones(page);
});

test('revisar: id que no es UUID o 404 es no encontrado, sin pedir nada', async ({ page }) => {
  const { capturas } = await base(page);
  await page.goto('/app/pagos/revisar?id=hola');
  await expect(page.getByRole('main')).toContainText('No encontramos este pago');
  await expect(page.getByRole('link', { name: 'Volver a pagos' })).toHaveAttribute('href', '/app/pagos/');
  expect(capturas).toHaveLength(0);
  await simular(page, 'GET', `/pagos/${ID1}`, json(404, { error: { codigo: 'no_encontrado', mensaje: 'x' } }));
  await page.goto(REVISAR);
  await expect(page.getByRole('main')).toContainText('No encontramos este pago');
  await sinViolaciones(page);
});

test('revisar: 403 y 503 al cargar el pago', async ({ page }) => {
  await base(page);
  await simular(page, 'GET', `/pagos/${ID1}`, json(403, { error: { codigo: 'sin_permiso', mensaje: 'x' } }));
  await page.goto(REVISAR);
  await expect(page.getByRole('main')).toContainText('Esta sección es solo para el Administrador.');
  await simular(page, 'GET', `/pagos/${ID1}`, errorApi(503, 'servicio_no_disponible'));
  await page.goto(REVISAR);
  await expect(page.getByRole('main')).toContainText('El servicio no responde.');
});

// --- 3. Datos para pagar ---
const INSTRUCCIONES = [
  { metodo: 'transferencia', texto: 'BCP 191-0000000-0-00', activo: true },
  { metodo: 'yape', texto: '999 888 777 · Bugalú SAC', activo: true },
  { metodo: 'plin', texto: '', activo: false },
  { metodo: 'tarjeta', texto: '', activo: false },
];

async function baseDatos(page, { instrucciones = INSTRUCCIONES, contacto = { texto: 'WhatsApp 999 111 222' } } = {}) {
  await base(page);
  await simular(page, 'GET', '/instrucciones-pago', json(200, instrucciones));
  await simular(page, 'GET', '/contacto-estudio', json(200, contacto));
}
const metodo = (page, nombre) => page.getByRole('group', { name: nombre });

for (const t of tamanos) {
  test(`datos: los cuatro metodos y el contacto con su valor a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await baseDatos(page);
    await page.goto('/app/pagos/datos');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('DATOS PARA PAGAR');
    for (const n of ['Transferencia bancaria', 'Yape', 'Plin', 'Tarjeta']) await expect(metodo(page, n)).toBeVisible();
    await expect(metodo(page, 'Yape').getByRole('textbox')).toHaveValue('999 888 777 · Bugalú SAC');
    await expect(metodo(page, 'Yape').getByRole('checkbox', { name: /Activo/ })).toBeChecked();
    await expect(metodo(page, 'Plin').getByRole('checkbox', { name: /Activo/ })).not.toBeChecked();
    await expect(page.getByLabel(/Mensaje de contacto/)).toHaveValue('WhatsApp 999 111 222');
    await expect(page.getByLabel(/Mensaje de contacto/)).toHaveAttribute('maxlength', '500');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/pagos-datos-${t.nombre}.png`, fullPage: true });
  });
}

test('datos: guardar envia los cuatro metodos y el contacto y vuelve con aviso', async ({ page }) => {
  await baseDatos(page);
  const metodos = await simular(page, 'PUT', '/instrucciones-pago', (r) => r.fulfill(json(200, r.request().postDataJSON())));
  const contacto = await simular(page, 'PUT', '/contacto-estudio', json(200, { texto: 'Escríbenos' }));
  await page.goto('/app/pagos/datos');
  await metodo(page, 'Plin').getByRole('textbox').fill('999 000 111');
  await metodo(page, 'Plin').getByRole('checkbox', { name: /Activo/ }).check();
  await page.getByLabel(/Mensaje de contacto/).fill('Escríbenos');
  await page.getByRole('button', { name: 'Guardar datos para pagar' }).click();
  await expect(page).toHaveURL(/\/app\/pagos\/\?aviso=datos-actualizados/);
  expect(metodos[0].cuerpo).toEqual([
    { metodo: 'transferencia', texto: 'BCP 191-0000000-0-00', activo: true },
    { metodo: 'yape', texto: '999 888 777 · Bugalú SAC', activo: true },
    { metodo: 'plin', texto: '999 000 111', activo: true },
    { metodo: 'tarjeta', texto: '', activo: false },
  ]);
  expect(contacto[0].cuerpo).toEqual({ texto: 'Escríbenos' });
  await expect(page.getByText('Datos para pagar guardados. Los clientes ya ven los nuevos.')).toBeVisible();
});

test('datos: un metodo activo sin texto marca su campo y no envia', async ({ page }) => {
  await baseDatos(page);
  const metodos = await simular(page, 'PUT', '/instrucciones-pago', json(200, INSTRUCCIONES));
  await page.goto('/app/pagos/datos');
  await metodo(page, 'Tarjeta').getByRole('checkbox', { name: /Activo/ }).check();
  await page.getByRole('button', { name: 'Guardar datos para pagar' }).click();
  await expect(metodo(page, 'Tarjeta').getByText('Escribe los datos para pagar con este método.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  expect(metodos).toHaveLength(0);
  await sinViolaciones(page);
});

test('datos: 422 del servidor da aviso con el mensaje y conserva los datos', async ({ page }) => {
  await baseDatos(page);
  await simular(page, 'PUT', '/instrucciones-pago', json(422, { error: { codigo: 'datos_invalidos', mensaje: 'El texto admite hasta 1000 caracteres.', detalles: { campo: 'texto' } } }));
  await page.goto('/app/pagos/datos');
  await metodo(page, 'Yape').getByRole('textbox').fill('nuevo yape');
  await page.getByRole('button', { name: 'Guardar datos para pagar' }).click();
  await expect(page.getByText('El texto admite hasta 1000 caracteres.')).toBeVisible();
  await expect(metodo(page, 'Yape').getByRole('textbox')).toHaveValue('nuevo yape');
  await expect(page.getByRole('button', { name: 'Guardar datos para pagar' })).toBeEnabled();
});

test('datos: ningun metodo activo avisa que los clientes no podran pagar', async ({ page }) => {
  await baseDatos(page, { instrucciones: INSTRUCCIONES.map((i) => ({ ...i, activo: false })) });
  await page.goto('/app/pagos/datos');
  await expect(page.getByText('Ningún método está activo: los clientes no podrán registrar pagos.')).toBeVisible();
});

test('datos: 403 al cargar', async ({ page }) => {
  await baseDatos(page);
  await simular(page, 'GET', '/instrucciones-pago', errorApi(403, 'sin_permiso'));
  await page.goto('/app/pagos/datos');
  await expect(page.getByRole('main')).toContainText('Esta sección es solo para el Administrador.');
});

// --- 4. Navegacion ---
const visibles = (page) => page.locator('.lateral-destino:visible .lateral-etiqueta, .tactil-destino:visible .tactil-etiqueta').allTextContents();

test('navegacion (escritorio): PAGOS tercero con contador y texto accesible', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto('/app/');
  expect(await visibles(page)).toEqual(['Inicio', 'Agenda', 'Pagos', 'Accesos', 'Usuarios', 'Franjas', 'Tarifas']);
  const enlace = page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: /Pagos/ });
  await expect(enlace).toHaveAttribute('href', '/app/pagos/');
  await expect(enlace).toHaveAccessibleName('Pagos 2 pagos por validar');
  await expect(enlace.locator('.etiqueta')).toHaveText('2');
  for (const e of await visibles(page)) expect(e.trim().length).toBeLessThanOrEqual(9);
  await sinViolaciones(page);
});

test('navegacion: 1 pago dice "1 pago por validar"; mas de 99 dice 99+; 0 o error no muestran contador', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page, { lista: [pago()] });
  await page.goto('/app/');
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: /Pagos/ })).toHaveAccessibleName('Pagos 1 pago por validar');
  await simular(page, 'GET', '/pagos', json(200, Array.from({ length: 120 }, () => pago())));
  await page.goto('/app/');
  await expect(page.getByRole('navigation', { name: 'Principal' }).locator('[data-contador]:visible .etiqueta')).toHaveText('99+');
  for (const resp of [json(200, []), errorApi(503, 'servicio_no_disponible')]) {
    await simular(page, 'GET', '/pagos', resp);
    await page.goto('/app/');
    await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Pagos', exact: true })).toBeVisible();
    await expect(page.locator('[data-contador]:visible')).toHaveCount(0);
  }
});

test('navegacion: PAGOS es el destino actual en las pantallas de pagos y el evento actualiza el contador', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto(REVISAR);
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: /Pagos/ })).toHaveAttribute('aria-current', 'page');
  await page.evaluate(() => document.dispatchEvent(new CustomEvent('bugalu:pagos-por-validar', { detail: 7 })));
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: /Pagos/ })).toHaveAccessibleName('Pagos 7 pagos por validar');
  await page.evaluate(() => document.dispatchEvent(new CustomEvent('bugalu:pagos-por-validar', { detail: 0 })));
  await expect(page.locator('[data-contador]:visible')).toHaveCount(0);
});

test('navegacion (movil): cinco destinos en la barra con PAGOS y contador; FRANJAS y TARIFAS en el menu', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await base(page);
  await page.goto('/app/');
  await expect(page.locator('.tactil-destino:visible')).toHaveCount(5);
  expect(await visibles(page)).toEqual(['Inicio', 'Agenda', 'Pagos', 'Accesos', 'Usuarios']);
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: /Pagos/ })).toHaveAccessibleName(/2 pagos por validar/);
  await page.screenshot({ path: 'pruebas/capturas/pagos-navegacion-390.png' });
  await page.getByText('Menú', { exact: true }).click();
  const menu = page.locator('.cabecera-menu-panel');
  await expect(menu.getByRole('link', { name: 'Franjas' })).toHaveAttribute('href', '/app/franjas/');
  await expect(menu.getByRole('link', { name: 'Tarifas' })).toHaveAttribute('href', '/app/tarifas/');
  await sinViolaciones(page);
});

test('navegacion: personal no ve PAGOS ni pide la lista', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(json(200, { id: 'u1', correo: 'a@b.com', correo_confirmado: true, nombre: 'Ana', telefono: null, nombre_artistico: null, rol: 'personal', especialidad: null })));
  const { vistas } = { vistas: await simular(page, 'GET', '/pagos', json(200, [])) };
  await page.goto('/app/');
  await expect(page.locator('.lateral-destino:visible')).toHaveCount(2);
  expect(vistas).toHaveLength(0);
});
