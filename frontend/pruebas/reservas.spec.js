// RF-04 (CA-05, CA-07, CA-08, CA-10): mis reservas y detalle de reserva. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';

const ID = '11111111-1111-4111-8111-111111111111';
const ID2 = '22222222-2222-4222-8222-222222222222';
const ID3 = '33333333-3333-4333-8333-333333333333';
const AHORA = new Date('2026-11-15T15:00:00Z'); // "hoy" fijo: el domingo 15 nov 2026, 10:00 en Lima
const dentroDe = (min) => new Date(AHORA.getTime() + min * 60e3).toISOString();
const SIMULACION = {
  lineas: [
    { concepto: 'Sala de grabación', cantidad: '2.50', unidad: 'hora', monto: '250.00' },
    { concepto: 'Ingeniero de sonido', cantidad: '5', unidad: 'lapso_30', monto: '60.00' },
    { concepto: 'Ingeniero de sonido (monto fijo)', cantidad: '1', unidad: 'fijo', monto: '80.00' },
  ],
  recargos: [{ tipo: 'noche', bloques: 2, monto: '25.00' }],
  total: '415.00',
  anticipo: '207.50',
};
const reserva = (extra = {}) => ({
  id: ID, folio: 'RES-0001', estado: 'pre_reservada', motivo_cancelacion: null,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:30:00-05:00', fin_buffer: '2026-12-18T18:00:00-05:00',
  sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [{ id: 'e1', nombre: 'Luis Mora' }, { id: 'e2', nombre: 'Eva Soto' }],
  precio: SIMULACION,
  cuotas: [{ id: 'c1', hito: 'al_reservar', monto: '207.50', estado: 'pendiente' }, { id: 'c2', hito: 'al_terminar', monto: '207.50', estado: 'pendiente' }],
  vence_pago: dentroDe(2 * 1440 + 3 * 60 + 30),
  ...extra,
});
const LISTA = [
  reserva({ id: ID3, folio: 'RES-0003', estado: 'confirmada', inicio: '2027-01-10T10:00:00-05:00', fin: '2027-01-10T12:00:00-05:00', servicio: 'Ensayo' }),
  reserva(),
  reserva({ id: ID2, folio: 'RES-0002', estado: 'finalizada', inicio: '2026-10-01T10:00:00-05:00', fin: '2026-10-01T11:00:00-05:00', servicio: 'Mezcla en vivo', vence_pago: null }),
  reserva({ id: 'c', folio: 'RES-0000', estado: 'cancelada', motivo_cancelacion: 'caducada', inicio: '2026-09-01T10:00:00-05:00', fin: '2026-09-01T10:30:00-05:00' }),
];

const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'cliente');
});

// Fallos de carga (estados-sistema), con el texto de la spec de mis reservas.
const fallos = (volverA, sinPermiso) => [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: 'Tu sesión no es válida. Inicia sesión para ver tus reservas.', enlace: ['Ir al acceso', `/acceso?volver=${encodeURIComponent(volverA)}`] },
  ...(sinPermiso ? [{ n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: sinPermiso, extra: '[403]', enlace: ['Volver a mis reservas', '/app/reservas/'] }] : []),
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];

