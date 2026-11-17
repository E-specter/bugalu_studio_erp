// RF-18 (CA-07 lado Administrador, CA-13 plazo, CA-16): cola de devoluciones, decidir y marcar realizada.
import { test, expect } from '@playwright/test';
import { json, errorApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos } from './ayudas-admin.js';
import { ID, DV1, DV2, AHORA, devolucion } from './ayudas-rf18.js';

const aviso = (page) => page.locator('[data-avisos] .aviso');
const lista = (page, estado = '') => page.goto(`/app/pagos/devoluciones${estado ? `?estado=${estado}` : ''}`);
const revisar = (page, id = DV1) => page.goto(`/app/pagos/devoluciones/revisar?id=${id}`);
const colas = (page, porEstado) => simular(page, 'GET', '/devoluciones', (r) => r.fulfill(json(200, porEstado[new URL(r.request().url()).searchParams.get('estado')] ?? [])));

const PENDIENTES = [
  devolucion({ id: DV1, solicitada_en: '2026-11-14T15:00:00Z' }),
  devolucion({ id: DV2, folio: 'R-2026-00002', id_reserva: 'r2', cliente: { id: 'u4', nombre: null }, solicitada_en: '2026-11-12T10:00:00Z', monto_solicitado: '60.00' }),
  devolucion({ id: 'd3', folio: 'R-2026-00003', id_reserva: 'r3', cliente: { id: 'u5', nombre: 'Luis Mora' }, solicitada_en: '2026-11-15T14:00:00Z', monto_solicitado: '25.50' }),
];
const APROBADAS = [
  devolucion({ id: 'a1', folio: 'R-2026-00004', id_reserva: 'r4', tipo: 'estudio', id_credito: null, estado: 'aprobada', monto_solicitado: '300.00', monto_aprobado: '300.00', limite: '2026-11-25T23:59:59-05:00', motivo: 'Cancelación del estudio' }),
  devolucion({ id: 'a2', folio: 'R-2026-00005', id_reserva: 'r5', tipo: 'estudio', id_credito: null, estado: 'aprobada', monto_solicitado: '120.00', monto_aprobado: '120.00', limite: '2026-11-10T23:59:59-05:00', motivo: 'Cancelación del estudio' }),
  devolucion({ id: 'a3', folio: 'R-2026-00006', id_reserva: 'r6', estado: 'aprobada', monto_solicitado: '100.00', monto_aprobado: '60.00', decidida_en: '2026-11-14T15:00:00Z' }),
];

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await comoAdministrador(page);
});

