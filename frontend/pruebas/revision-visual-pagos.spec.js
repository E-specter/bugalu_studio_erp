// TAREA-RF05-7: correcciones de la revision visual de pagos (B1..B3, N1, N2, N10, N11, N12).
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones } from './ayudas-acceso.js';
import { simular, comoAdministrador } from './ayudas-admin.js';

const ID = '11111111-1111-4111-8111-111111111111';
const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const C2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const PAGO = '3f2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e6f';
const AHORA = new Date('2026-11-15T15:00:00Z');
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const PEDIDO = 'Ya registraste un pago, así que la cancelación la gestiona el estudio.';
const SIMULACION = { lineas: [{ concepto: 'Sala de grabación', cantidad: '2.50', unidad: 'hora', monto: '415.00' }], recargos: [], total: '415.00', anticipo: '207.50' };
const pago = (extra = {}) => ({ id: 'p1', estado: 'aprobado', metodo: 'yape', monto: '207.50', numero_operacion: 'OP1234', motivo_rechazo: null, registrado_en: '2026-11-15T12:00:00Z', ...extra });
const cuotas = (a = {}) => [
  { id: C1, hito: 'al_reservar', monto: '207.50', estado: 'pendiente', pagable: true, pagos: [], ...a },
  { id: C2, hito: 'al_terminar', monto: '207.50', estado: 'pendiente', pagable: false, pagos: [] },
];
const reserva = (extra = {}) => ({
  id: ID, folio: 'R-2026-00001', estado: 'pre_reservada', motivo_cancelacion: null, nota_cancelacion: null, pago_por_validar: false,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:30:00-05:00', sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [],
  precio: SIMULACION, vence_pago: new Date(AHORA.getTime() + 3 * 864e5).toISOString(), cuotas: cuotas(), ...extra,
});
const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
const preparar = async (page, rol, r) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, rol);
  await simular(page, 'GET', '/contacto-estudio', json(200, { texto: 'WhatsApp 999 000 111' }));
  await simular(page, 'GET', `/reservas/${ID}`, json(200, r));
};

test('B1: el parrafo "lo gestiona el estudio" no sale al cliente sin pagos', async ({ page }) => {
  await preparar(page, 'cliente', reserva());
  await page.goto(`/app/reservas/detalle?id=${ID}`);
  await expect(page.getByRole('button', { name: 'Cancelar reserva' })).toBeVisible();
  await expect(page.getByText(PEDIDO)).toBeHidden();
});

test('B1: tampoco al Administrador con pagos', async ({ page }) => {
  await preparar(page, 'administrador', reserva({ cliente: 'Ana Pérez', estado: 'confirmada', vence_pago: null, cuotas: cuotas({ estado: 'pagada', pagable: false, pagos: [pago()] }) }));
  await page.goto(`/app/reservas/detalle?id=${ID}`);
  await expect(page.getByRole('button', { name: 'Cancelar reserva', exact: true })).toBeVisible();
  await expect(page.getByText(PEDIDO)).toBeHidden();
});

test('B1: si lo ve el cliente con pagos', async ({ page }) => {
  await preparar(page, 'cliente', reserva({ pago_por_validar: true, cuotas: cuotas({ estado: 'en_validacion', pagable: false, pagos: [pago({ estado: 'pendiente_validacion' })] }) }));
  await page.goto(`/app/reservas/detalle?id=${ID}`);
  await expect(page.getByText(PEDIDO)).toBeVisible();
});

test('B2: a 390 las partidas no pintan rotulos ni parten los importes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await preparar(page, 'cliente', reserva());
  await page.goto(`/app/reservas/detalle?id=${ID}`);
  const r = await page.locator('.tabla-partidas td').evaluateAll((tds) => tds.map((td) => ({
    antes: getComputedStyle(td, '::before').content,
    lineas: td.classList.contains('tabla-num') && td.textContent.trim() ? new Set([...(() => { const g = document.createRange(); g.selectNodeContents(td); return [...g.getClientRects()].map((x) => Math.round(x.top)); })()]).size : 1,
  })));
  expect(r.length).toBeGreaterThan(0);
  for (const c of r) { expect(['none', 'normal']).toContain(c.antes); expect(c.lineas).toBe(1); }
});