// --- 1. Lista ---
for (const t of tamanos) {
  test(`lista: próximas con folio, fecha, duración, estado, total y plazo, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await simular(page, 'GET', '/reservas/mias', json(200, LISTA));
    await page.goto('/app/reservas/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/mis reservas/i);
    await expect(page.getByRole('status').filter({ hasText: '2 reservas próximas' })).toHaveCount(1);
    await expect(page.locator('.encabezado')).toContainText('[P2] SALA / RESERVAS');
    await expect(page.getByRole('link', { name: 'Reservar sala' })).toHaveAttribute('href', '/reservar/');
    const filas = page.getByRole('row');
    await expect(filas).toHaveCount(3); // cabecera + 2; ascendente por inicio
    await expect(filas.nth(1)).toContainText('RES-0001');
    await expect(filas.nth(1)).toContainText('Grabación de voces');
    await expect(filas.nth(1)).toContainText('18 dic 2026');
    await expect(filas.nth(1)).toContainText('15:00–17:30');
    await expect(filas.nth(1)).toContainText('2 h 30 min');
    await expect(filas.nth(1)).toContainText('Pre-reservada');
    await expect(filas.nth(1)).toContainText('S/ 415,00');
    await expect(filas.nth(1)).toContainText(/Antes del \d{1,2} \w{3}, \d{2}:\d{2}/);
    await expect(filas.nth(1)).toContainText('faltan 2 d 3 h');
    await expect(filas.nth(1)).toContainText('Sin pago registrado, caduca y el horario se libera.');
    await expect(filas.nth(2)).toContainText('RES-0003');
    await expect(filas.nth(2)).toContainText('Confirmada');
    await expect(filas.nth(2)).not.toContainText('caduca');
    await expect(page.getByRole('link', { name: 'Ver reserva RES-0001' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    await expect(page.getByRole('link', { name: 'Próximas' })).toHaveAttribute('aria-current', 'true');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reservas-lista-${t.nombre}.png`, fullPage: true });
  });

  test(`lista: historial con motivo de cancelación, a ${t.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await simular(page, 'GET', '/reservas/mias', json(200, LISTA));
    await page.goto('/app/reservas/?ver=historial');
    await expect(page.getByRole('link', { name: 'Historial' })).toHaveAttribute('aria-current', 'true');
    await expect(page.getByRole('status').filter({ hasText: '2 reservas en el historial' })).toHaveCount(1);
    const filas = page.getByRole('row');
    await expect(filas.nth(1)).toContainText('RES-0002'); // descendente por inicio
    await expect(filas.nth(1)).toContainText('Finalizada');
    await expect(filas.nth(2)).toContainText('RES-0000');
    await expect(filas.nth(2)).toContainText('Cancelada');
    await expect(filas.nth(2)).toContainText('Caducó sin pago');
    await expect(filas.nth(2)).not.toContainText('faltan');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/reservas-historial-${t.nombre}.png`, fullPage: true });
  });
}

test('lista: motivos de cancelación en texto', async ({ page }) => {
  const c = (folio, motivo) => reserva({ id: `${folio}`, folio, estado: 'cancelada', motivo_cancelacion: motivo });
  await simular(page, 'GET', '/reservas/mias', json(200, [c('A-1', 'cliente'), c('A-2', 'administrador'), c('A-3', 'caducada')]));
  await page.goto('/app/reservas/?ver=historial');
  await expect(page.getByRole('row').nth(1)).toContainText('La cancelaste');
  await expect(page.getByRole('row').nth(2)).toContainText('La canceló el estudio');
  await expect(page.getByRole('row').nth(3)).toContainText('Caducó sin pago');
});