// --- Lista ---
for (const t of tamanos) {
  test(`devoluciones: pendientes, la más antigua arriba, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await colas(page, { pendiente: PENDIENTES });
    await lista(page);
    expect(vistas[0].url.searchParams.get('estado')).toBe('pendiente');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^devoluciones$/i);
    await expect(page.locator('.encabezado')).toContainText('[A11] COBROS / DEVOLUCIONES');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Pagos', 'Devoluciones']);
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Devoluciones que pidieron los clientes y las de cancelaciones del estudio. Decide cada una y márcala cuando hayas devuelto el dinero.');
    await expect(page.getByRole('link', { name: 'Volver a pagos' })).toHaveAttribute('href', '/app/pagos/');
    await expect(page.getByRole('link', { name: 'Pendientes' })).toHaveAttribute('aria-current', 'true');
    await expect(page.locator('[data-total]')).toHaveText('3 devoluciones pendientes');
    const filas = page.getByRole('row');
    await expect(filas).toHaveCount(4);
    await expect(filas.nth(1)).toContainText('R-2026-00002');
    await expect(filas.nth(1)).toContainText('Sin nombre');
    await expect(filas.nth(1)).toContainText('S/ 60,00');
    await expect(filas.nth(2)).toContainText('R-2026-00001');
    await expect(filas.nth(2)).toContainText('Crédito de cancelación');
    await expect(filas.nth(2)).toContainText('Eva Soto');
    await expect(filas.nth(3)).toContainText('R-2026-00003');
    await expect(page.getByRole('link', { name: 'Revisar devolución de R-2026-00001' })).toHaveAttribute('href', `/app/pagos/devoluciones/revisar?id=${DV1}`);
    await expect(page.locator('[data-anuncio]')).toHaveText('3 devoluciones pendientes');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-devoluciones-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('devoluciones: aprobadas con plazo en texto, FUERA DE PLAZO y monto parcial', async ({ page }) => {
  await colas(page, { aprobada: APROBADAS });
  await lista(page, 'aprobada');
  await expect(page.getByRole('link', { name: 'Aprobadas' })).toHaveAttribute('aria-current', 'true');
  await expect(page.getByRole('columnheader', { name: 'Plazo' })).toBeVisible();
  const f = (folio) => page.getByRole('row', { name: new RegExp(folio) });
  await expect(f('R-2026-00004')).toContainText('Cancelación del estudio');
  await expect(f('R-2026-00004')).toContainText(/25 nov · faltan 10 d/);
  await expect(f('R-2026-00005')).toContainText('Fuera de plazo');
  await expect(f('R-2026-00005')).toContainText('Venció el 10 nov');
  await expect(f('R-2026-00006')).toContainText('S/ 60,00 de S/ 100,00');
  // Las del estudio, por limite: la vencida primero.
  await expect(page.getByRole('row').nth(1)).toContainText('R-2026-00005');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-devoluciones-aprobadas-1440.png', fullPage: true });
});

test('devoluciones: realizadas y rechazadas, la más reciente arriba, con su fecha', async ({ page }) => {
  await colas(page, {
    realizada: [devolucion({ id: 'x1', folio: 'R-2026-00007', estado: 'realizada', realizada_en: '2026-11-10T15:00:00Z', monto_aprobado: '100.00' }), devolucion({ id: 'x2', folio: 'R-2026-00008', estado: 'realizada', realizada_en: '2026-11-13T15:00:00Z', monto_aprobado: '100.00' })],
    rechazada: [devolucion({ id: 'x3', folio: 'R-2026-00009', estado: 'rechazada', decidida_en: '2026-11-11T15:00:00Z', motivo_decision: 'Sin sustento' })],
  });
  await lista(page, 'realizada');
  await expect(page.getByRole('row').nth(1)).toContainText('R-2026-00008');
  await expect(page.getByRole('row').nth(1)).toContainText('13 nov');
  await lista(page, 'rechazada');
  await expect(page.getByRole('row').nth(1)).toContainText('11 nov');
  await sinViolaciones(page);
});

test('devoluciones: vacío de pendientes sin acción y vacío de otros filtros con "Ver pendientes"', async ({ page }) => {
  await colas(page, {});
  await lista(page);
  await expect(page.locator('[data-salida]').getByText('No hay devoluciones por decidir')).toBeVisible();
  await expect(page.getByText('Cuando un cliente pida la devolución de un crédito, aparecerá aquí.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver pendientes' })).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-devoluciones-vacio-1440.png', fullPage: true });
  for (const [estado, texto] of [['aprobada', 'Aún no hay devoluciones aprobadas.'], ['realizada', 'Aún no hay devoluciones realizadas.'], ['rechazada', 'Aún no hay devoluciones rechazadas.']]) {
    await lista(page, estado);
    await expect(page.getByText(texto)).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver pendientes' })).toHaveAttribute('href', '/app/pagos/devoluciones');
  }
  await lista(page, 'otra');
  await expect(page.getByRole('link', { name: 'Pendientes' })).toHaveAttribute('aria-current', 'true');
});

for (const f of fallos) {
  test(`devoluciones: lista con ${f.n}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = true;
    await simular(page, 'GET', '/devoluciones', (r) => (falla ? f.r(r) : r.fulfill(json(200, PENDIENTES))));
    await lista(page);
    await expect(page.locator('[data-salida]')).toContainText(f.texto);
    if (f.enlace) await expect(page.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1]('/app/pagos/devoluciones'));
    await sinViolaciones(page);
    if (f.reintentar) {
      falla = false;
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByRole('row')).toHaveCount(4);
    }
    if (f.n !== 'no-json') expect(consola).toEqual([]);
  });
}

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('devoluciones: avisa en vez de quedarse cargando', async ({ page }) => {
    await page.goto('/app/pagos/devoluciones');
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
    await page.goto(`/app/pagos/devoluciones/revisar?id=${DV1}`);
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
  });
});