test('B3: a 390 monto y operacion van en una columna', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await preparar(page, 'cliente', reserva());
  await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape', activo: true }]));
  await page.goto(`/app/reservas/pagar?id=${ID}&cuota=${C1}`);
  const a = await page.locator('#pago-monto').boundingBox();
  const b = await page.locator('#pago-operacion').boundingBox();
  expect(Math.abs(a.x - b.x)).toBeLessThan(2);
  expect(b.y).toBeGreaterThan(a.y + a.height);
  await page.screenshot({ path: 'pruebas/capturas/pago-formulario-corregido-390.png', fullPage: true });
});

test('N10: el nombre accesible del destino tactil empieza por la etiqueta', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await comoAdministrador(page);
  await simular(page, 'GET', '/pagos', json(200, [{ id: 'a' }, { id: 'b' }]));
  await page.goto('/app/');
  await expect(page.locator('.tactil-destino[href="/app/pagos/"]')).toHaveAccessibleName('Pagos 2 pagos por validar');
});

test('N11: durante el envio "Quitar" queda bloqueado', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await preparar(page, 'cliente', reserva());
  await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape', activo: true }]));
  await page.route(`${API}/pagos`, async (r) => { await espera; await r.fulfill(errorApi(503, 'x')); });
  await page.goto(`/app/reservas/pagar?id=${ID}&cuota=${C1}`);
  await page.getByRole('radio', { name: 'Yape' }).check();
  await page.getByLabel(/Monto pagado/).fill('207,5');
  await page.getByLabel(/Número de operación/).fill('op-12345');
  await page.getByLabel(/Captura del comprobante/).setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await page.getByRole('button', { name: 'Registrar pago' }).click();
  await expect(page.getByRole('button', { name: 'Quitar voucher.png' })).toBeDisabled();
  soltar();
});

test('N12: 413 con captura dentro del limite no dice que pesa mas de 5 MB', async ({ page }) => {
  await preparar(page, 'cliente', reserva());
  await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape', activo: true }]));
  await simular(page, 'POST', '/pagos', json(413, { error: { codigo: 'archivo_muy_grande', mensaje: 'x', detalles: null } }));
  await page.goto(`/app/reservas/pagar?id=${ID}&cuota=${C1}`);
  await page.getByRole('radio', { name: 'Yape' }).check();
  await page.getByLabel(/Monto pagado/).fill('207,5');
  await page.getByLabel(/Número de operación/).fill('op-12345');
  await page.getByLabel(/Captura del comprobante/).setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await page.getByRole('button', { name: 'Registrar pago' }).click();
  await expect(page.locator('#pago-captura-error')).toContainText('La captura es demasiado pesada para subirla. Sube una más ligera, de hasta 5 MB.');
});

test('N1: el 404 de revisar es el panel [404] PAGO NO ENCONTRADO', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/pagos', json(200, []));
  await simular(page, 'GET', `/pagos/${PAGO}`, json(404, { error: { codigo: 'no_encontrado', mensaje: 'x' } }));
  await page.goto(`/app/pagos/revisar?id=${PAGO}`);
  await expect(page.getByRole('main')).toContainText('[404]');
  await expect(page.getByRole('main')).toContainText(/pago no encontrado/i);
  await expect(page.getByRole('main')).toContainText('No encontramos este pago.');
  await expect(page.getByRole('link', { name: 'Volver a pagos' })).toHaveAttribute('href', '/app/pagos/');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pagos-revisar-404.png', fullPage: true });
});

test('N2: el PDF se abre como "Abrir comprobante.pdf"', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/pagos', json(200, []));
  await simular(page, 'GET', `/pagos/${PAGO}`, json(200, {
    id: PAGO, estado: 'pendiente_validacion', metodo: 'yape', monto: '225.00', numero_operacion: 'ABC123', motivo_rechazo: null, registrado_en: '2026-11-15T12:00:00Z', validado_en: null, monto_coincide: true,
    cuota: { id: 'c1', hito: 'al_reservar', monto: '225.00' }, reserva: { id: 'r1', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'pre_reservada' }, cliente: { id: 'u9', nombre: 'Ana Pérez' },
  }));
  await simular(page, 'GET', `/pagos/${PAGO}/captura`, json(200, { url: 'http://supabase.prueba/c.pdf', expira_en: '2026-11-15T15:10:00Z', tipo: 'pdf' }));
  await page.clock.setFixedTime(AHORA);
  await page.goto(`/app/pagos/revisar?id=${PAGO}`);
  await expect(page.getByRole('link', { name: /Abrir comprobante\.pdf/ })).toBeVisible();
});