test('lista: sin reservas invita a reservar y quita la acción del encabezado', async ({ page }) => {
  await simular(page, 'GET', '/reservas/mias', json(200, []));
  await page.goto('/app/reservas/');
  await expect(page.locator('[data-salida]').getByText('Aún no tienes reservas')).toBeVisible();
  await expect(page.locator('[data-salida]').getByText('Elige un horario libre y reserva la sala en unos pasos.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Reservar sala' })).toHaveCount(1);
  await expect(page.getByRole('link', { name: 'Reservar sala' })).toHaveAttribute('href', '/reservar/');
  await expect(page.getByRole('navigation', { name: 'Filtrar reservas' })).toHaveCount(0);
  await expect(page.getByRole('table')).toHaveCount(0);
  for (const t of tamanos) {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/reservas-vacio-${t.nombre}.png`, fullPage: true });
  }
});

test('lista: un filtro sin resultados ofrece el otro', async ({ page }) => {
  await simular(page, 'GET', '/reservas/mias', json(200, [LISTA[2]]));
  await page.goto('/app/reservas/');
  await expect(page.locator('[data-salida]').getByText('No tienes reservas próximas.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver historial' })).toHaveAttribute('href', '/app/reservas/?ver=historial');
  await sinViolaciones(page);
  await page.goto('/app/reservas/?ver=historial');
  await expect(page.getByRole('row')).toHaveCount(2);
  await simular(page, 'GET', '/reservas/mias', json(200, [LISTA[1]]));
  await page.goto('/app/reservas/?ver=historial');
  await expect(page.locator('[data-salida]').getByText('Aún no hay reservas en tu historial.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver próximas' })).toHaveAttribute('href', '/app/reservas/');
});

test('lista: el plazo se recalcula cada minuto y solo se anuncia al cruzar un umbral', async ({ page }) => {
  await page.clock.install({ time: AHORA });
  await simular(page, 'GET', '/reservas/mias', json(200, [reserva({ vence_pago: dentroDe(61.5) })]));
  await page.goto('/app/reservas/');
  const plazo = page.locator('[data-plazo]');
  const anuncio = page.locator('[data-anuncio]');
  await expect(plazo).toHaveText('faltan 1 h 1 min');
  await expect(anuncio).toHaveText('1 reserva próxima');
  await page.clock.runFor(60_000);
  await expect(plazo).toHaveText('faltan 1 h');
  await expect(anuncio).toHaveText('1 reserva próxima'); // sin anuncio por cada minuto
  await page.clock.runFor(60_000);
  await expect(plazo).toHaveText('faltan 59 min');
  await expect(anuncio).toHaveText('La reserva RES-0001 vence en menos de 1 h.');
  await page.clock.runFor(45 * 60_000);
  await expect(anuncio).toHaveText('La reserva RES-0001 vence en menos de 15 min.');
  await page.clock.runFor(15 * 60_000);
  await expect(anuncio).toHaveText('La reserva RES-0001 venció sin pago.');
  await expect(page.getByRole('row').nth(1)).toContainText('Caducada');
  await expect(page.getByRole('row').nth(1)).toContainText('Venció sin pago');
});

for (const f of fallos('/app/reservas/')) {
  test(`lista: ${f.n} muestra su estado`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await simular(page, 'GET', '/reservas/mias', f.r);
    await page.goto('/app/reservas/');
    const aviso = page.locator('[data-salida] .aviso');
    await expect(aviso).toContainText(f.texto);
    if (f.enlace) await expect(aviso.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1]);
    if (f.reintentar) await expect(aviso.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    for (const t of tamanos) {
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await sinViolaciones(page);
    }
    expect(consola).toEqual([]);
  });
}

test('lista: Reintentar vuelve a cargar y el foco va al panel', async ({ page }) => {
  let n = 0;
  await simular(page, 'GET', '/reservas/mias', (r) => (n++ ? r.fulfill(json(200, LISTA)) : r.fulfill(errorApi(503, 'x'))));
  await page.goto('/app/reservas/');
  await page.getByRole('button', { name: 'Reintentar' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('row')).toHaveCount(3);
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/app/reservas/', `/app/reservas/detalle?id=${ID}`]) {
    test(`${ruta} avisa y no queda cargando`, async ({ page }) => {
      await page.goto(ruta);
      expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-reservas [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await expect(page.getByText('Cargando…')).toBeHidden(); // axe necesita JS: aqui no corre
      await page.screenshot({ path: `pruebas/capturas/reservas-${ruta.includes('detalle') ? 'detalle' : 'lista'}-sin-js.png`, fullPage: true });
    });
  }
});

// --- 2. Detalle ---
const ver = (page, id = ID) => page.goto(`/app/reservas/detalle?id=${id}`);

for (const t of tamanos) {
  test(`detalle: pre-reservada con desglose, cuotas y plazo, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva()));
    await ver(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/reserva RES-0001/i);
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Grabación de voces · 18 dic 2026, 15:00–17:30');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reservas', 'RES-0001']);
    const datos = page.locator('dl');
    await expect(datos).toContainText('Pre-reservada');
    await expect(datos).toContainText('2 h 30 min');
    await expect(datos).toContainText('Sala principal');
    await expect(datos).toContainText('Luis Mora, Eva Soto');
    await expect(datos).not.toContainText('Cliente');
    const precio = page.getByRole('table', { name: 'Desglose del precio' });
    await expect(precio.getByRole('row')).toHaveCount(1 + 3 + 1 + 2); // cabecera, líneas, recargo, total y anticipo
    await expect(precio).toContainText('Sala de grabación');
    await expect(precio).toContainText('2,5 h');
    await expect(precio).toContainText('5 × 30 min');
    await expect(precio).toContainText('Recargo de noche');
    await expect(precio).toContainText('2 × 30 min');
    await expect(precio.getByRole('row', { name: /Total/ })).toContainText('S/ 415,00');
    await expect(precio.getByRole('row', { name: /Anticipo/ })).toContainText('S/ 207,50');
    await expect(page.getByText('Precio calculado al reservar.')).toBeVisible();
    const cuotas = page.getByRole('table', { name: 'Cuotas' });
    await expect(cuotas.getByRole('row', { name: /Al reservar/ })).toContainText('50 %');
    await expect(cuotas.getByRole('row', { name: /Al reservar/ })).toContainText('Pendiente');
    await expect(cuotas.getByRole('row', { name: /Al terminar la sesión/ })).toContainText('S/ 207,50');
    await expect(page.getByText(/Paga el anticipo antes del \d{1,2} \w{3}, \d{2}:\d{2}/i)).toBeVisible();
    await expect(page.getByText('faltan 2 d 3 h')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancelar reserva', exact: true })).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reservas-detalle-${t.nombre}.png`, fullPage: true });
  });
}