// --- Pagos: acción y aviso ---
test('pagos: suma la acción "Devoluciones" y el aviso de trabajo pendiente', async ({ page }) => {
  await simular(page, 'GET', '/pagos', json(200, []));
  await colas(page, { pendiente: PENDIENTES.slice(0, 2), aprobada: APROBADAS.slice(0, 1) });
  await page.goto('/app/pagos/');
  await expect(page.getByRole('link', { name: 'Devoluciones', exact: true })).toHaveAttribute('href', '/app/pagos/devoluciones');
  await expect(page.getByText('Tienes 2 devoluciones por decidir y 1 por hacer.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver devoluciones' })).toHaveAttribute('href', '/app/pagos/devoluciones');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-pagos-aviso-devoluciones-1440.png', fullPage: true });
  await colas(page, { pendiente: PENDIENTES.slice(0, 1) });
  await page.goto('/app/pagos/');
  await expect(page.getByText('Tienes 1 devolución por decidir.')).toBeVisible();
  await colas(page, { aprobada: APROBADAS });
  await page.goto('/app/pagos/');
  await expect(page.getByText('Tienes 3 devoluciones por hacer.')).toBeVisible();
  await colas(page, {});
  await page.goto('/app/pagos/');
  await expect(page.getByRole('link', { name: 'Ver devoluciones' })).toHaveCount(0);
  await simular(page, 'GET', '/devoluciones', (r) => r.fulfill(errorApi(503, 'x')));
  await page.goto('/app/pagos/');
  await expect(page.getByRole('link', { name: 'Ver devoluciones' })).toHaveCount(0);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/pagos/i);
});

test('pagos: el aviso de devoluciones no pisa el de ?aviso=', async ({ page }) => {
  await simular(page, 'GET', '/pagos', json(200, []));
  await colas(page, { pendiente: PENDIENTES });
  await page.goto('/app/pagos/?aviso=pago-aprobado');
  await expect(page.locator('[data-avisos]')).toContainText('Pago aprobado');
  await expect(page.getByText('Tienes 3 devoluciones por decidir.')).toBeVisible();
});

// --- Revisar: decidir ---
const decidir = (page) => page.getByRole('region', { name: /V2 Decisión/i });
const opcion = (page, nombre) => decidir(page).getByRole('radio', { name: nombre });
const enviar = (page, nombre) => decidir(page).getByRole('button', { name: nombre });

for (const t of tamanos) {
  test(`revisar: devolución pendiente con la solicitud y las tres decisiones, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
    await revisar(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/revisar devolución/i);
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Pagos', 'Devoluciones', 'R-2026-00001']);
    await expect(page.locator('.encabezado-descripcion')).toContainText('Eva Soto · Crédito de cancelación de la reserva R-2026-00001');
    const v1 = page.getByRole('region', { name: /V1 Solicitud/i });
    await expect(v1).toContainText('Eva Soto');
    await expect(v1).toContainText('S/ 100,00');
    await expect(v1).toContainText('Prefiero el dinero porque no voy a reservar de nuevo.');
    await expect(v1.getByRole('link', { name: 'R-2026-00001' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    const grupo = decidir(page).getByRole('group', { name: 'Decisión' });
    await expect(grupo.getByRole('radio')).toHaveCount(3);
    await expect(grupo).toContainText('Devolver todo (S/ 100,00)');
    await expect(grupo).toContainText('Devolver una parte');
    await expect(grupo).toContainText('Rechazar');
    await expect(page.getByLabel(/Monto a devolver/)).toBeHidden();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-devolucion-revisar-${t.nombre}.png`, fullPage: true });
  });
}

test('revisar: devolver todo, el texto del botón sigue a la opción y vuelve a la lista con el aviso', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  const envios = await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, json(200, devolucion({ estado: 'aprobada', monto_aprobado: '100.00' })));
  await colas(page, {});
  await revisar(page);
  await expect(decidir(page).getByRole('button', { name: /Aprobar|Rechazar devolución|Registrar/ }).first()).toBeVisible();
  await opcion(page, /Devolver todo/).check();
  await expect(decidir(page)).toContainText('El crédito queda en S/ 0,00 y avisamos al cliente. Luego haces la devolución fuera de la app y la marcas como hecha.');
  await enviar(page, 'Aprobar devolución total').click();
  expect(envios[0].cuerpo).toEqual({ decision: 'total' });
  await page.waitForURL(/\/app\/pagos\/devoluciones\/?\?.*aviso=devolucion-decidida|\/app\/pagos\/devoluciones\/\?aviso=devolucion-decidida/);
  await expect(aviso(page)).toContainText('Decisión registrada. Avisamos al cliente por correo.');
  await expect(aviso(page)).toBeFocused();
  await sinViolaciones(page);
});

