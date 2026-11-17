// RF-20 (CA-02, CA-03, CA-07, CA-09): desglose de IGV y porcentaje de adelanto en cada pantalla donde hay precio. La API se simula con page.route;
// los textos salen de lo que dicta el backend (el navegador nunca calcula base ni IGV). "Hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador } from './ayudas-admin.js';

const AHORA = new Date('2026-11-15T15:00:00Z');
const R1 = '11111111-1111-4111-8111-111111111111';
const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const C2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const INI = '2026-11-19T10:00:00-05:00';
const t = (dia, hora) => `2026-11-${dia}T${hora}:00-05:00`;

// Los dos modos del IGV, con un adelanto que no es 50 %: total 150,00 al 18 % -> base 127,12 e IGV 22,88; adelanto 30 % = 45,00.
const CASOS = [
  { nombre: 'IGV incluido', incluido: true, adelanto: 30, resumen: 'Incluye IGV (18 %)', ayuda: 'Precios con IGV incluido (18 %).' },
  { nombre: 'IGV sin incluir', incluido: false, adelanto: 30, resumen: 'Más IGV (18 %)', ayuda: 'Precios sin IGV: el IGV (18 %) se suma al total.' },
];
const impuesto = (incluido, porcentaje = '18.00') => ({ nombre: 'IGV', porcentaje, incluido, base: '127.12', monto: '22.88' });
const precio = (c) => ({
  lineas: [{ concepto: 'Grabación', cantidad: '2.0', unidad: 'hora', monto: '240.00' }],
  recargos: [], total: '150.00', anticipo: '45.00', porcentaje_adelanto: c.adelanto, impuesto: impuesto(c.incluido),
});
// Filas del pie de la tabla de partidas segun el modo (ver partidasPrecio).
const pieEsperado = (c) => (c.incluido
  ? [/^Total.*S\/ 150,00/, /^Incluye IGV \(18 %\).*S\/ 22,88/, /^Anticipo 30 %.*S\/ 45,00/]
  : [/^Subtotal.*S\/ 127,12/, /^IGV \(18 %\).*S\/ 22,88/, /^Total.*S\/ 150,00/, /^Anticipo 30 %.*S\/ 45,00/]);
async function pieDe(tabla, c) {
  const esperado = pieEsperado(c);
  const filas = tabla.locator('tfoot tr');
  await expect(filas).toHaveCount(esperado.length);
  for (const [i, re] of esperado.entries()) await expect(filas.nth(i)).toHaveText(re);
  // La fila del IGV es informativa: sin el peso de un total.
  const igv = tabla.locator('tfoot tr.tabla-igv');
  await expect(igv).toHaveCount(1);
  expect(Number(await igv.locator('th').evaluate((e) => getComputedStyle(e).fontWeight))).toBeLessThan(600);
}

// --- Reservar: paso 02 (ayuda, tabla y resumen) y 05 Listo ---
const SERV = [{ id: 's1', nombre: 'Grabación', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '0.00', especialistas_por_defecto: [], activo: true }];
const DISP = { limites: { desde: t('16', '10:00'), hasta: '2026-12-15T10:00:00-05:00' }, franjas: [{ id: 'f1', inicio: t('19', '10:00'), fin: t('19', '14:00') }], ocupados: [], cierres: [], dias: [] };
const RESERVA = (c) => ({
  id: R1, folio: 'R-2026-00013', estado: 'pre_reservada', motivo_cancelacion: null, inicio: INI, fin: t('19', '12:00'), fin_buffer: t('19', '12:30'),
  sala: 'La Molina', servicio: 'Grabación', especialistas: [], precio: precio(c), cuotas: [], vence_pago: '2026-11-17T10:00:00-05:00',
  parametros_aplicados: { porcentaje_igv: '18.00', precios_incluyen_igv: c.incluido, horas_limite_pago: 24, horas_nivel_1: 48, horas_nivel_2: 24, porcentaje_adelanto: c.adelanto },
});
async function montarReservar(page, c, { impuestos } = {}) {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil()));
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [{ id: 'sala-1', nombre: 'La Molina' }])));
  await page.route(`${API}/disponibilidad?**`, (r) => r.fulfill(json(200, DISP)));
  await page.route(`${API}/servicios`, (r) => r.fulfill(json(200, SERV)));
  await page.route(`${API}/especialistas`, (r) => r.fulfill(json(200, [])));
  await page.route(`${API}/simulaciones`, (r) => r.fulfill(json(200, precio(c))));
  await page.route(`${API}/impuestos`, (r) => r.fulfill(impuestos ?? json(200, { porcentaje_igv: '18.00', precios_incluyen_igv: c.incluido })));
  await page.route(`${API}/reservas/${R1}`, (r) => r.fulfill(json(200, RESERVA(c))));
}
const PASO2 = `/reservar/servicio/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`;