test('detalle: con menos de 1 h avisa de la caducidad', async ({ page }) => {
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ vence_pago: dentroDe(45.5) })));
  await ver(page);
  await expect(page.getByText('Tu reserva vence en 45 min. Si no registras el pago, se cancelará y el horario se liberará.')).toBeVisible();
  await expect(page.locator('.aviso[role]')).toHaveCount(0); // no se anuncia solo
  await sinViolaciones(page);
});

test('detalle: pre-reservada con plazo vencido se ve caducada y sin cancelar', async ({ page }) => {
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ vence_pago: dentroDe(-30) })));
  await ver(page);
  await expect(page.getByText('Caducada', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Venció sin pago el \d{1,2} \w{3}, \d{2}:\d{2}\. El horario quedó libre\./)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancelar reserva' })).toHaveCount(0);
  await sinViolaciones(page);
});

const porEstado = [
  ['confirmada', { estado: 'confirmada' }, ['Confirmada', 'Pagas el resto al terminar la sesión.']],
  ['en_curso', { estado: 'en_curso' }, ['En curso']],
  ['finalizada', { estado: 'finalizada', cuotas: [{ id: 'c1', hito: 'al_reservar', monto: '207.50', estado: 'pagada' }, { id: 'c2', hito: 'al_terminar', monto: '207.50', estado: 'pendiente' }] }, ['Finalizada', 'Falta pagar el resto: S/ 207,50.']],
  ['cancelada por ti', { estado: 'cancelada', motivo_cancelacion: 'cliente' }, ['Cancelada', 'La cancelaste.']],
  ['cancelada caducada', { estado: 'cancelada', motivo_cancelacion: 'caducada' }, ['Cancelada', /Caducó sin pago el \d{1,2} \w{3}, \d{2}:\d{2}\. El horario se liberó\./]],
  ['cancelada por el estudio', { estado: 'cancelada', motivo_cancelacion: 'administrador' }, ['Cancelada', 'La canceló el estudio.']],
];
for (const [nombre, extra, textos] of porEstado) {
  test(`detalle: ${nombre}`, async ({ page }) => {
    await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva(extra)));
    await ver(page);
    for (const texto of textos) await expect(page.locator('[data-estado-reserva]')).toContainText(texto);
    await expect(page.getByRole('button', { name: 'Cancelar reserva' })).toHaveCount(0); // el cliente solo cancela pre-reservadas
    await sinViolaciones(page);
  });
}