test('revisar: devolver todo, el motivo es opcional y sin mínimo, hasta 500', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  const envios = await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, json(200, devolucion({ estado: 'aprobada', monto_aprobado: '100.00' })));
  await colas(page, {});
  await revisar(page);
  await opcion(page, /Devolver todo/).check();
  await page.getByLabel(/^Motivo/).fill('corto');
  await enviar(page, 'Aprobar devolución total').click();
  expect(envios[0].cuerpo).toEqual({ decision: 'total', motivo: 'corto' });
});

test('revisar: devolución parcial valida el monto y el motivo, y manda el monto como texto decimal', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  const envios = await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, json(200, devolucion({ estado: 'aprobada', monto_aprobado: '60.00' })));
  await colas(page, {});
  await revisar(page);
  await enviar(page, /Registrar decisión|Aprobar|Rechazar/).first().click();
  await expect(page.getByText('Elige qué decides.').first()).toBeVisible();
  await expect(aviso(page)).toBeFocused();
  await opcion(page, /Devolver una parte/).check();
  await expect(page.getByLabel(/Monto a devolver/)).toBeVisible();
  await expect(decidir(page).getByRole('radio', { name: /Devolver una parte/ })).toHaveAttribute('aria-controls', /.+/);
  await expect(decidir(page)).toContainText('Se descuenta');
  await enviar(page, 'Aprobar devolución parcial').click();
  await expect(page.getByText('Escribe un monto entre S/ 0,01 y S/ 100,00.').first()).toBeVisible();
  for (const malo of ['0', '100,01', 'x']) {
    await page.getByLabel(/Monto a devolver/).fill(malo);
    await enviar(page, 'Aprobar devolución parcial').click();
    await expect(page.getByText('Escribe un monto entre S/ 0,01 y S/ 100,00.').first()).toBeVisible();
  }
  await page.getByLabel(/Monto a devolver/).fill('60');
  await enviar(page, 'Aprobar devolución parcial').click();
  await expect(page.getByText('Escribe el motivo de la devolución parcial.').first()).toBeVisible();
  expect(envios).toHaveLength(0);
  await page.getByLabel(/^Motivo/).fill('Solo devolvemos una parte');
  await enviar(page, 'Aprobar devolución parcial').click();
  expect(envios[0].cuerpo).toEqual({ decision: 'parcial', monto: '60.00', motivo: 'Solo devolvemos una parte' });
});

test('revisar: rechazar exige el motivo (10 a 500) y lo manda', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  const envios = await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, json(200, devolucion({ estado: 'rechazada', motivo_decision: 'Fuera de política' })));
  await colas(page, {});
  await revisar(page);
  await opcion(page, 'Rechazar').check();
  await expect(decidir(page)).toContainText('El crédito sigue igual y el cliente verá tu motivo');
  await expect(decidir(page)).toContainText('El cliente lo verá. Obligatorio si devuelves una parte o rechazas.');
  await enviar(page, 'Rechazar devolución').click();
  await expect(page.getByText('Escribe por qué la rechazas.').first()).toBeVisible();
  await page.getByLabel(/^Motivo/).fill('corto');
  await enviar(page, 'Rechazar devolución').click();
  await expect(page.getByText('El motivo debe tener entre 10 y 500 caracteres.').first()).toBeVisible();
  await page.getByLabel(/^Motivo/).evaluate((e) => { e.value = 'x'.repeat(501); });
  await enviar(page, 'Rechazar devolución').click();
  await expect(page.getByText('El motivo admite hasta 500 caracteres.').first()).toBeVisible();
  expect(envios).toHaveLength(0);
  await page.getByLabel(/^Motivo/).fill('Fuera de política');
  await enviar(page, 'Rechazar devolución').click();
  expect(envios[0].cuerpo).toEqual({ decision: 'rechazo', motivo: 'Fuera de política' });
  await page.waitForURL(/aviso=devolucion-decidida/);
});