for (const c of CASOS) {
  for (const tm of tamanos) {
    test(`reservar 02: ${c.nombre}, adelanto ${c.adelanto} %, tabla, resumen y ayuda a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montarReservar(page, c);
      await page.goto(PASO2);
      const tabla = page.getByRole('region', { name: 'Precio simulado' }).getByRole('table', { name: 'Partidas' });
      await pieDe(tabla, c);
      const resumen = page.getByRole('region', { name: 'Tu reserva' });
      await expect(resumen).toContainText(c.resumen);
      await expect(resumen).toContainText('S/ 22,88');
      await expect(resumen).toContainText('Anticipo 30 %');
      await expect(page.getByRole('group', { name: 'Servicio' })).toContainText(c.ayuda);
      await expect(page.locator('bugalu-reserva [data-anuncio]')).toHaveText('Total S/ 150,00, anticipo S/ 45,00');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/desglose-reservar-02-${c.incluido ? 'incluido' : 'neto'}-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });

    test(`reservar 05 Listo: ${c.nombre}, adelanto ${c.adelanto} % a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montarReservar(page, c);
      await page.goto(`/reservar/listo/?id=${R1}`);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Reserva registrada');
      const datos = page.locator('[data-datos-listo]');
      await expect(datos).toContainText(c.resumen);
      await expect(datos).toContainText('S/ 22,88');
      await expect(datos).toContainText('Anticipo 30 %');
      await expect(datos).toContainText('S/ 45,00');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/desglose-reservar-05-${c.incluido ? 'incluido' : 'neto'}-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }
}

test('reservar 02: sin respuesta de /impuestos no hay ayuda de IGV y nada se rompe', async ({ page }) => {
  const consola = vigilarConsola(page);
  await montarReservar(page, CASOS[0], { impuestos: errorApi(503, 'servicio_no_disponible') });
  await page.goto(PASO2);
  await expect(page.getByRole('radio', { name: /Grabación/ })).toBeChecked();
  await expect(page.getByRole('group', { name: 'Servicio' })).not.toContainText('IGV');
  await expect(page.getByRole('region', { name: 'Precio simulado' })).toBeVisible();
  expect(consola).toEqual([]);
});

test('reservar 02: la ayuda usa el porcentaje vigente de /impuestos, con sus decimales', async ({ page }) => {
  await montarReservar(page, CASOS[0], { impuestos: json(200, { porcentaje_igv: '12.50', precios_incluyen_igv: true }) });
  await page.goto(PASO2);
  await expect(page.getByRole('group', { name: 'Servicio' })).toContainText('Precios con IGV incluido (12,5 %).');
});

// --- Mis reservas: detalle ---
const detalle = (c) => ({
  id: R1, folio: 'R-2026-00001', estado: 'pre_reservada', motivo_cancelacion: null, inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:00:00-05:00', fin_buffer: '2026-12-18T17:30:00-05:00',
  sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [], precio: precio(c),
  cuotas: [{ id: C1, hito: 'al_reservar', monto: '45.00', estado: 'pendiente' }, { id: C2, hito: 'al_terminar', monto: '105.00', estado: 'pendiente' }],
  vence_pago: new Date(AHORA.getTime() + 50 * 3600e3).toISOString(), parametros_aplicados: RESERVA(c).parametros_aplicados,
});
for (const c of CASOS) {
  for (const tm of tamanos) {
    test(`detalle de reserva: ${c.nombre}, adelanto ${c.adelanto} % a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await page.clock.setFixedTime(AHORA);
      await conSesion(page);
      await silenciarApi(page);
      await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
      await simular(page, 'GET', `/reservas/${R1}`, json(200, detalle(c)));
      await page.goto(`/app/reservas/detalle?id=${R1}`);
      await pieDe(page.getByRole('table', { name: 'Desglose del precio' }), c);
      await expect(page.getByRole('table', { name: 'Cuotas' }).getByRole('row', { name: /Al reservar/ })).toContainText('30 %');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/desglose-detalle-${c.incluido ? 'incluido' : 'neto'}-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }
}

// --- Registrar pago: lateral, bajo el importe de la cuota; el porcentaje es el de la reserva, no el vigente ---
for (const [nombre, imp, esperado] of [['IGV incluido', impuesto(true), 'Incluye IGV (18 %).'], ['IGV sin incluir al 10 %', impuesto(false, '10.00'), 'Incluye IGV (10 %).']]) {
  for (const tm of tamanos) {
    test(`registrar pago: ${nombre} a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await page.clock.setFixedTime(AHORA);
      await conSesion(page);
      await silenciarApi(page);
      await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
      const base = detalle(CASOS[0]);
      const r = { ...base, pago_por_validar: false, nota_cancelacion: null, precio: { ...base.precio, impuesto: imp }, cuotas: base.cuotas.map((c) => ({ ...c, pagable: c.id === C1, pagos: [] })) };
      await simular(page, 'GET', `/reservas/${R1}`, json(200, r));
      await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }]));
      await simular(page, 'GET', '/contacto-estudio', json(200, { texto: 'WhatsApp 999 000 111' }));
      await page.goto(`/app/reservas/pagar?id=${R1}&cuota=${C1}`);
      await expect(page.getByText(esperado)).toBeVisible();
      await expect(page.getByText('Al reservar · 30 %')).toBeVisible(); // el adelanto sale de las cuotas, no de un 50 fijo
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/desglose-pago-${imp.incluido ? 'incluido' : 'neto'}-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }
}