test('detalle: el estado en cuotas pagadas lleva texto', async ({ page }) => {
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ estado: 'confirmada', cuotas: [{ id: 'c1', hito: 'al_reservar', monto: '207.50', estado: 'pagada' }, { id: 'c2', hito: 'al_terminar', monto: '207.50', estado: 'pendiente' }] })));
  await ver(page);
  await expect(page.getByRole('row', { name: /Al reservar/ })).toContainText('Pagada');
});

test('detalle: el personal ve al cliente y no puede cancelar', async ({ page }) => {
  await comoRol(page, 'personal');
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ cliente: 'Ana Pérez' })));
  await ver(page);
  await expect(page.locator('dl')).toContainText('Ana Pérez');
  await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Agenda', 'RES-0001']);
  await expect(page.getByRole('button', { name: 'Cancelar reserva' })).toHaveCount(0);
  await sinViolaciones(page);
});

test('detalle: el Administrador cancela también las confirmadas', async ({ page }) => {
  await comoRol(page, 'administrador');
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ cliente: 'Ana Pérez', estado: 'confirmada' })));
  await ver(page);
  await expect(page.getByRole('button', { name: 'Cancelar reserva' })).toBeVisible();
});

// --- 3. Cancelar ---
test('cancelar: confirmación accesible, foco, y el estado se actualiza al confirmar', async ({ page }) => {
  const consola = vigilarConsola(page);
  const cancelar = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, reserva({ estado: 'cancelada', motivo_cancelacion: 'cliente' })));
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva()));
  page.on('dialog', (d) => { throw new Error(`diálogo nativo: ${d.message()}`); });
  await ver(page);
  const abrir = page.getByRole('button', { name: 'Cancelar reserva', exact: true });
  await abrir.focus();
  await page.keyboard.press('Enter');
  const confirmacion = page.getByRole('region', { name: /Cancelar reserva RES-0001/ });
  await expect(confirmacion).toBeVisible();
  await expect(page.getByRole('heading', { name: /Cancelar reserva RES-0001/ })).toBeFocused();
  await expect(confirmacion).toContainText('El horario se libera al momento y no se te cobra nada.');
  await expect(confirmacion).toContainText('18 dic 2026');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-cancelar-confirmar.png', fullPage: true });
  // Escape vuelve sin cancelar y devuelve el foco al botón.
  await page.keyboard.press('Escape');
  await expect(confirmacion).toBeHidden();
  await expect(abrir).toBeFocused();
  expect(cancelar).toHaveLength(0);
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Cancelar reserva RES-0001' }).click();
  expect(cancelar).toHaveLength(1);
  const aviso = page.locator('[data-avisos] .aviso');
  await expect(aviso).toContainText('Reserva cancelada. El horario quedó libre y no se te cobró nada.');
  await expect(aviso).toBeFocused();
  await expect(page.locator('[data-estado-reserva]')).toContainText('La cancelaste.');
  await expect(page.locator('dl')).toContainText('Cancelada');
  await expect(page.getByRole('button', { name: /Cancelar reserva/ })).toHaveCount(0);
  await expect(confirmacion).toBeHidden();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/reservas-cancelar-exito.png', fullPage: true });
});

