// RF-15 etapa B, ampliaciones: pagos, creditos y devoluciones que nacen de una asesoria. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador } from './ayudas-admin.js';
import { AHORA, CR1, CR2, DV1, credito, devolucion } from './ayudas-rf18.js';

const PID = '3f2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e6f';
const AID = '22222222-2222-4222-8222-222222222222';
const sinDesborde = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const pago = (extra = {}) => ({
  id: PID, estado: 'pendiente_validacion', metodo: 'yape', monto: '140.00', numero_operacion: 'ABC123',
  registrado_en: '2026-11-15T12:00:00Z', monto_coincide: true,
  cuota: { id: 'c1', hito: 'al_reservar', monto: '140.00' },
  reserva: { id: AID, tipo: 'asesoria', folio: 'A-2026-00001', inicio: '2026-12-18T20:00:00Z', estado: 'pre_reservada' },
  cliente: { id: 'u9', nombre: 'Ana Pérez' }, ...extra,
});
const SALA = pago({ id: '4a2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e70', reserva: { id: 'r1', tipo: 'sala', folio: 'R-2026-00042', inicio: '2026-11-20T15:00:00Z', estado: 'pre_reservada' } });

async function pagos(page, lista) {
  await page.clock.setFixedTime(AHORA);
  await comoAdministrador(page);
  await simular(page, 'GET', '/pagos', json(200, lista));
  await simular(page, 'GET', `/pagos/${PID}`, json(200, pago()));
  await simular(page, 'GET', `/pagos/${PID}/captura`, json(200, { url: 'http://supabase.prueba/c.png', expira_en: '2026-11-15T15:10:00Z', tipo: 'imagen' }));
  await page.route('http://supabase.prueba/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64') }));
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, { id: AID, duracion: 60, profesional: { id: 'p1', nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat' } }));
}

for (const t of tamanos) {
  test(`pagos: la fila de una asesoria enlaza a su detalle y la de sala no, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await pagos(page, [pago(), SALA]);
    await page.goto('/app/pagos/');
    await expect(page.getByRole('link', { name: 'A-2026-00001', exact: true })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
    await expect(page.getByRole('link', { name: 'R-2026-00042', exact: true })).toHaveCount(0);
    await expect(page.getByRole('rowheader').first()).toContainText('Asesoría · Pago único');
    await expect(page.getByRole('columnheader', { name: 'Reserva' })).toBeVisible();
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15b7-pagos-lista-${t.nombre}.png`, fullPage: true });
  });

  test(`pagos: con solo asesorias la columna dice ASESORIA y revisar muestra la asesoria, a ${t.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await pagos(page, [pago()]);
    await page.goto('/app/pagos/');
    await expect(page.getByRole('columnheader', { name: 'Asesoría' })).toBeVisible();
    await page.goto(`/app/pagos/revisar?id=${PID}`);
    const v3 = page.getByRole('region', { name: /V3 Asesoría/i });
    await expect(v3.getByRole('link', { name: 'A-2026-00001' })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
    await expect(v3.getByText('Asesoría de 1 h con Ana Beat')).toBeVisible();
    await expect(v3.getByText('Pendiente de pago')).toBeVisible();
    await expect(page.locator('.encabezado-descripcion')).toContainText('de la asesoría A-2026-00001');
    await expect(page.getByText('Al aprobar, la cuota queda pagada, la asesoría se confirma y avisamos al cliente.')).toBeVisible();
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    await page.screenshot({ path: `pruebas/capturas/rf15b7-pagos-revisar-${t.nombre}.png`, fullPage: true });
  });
}

test('pagos: si la asesoria no carga, V3 conserva la fecha y aprobar vuelve con el aviso de asesoria', async ({ page }) => {
  await pagos(page, [pago()]);
  await simular(page, 'GET', `/asesorias/${AID}`, json(503, { error: { codigo: 'servicio_no_disponible', mensaje: 'x' } }));
  const aprobar = await simular(page, 'POST', `/pagos/${PID}/aprobar`, json(200, pago({ estado: 'aprobado', reserva: { ...pago().reserva, estado: 'confirmada' } })));
  await page.goto(`/app/pagos/revisar?id=${PID}`);
  await expect(page.getByRole('region', { name: /V3 Asesoría/i })).toContainText('18 dic 2026, 15:00');
  await page.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(page).toHaveURL(/aviso=asesoria-confirmada/);
  await expect(page.locator('[data-avisos] .aviso')).toContainText('La asesoría quedó confirmada y avisamos al cliente.');
  expect(aprobar).toHaveLength(1);
});

// --- Creditos ---
const comoCliente = async (page) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
};
for (const t of tamanos) {
  test(`creditos: el de una asesoria enlaza a su detalle y no ofrece devolucion, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page);
    await simular(page, 'GET', '/creditos', json(200, [
      credito({ id: CR1, tipo: 'excepcion', origen: { id_reserva: AID, folio: 'A-2026-00001', tipo: 'asesoria' } }),
      credito({ id: CR2, tipo: 'nivel_1', origen: { id_reserva: 'r2', folio: 'R-2026-00002', tipo: 'sala' } }),
    ]));
    await page.goto('/app/reservas/creditos');
    await expect(page.getByRole('link', { name: 'A-2026-00001' })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
    await expect(page.getByRole('link', { name: 'R-2026-00002' })).toHaveAttribute('href', '/app/reservas/detalle?id=r2');
    const filaA = page.getByRole('row').filter({ hasText: 'A-2026-00001' });
    await expect(filaA).toContainText('· asesoría');
    await expect(filaA).toContainText('Sin devolución: nació de una asesoría.');
    await expect(filaA.getByRole('button', { name: /Pedir devolución/ })).toHaveCount(0);
    await expect(page.getByRole('row').filter({ hasText: 'R-2026-00002' }).getByRole('button', { name: /Pedir devolución/ })).toBeVisible();
    await expect(page.getByRole('region', { name: /Cómo funciona/i })).toContainText('Úsalo en tus reservas o asesorías.');
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15b7-creditos-${t.nombre}.png`, fullPage: true });
  });
}

test('creditos: 409 devolucion_no_permitida de un crédito de sala conserva su texto', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', '/creditos', json(200, [credito({ id: CR1, tipo: 'excepcion', origen: { id_reserva: 'r2', folio: 'R-2026-00002', tipo: 'sala' } })]));
  await simular(page, 'POST', `/creditos/${CR1}/devolucion`, json(409, { error: { codigo: 'devolucion_no_permitida', mensaje: 'x' } }));
  await page.goto('/app/reservas/creditos');
  await page.getByRole('button', { name: /Pedir devolución/ }).click();
  await page.getByRole('textbox', { name: /Motivo/ }).fill('Prefiero el dinero porque no voy a volver.');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Este crédito no admite devolución.');
});

// --- Devoluciones (Administrador) ---
test('devoluciones: el enlace sigue Devolucion.reserva.tipo', async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await comoAdministrador(page);
  const dev = devolucion({ id: DV1, folio: 'A-2026-00001', id_reserva: AID, reserva: { id: AID, folio: 'A-2026-00001', tipo: 'asesoria' } });
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, dev));
  await page.goto(`/app/pagos/devoluciones/revisar?id=${DV1}`);
  await expect(page.getByRole('link', { name: 'A-2026-00001' }).first()).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
  await expect(page.locator('dt', { hasText: 'Asesoría' })).toBeVisible();
  await sinViolaciones(page);
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion({ id: DV1, reserva: { id: 'r1', folio: 'R-2026-00001', tipo: 'sala' } })));
  await page.goto(`/app/pagos/devoluciones/revisar?id=${DV1}`);
  await expect(page.getByRole('link', { name: 'R-2026-00001' }).first()).toHaveAttribute('href', /\/app\/reservas\/detalle\?id=/);
});

test('320 px: pagos, revisar, creditos y devolucion de una asesoria sin desborde', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await pagos(page, [pago(), SALA]);
  await simular(page, 'GET', '/creditos', json(200, [credito({ id: CR1, tipo: 'excepcion', origen: { id_reserva: AID, folio: 'A-2026-00001', tipo: 'asesoria' } })]));
  await simular(page, 'GET', `/devoluciones/${DV1}`, json(200, devolucion({ id: DV1, folio: 'A-2026-00001', id_reserva: AID, reserva: { id: AID, folio: 'A-2026-00001', tipo: 'asesoria' } })));
  for (const ruta of ['/app/pagos/', `/app/pagos/revisar?id=${PID}`, `/app/pagos/devoluciones/revisar?id=${DV1}`]) {
    await page.goto(ruta);
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
    expect(await sinDesborde(page)).toBe(true);
  }
});