test('revisar: enviando muestra la carga y bloquea los campos', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, async (r) => { await espera; await r.fulfill(json(200, devolucion({ estado: 'aprobada', monto_aprobado: '100.00' }))); });
  await colas(page, {});
  await revisar(page);
  await opcion(page, /Devolver todo/).check();
  await enviar(page, 'Aprobar devolución total').click();
  await expect(page.getByRole('button', { name: 'Aprobando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(opcion(page, 'Rechazar')).toBeDisabled();
  soltar();
});

for (const [codigo, texto] of [
  ['devolucion_decidida', 'Esta devolución ya se decidió, quizá desde otra sesión.'],
  ['devolucion_no_aprobada', 'Esta devolución no está aprobada: no se puede marcar como realizada.'],
]) {
  test(`revisar: 409 ${codigo} explica y recarga la ficha`, async ({ page }) => {
    let lecturas = 0;
    await simular(page, 'GET', `/devoluciones/${DV1}`, (r) => r.fulfill(json(200, devolucion(lecturas++ ? { estado: 'rechazada', decidida_en: '2026-11-15T14:00:00Z', motivo_decision: 'Ya rechazada' } : codigo === 'devolucion_no_aprobada' ? { estado: 'aprobada', monto_aprobado: '100.00' } : {}))));
    await simular(page, 'POST', `/devoluciones/${DV1}/${codigo === 'devolucion_decidida' ? 'decidir' : 'realizada'}`, (r) => r.fulfill(errorApi(409, codigo)));
    await revisar(page);
    if (codigo === 'devolucion_decidida') {
      await opcion(page, /Devolver todo/).check();
      await enviar(page, 'Aprobar devolución total').click();
    } else {
      await page.getByLabel(/Nota/).fill('Yape, operación 12345678');
      await page.getByRole('button', { name: 'Marcar como realizada' }).click();
    }
    await expect(aviso(page)).toContainText(texto);
    await expect(aviso(page)).toHaveClass(/aviso-informacion/);
    await expect(aviso(page)).toBeFocused();
    await expect(page.getByRole('region', { name: /V2/ })).toHaveCount(0);
    await sinViolaciones(page);
  });
}

test('revisar: 422 va bajo el campo y 503 avisa sin Reintentar', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion()));
  let respuesta = errorApi(422, 'monto_invalido');
  await simular(page, 'POST', `/devoluciones/${DV1}/decidir`, (r) => r.fulfill(respuesta));
  await revisar(page);
  await opcion(page, /Devolver una parte/).check();
  await page.getByLabel(/Monto a devolver/).fill('60');
  await page.getByLabel(/^Motivo/).fill('Solo devolvemos una parte');
  await enviar(page, 'Aprobar devolución parcial').click();
  await expect(page.getByText('Escribe un monto entre S/ 0,01 y S/ 100,00.').first()).toBeVisible();
  await expect(page.getByLabel(/Monto a devolver/)).toHaveAttribute('aria-invalid', 'true');
  respuesta = errorApi(422, 'motivo_requerido');
  await enviar(page, 'Aprobar devolución parcial').click();
  await expect(page.getByText('Escribe el motivo de la devolución parcial.').first()).toBeVisible();
  respuesta = errorApi(503, 'x');
  await enviar(page, 'Aprobar devolución parcial').click();
  await expect(aviso(page)).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
});

// --- Revisar: marcar realizada ---
const APROBADA = (extra = {}) => devolucion({ estado: 'aprobada', monto_aprobado: '60.00', decidida_en: '2026-11-14T15:00:00Z', ...extra });
test('revisar: aprobada pide la nota, la valida y marca como realizada', async ({ page }) => {
  const consola = vigilarConsola(page);
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, APROBADA()));
  const envios = await simular(page, 'POST', `/devoluciones/${DV1}/realizada`, json(200, APROBADA({ estado: 'realizada' })));
  await colas(page, {});
  await revisar(page);
  const panel = page.getByRole('region', { name: /V2 Devolver/i });
  await expect(panel).toContainText('S/ 60,00');
  await expect(panel).toContainText('Medio y número de operación. Por ejemplo: «Yape, operación 12345678».');
  await expect(panel).toContainText('El cliente recibe tu nota por correo y la ve en Mis créditos. No se puede deshacer.');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-devolucion-realizada-form-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Marcar como realizada' }).click();
  await expect(page.getByText('Escribe el medio y el número de operación.').first()).toBeVisible();
  await page.getByLabel(/Nota/).evaluate((e) => { e.value = 'x'.repeat(501); });
  await page.getByRole('button', { name: 'Marcar como realizada' }).click();
  await expect(page.getByText('La nota admite hasta 500 caracteres.').first()).toBeVisible();
  expect(envios).toHaveLength(0);
  await page.getByLabel(/Nota/).fill('Yape, operación 12345678');
  await page.getByRole('button', { name: 'Marcar como realizada' }).click();
  expect(envios[0].cuerpo).toEqual({ nota: 'Yape, operación 12345678' });
  await page.waitForURL(/aviso=devolucion-realizada/);
  await expect(aviso(page)).toContainText('Devolución marcada como hecha. Avisamos al cliente con tu nota.');
  expect(consola).toEqual([]);
});