test('cancelar: enviando bloquea los botones', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva()));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, async (r) => { await espera; await r.fulfill(json(200, reserva({ estado: 'cancelada', motivo_cancelacion: 'cliente' }))); });
  await ver(page);
  await page.getByRole('button', { name: 'Cancelar reserva', exact: true }).click();
  await page.getByRole('button', { name: 'Cancelar reserva RES-0001' }).click();
  await expect(page.getByRole('button', { name: 'Cancelando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeDisabled();
  soltar();
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Reserva cancelada');
});

const conflictos = [
  ['tiene_pagos', 'Ya registraste un pago para esta reserva, así que no puedes cancelarla desde aquí. Escríbenos para revisar tu caso.'],
  ['no_cancelable', 'Esta reserva ya no se puede cancelar: está confirmada.'],
];
for (const [codigo, texto] of conflictos) {
  test(`cancelar: 409 ${codigo} se explica y el foco va al aviso`, async ({ page }) => {
    let lecturas = 0;
    await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, reserva(codigo === 'no_cancelable' && lecturas++ ? { estado: 'confirmada' } : {}))));
    await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(409, codigo)));
    await ver(page);
    await page.getByRole('button', { name: 'Cancelar reserva', exact: true }).click();
    await page.getByRole('button', { name: 'Cancelar reserva RES-0001' }).click();
    const aviso = page.locator('[data-avisos] .aviso');
    await expect(aviso).toContainText(texto);
    await expect(aviso).toBeFocused();
    await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Cancelar reserva RES-0001' })).toHaveCount(0);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/reservas-cancelar-${codigo}.png`, fullPage: true });
  });
}

test('cancelar: un 503 deja el botón disponible y avisa sin Reintentar', async ({ page }) => {
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva()));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(503, 'x')));
  await ver(page);
  await page.getByRole('button', { name: 'Cancelar reserva', exact: true }).click();
  await page.getByRole('button', { name: 'Cancelar reserva RES-0001' }).click();
  await expect(page.locator('[data-avisos] .aviso')).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Cancelar reserva RES-0001' })).toBeEnabled();
});

// --- 4. Estados de carga del detalle ---
test('detalle: un id que no es UUID es "no encontrada" sin llamar a la API', async ({ page }) => {
  const vistas = await simular(page, 'GET', '/reservas/abc', json(200, reserva()));
  await page.goto('/app/reservas/detalle?id=abc');
  await expect(page.locator('[data-salida]').getByText('No encontramos esta reserva.')).toBeVisible();
  await expect(page.getByRole('heading', { name: /\[404\] Reserva no encontrada/i })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a mis reservas' })).toHaveAttribute('href', '/app/reservas/');
  expect(vistas).toHaveLength(0);
  for (const t of tamanos) {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await sinViolaciones(page);
  }
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-no-encontrada.png', fullPage: true });
});

test('detalle: sin id tampoco consulta', async ({ page }) => {
  await page.goto('/app/reservas/detalle');
  await expect(page.locator('[data-salida]').getByText('No encontramos esta reserva.')).toBeVisible();
});

test('detalle: 404 y 403 sustituyen el bloque', async ({ page }) => {
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(errorApi(404, 'reserva_no_encontrada')));
  await simular(page, 'GET', `/reservas/${ID2}`, (r) => r.fulfill(errorApi(403, 'sin_permiso')));
  await ver(page);
  await expect(page.locator('[data-salida]').getByText('No encontramos esta reserva.')).toBeVisible();
  await sinViolaciones(page);
  await ver(page, ID2);
  await expect(page.getByRole('heading', { name: /\[403\]/ })).toBeVisible();
  await expect(page.locator('[data-salida]').getByText('Esta reserva no es tuya.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a mis reservas' })).toHaveAttribute('href', '/app/reservas/');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-sin-permiso.png', fullPage: true });
});

for (const f of fallos(`/app/reservas/detalle?id=${ID}`).filter((x) => x.n !== '403')) {
  test(`detalle: ${f.n} muestra su estado`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await simular(page, 'GET', `/reservas/${ID}`, f.r);
    await ver(page);
    const aviso = page.locator('[data-salida] .aviso');
    await expect(aviso).toContainText(f.texto);
    if (f.enlace) await expect(aviso.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1]);
    if (f.reintentar) await expect(aviso.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    for (const t of tamanos) {
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await sinViolaciones(page);
    }
    expect(consola).toEqual([]);
  });
}

test('detalle: la carga se ve con aria-busy y no deja violaciones', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await simular(page, 'GET', `/reservas/${ID}`, async (r) => { await espera; await r.fulfill(json(200, reserva())); });
  await ver(page);
  await expect(page.getByText('Cargando…')).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-carga.png', fullPage: true });
  soltar();
  await expect(page.locator('dl')).toContainText('Luis Mora');
});