// --- Revisar pago (Administrador): IGV INCLUIDO con importe y base, informativo ---
const pago = (impuestoDelPago) => ({
  id: R1, estado: 'pendiente_validacion', metodo: 'yape', monto: '75.00', numero_operacion: 'ABC123', motivo_rechazo: null,
  registrado_en: '2026-11-15T12:00:00Z', validado_en: null, monto_coincide: true,
  cuota: { id: C1, hito: 'al_reservar', monto: '75.00' },
  reserva: { id: 'r1', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'pre_reservada' },
  cliente: { id: 'u9', nombre: 'Ana Pérez' },
  ...(impuestoDelPago && { impuesto: impuestoDelPago }),
});
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
async function montarRevision(page, p) {
  await page.clock.setFixedTime(AHORA);
  await comoAdministrador(page);
  await page.route('http://supabase.prueba/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }));
  await simular(page, 'GET', `/pagos/${R1}/captura`, json(200, { url: 'http://supabase.prueba/c.png', expira_en: '2026-11-15T15:10:00Z', tipo: 'imagen' }));
  await simular(page, 'GET', `/pagos/${R1}`, json(200, p));
}
for (const [nombre, imp, etiqueta, valor] of [
  ['18 %', { porcentaje: '18.00', base: '63.56', monto: '11.44' }, 'IGV incluido (18 %)', 'S/ 11,44 · base S/ 63,56'],
  ['10 % guardado en la reserva', { porcentaje: '10.00', base: '68.18', monto: '6.82' }, 'IGV incluido (10 %)', 'S/ 6,82 · base S/ 68,18'],
]) {
  for (const tm of tamanos) {
    test(`revisar pago: ${nombre} a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montarRevision(page, pago(imp));
      await page.goto(`/app/pagos/revisar?id=${R1}`);
      const seccion = page.getByRole('region', { name: /Pago$/ });
      await expect(seccion.getByText(etiqueta, { exact: true })).toBeVisible();
      await expect(seccion).toContainText(valor);
      await expect(seccion).toContainText('Informativo: el comprobante se emite fuera de la app.');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/desglose-revisar-${imp.porcentaje === '18.00' ? '18' : '10'}-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }
}

test('revisar pago: un pago anterior a RF-20, sin impuesto, no muestra la fila', async ({ page }) => {
  await montarRevision(page, pago(null));
  await page.goto(`/app/pagos/revisar?id=${R1}`);
  await expect(page.getByRole('region', { name: /Pago$/ })).toContainText('ABC123');
  await expect(page.getByText(/IGV incluido/)).toBeHidden();
});