test('revisar: la del estudio con el plazo vencido muestra FUERA DE PLAZO junto a "Venció el"', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, APROBADA({ tipo: 'estudio', id_credito: null, monto_aprobado: '300.00', monto_solicitado: '300.00', limite: '2026-11-10T23:59:59-05:00' })));
  await revisar(page);
  for (const region of [/V1 Solicitud/i, /V2 Devolver/i]) {
    await expect(page.getByRole('region', { name: region })).toContainText('Venció el 10 nov');
    await expect(page.getByRole('region', { name: region })).toContainText('Fuera de plazo');
  }
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-devolucion-revisar-fuera-de-plazo.png', fullPage: true });
});

test('revisar: la del estudio muestra su plazo en la solicitud y en el panel', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, APROBADA({ tipo: 'estudio', id_credito: null, monto_aprobado: '300.00', monto_solicitado: '300.00', limite: '2026-11-25T23:59:59-05:00' })));
  await revisar(page);
  await expect(page.getByRole('region', { name: /V1 Solicitud/i })).toContainText('Cancelación del estudio');
  await expect(page.getByRole('region', { name: /V1 Solicitud/i })).toContainText(/25 nov · faltan 10 d/);
  await expect(page.getByRole('region', { name: /V2 Devolver/i })).toContainText(/25 nov · faltan 10 d/);
  await expect(page.getByText('Motivo del cliente')).toHaveCount(0);
  await sinViolaciones(page);
});

test('revisar: realizada y rechazada muestran el resultado en una barra, sin formulario', async ({ page }) => {
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, APROBADA({ estado: 'realizada', realizada_en: '2026-11-15T09:00:00-05:00', nota_realizada: 'Yape, operación 12345678' })));
  await revisar(page);
  await expect(page.locator('.indicador')).toContainText('Realizada');
  await expect(page.locator('.indicador')).toContainText('15 nov');
  await expect(page.locator('main')).toContainText('Yape, operación 12345678');
  await expect(page.getByRole('button', { name: /Marcar como realizada|Aprobar/ })).toHaveCount(0);
  await sinViolaciones(page);
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion({ estado: 'rechazada', decidida_en: '2026-11-14T10:00:00-05:00', motivo_decision: 'Fuera de política' })));
  await revisar(page);
  await expect(page.locator('.indicador')).toContainText('Rechazada');
  await expect(page.locator('main')).toContainText('Fuera de política');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-devolucion-rechazada-1440.png', fullPage: true });
});

// --- Revisar: estados de la pantalla ---
test('revisar: id que no es UUID o devolución inexistente muestran "no encontrada"', async ({ page }) => {
  const vistas = await simular(page, 'GET', '/devoluciones/abc', json(200, devolucion()));
  await page.goto('/app/pagos/devoluciones/revisar?id=abc');
  await expect(page.getByRole('heading', { name: /\[404\] Devolución no encontrada/i })).toBeVisible();
  await expect(page.getByText('No encontramos esta devolución.').first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a devoluciones' })).toHaveAttribute('href', '/app/pagos/devoluciones');
  expect(vistas).toHaveLength(0);
  await simular(page, 'GET', `/devoluciones/${DV1}`, (r) => r.fulfill(errorApi(404, 'no_encontrada')));
  await revisar(page);
  await expect(page.getByRole('heading', { name: /\[404\] Devolución no encontrada/i })).toBeVisible();
  await sinViolaciones(page);
});

for (const f of fallos) {
  test(`revisar: ${f.n} al cargar`, async ({ page }) => {
    await simular(page, 'GET', `/devoluciones/${DV1}`, f.r);
    await revisar(page);
    await expect(page.locator('[data-salida]')).toContainText(f.texto);
    await sinViolaciones(page);
  });
}
