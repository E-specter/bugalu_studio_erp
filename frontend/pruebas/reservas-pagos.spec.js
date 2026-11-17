// RF-05 (CA-09) y RF-06 (CA-04, CA-05) en mis reservas: cuotas con su estado de pago, pago por validar, saldo, nota de cancelación.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';

const ID = '11111111-1111-4111-8111-111111111111';
const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const C2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const AHORA = new Date('2026-11-15T15:00:00Z');
const dentroDe = (min) => new Date(AHORA.getTime() + min * 60e3).toISOString();
const SIMULACION = { lineas: [{ concepto: 'Sala de grabación', cantidad: '2.50', unidad: 'hora', monto: '415.00' }], recargos: [], total: '415.00', anticipo: '207.50' };
const pago = (extra = {}) => ({ id: 'p1', estado: 'pendiente_validacion', metodo: 'yape', monto: '207.50', numero_operacion: 'OP1234', motivo_rechazo: null, registrado_en: '2026-11-15T12:00:00Z', ...extra });
const cuotas = (a = {}, b = {}) => [
  { id: C1, hito: 'al_reservar', monto: '207.50', estado: 'pendiente', pagable: true, pagos: [], ...a },
  { id: C2, hito: 'al_terminar', monto: '207.50', estado: 'pendiente', pagable: false, pagos: [], ...b },
];
const pagada = { estado: 'pagada', pagable: false, pagos: [pago({ estado: 'aprobado' })] };
const enValidacion = { estado: 'en_validacion', pagable: false, pagos: [pago()] };
const reserva = (extra = {}) => ({
  id: ID, folio: 'R-2026-00001', estado: 'pre_reservada', motivo_cancelacion: null, nota_cancelacion: null, pago_por_validar: false,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:30:00-05:00', sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [],
  precio: SIMULACION, vence_pago: dentroDe(2 * 1440 + 3 * 60 + 30), cuotas: cuotas(), ...extra,
});
const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
const ver = (page, query = '') => page.goto(`/app/reservas/detalle?id=${ID}${query}`);
const barra = (page) => page.locator('[data-estado-reserva]');

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'cliente');
  await simular(page, 'GET', '/contacto-estudio', json(200, { texto: 'WhatsApp 999 000 111' }));
});
const con = (page, r) => simular(page, 'GET', `/reservas/${ID}`, json(200, r));

for (const t of tamanos) {
  test(`detalle: cuota pendiente con "Registrar pago" primario hacia la pantalla de pago, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await con(page, reserva());
    await ver(page);
    const enlace = page.getByRole('link', { name: 'Registrar pago' });
    await expect(enlace).toHaveAttribute('href', `/app/reservas/pagar?id=${ID}&cuota=${C1}`);
    await expect(enlace).toHaveClass(/boton-primario/);
    await expect(page.getByRole('row', { name: /Al reservar/ })).toContainText('Pendiente');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reservas-detalle-pagar-${t.nombre}.png`, fullPage: true });
  });

  test(`detalle: pago por validar, cuota en validación y sin caducar, a ${t.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await con(page, reserva({ pago_por_validar: true, vence_pago: dentroDe(-30), cuotas: cuotas(enValidacion) }));
    await ver(page);
    await expect(barra(page)).toContainText('Pago en validación');
    await expect(barra(page)).toContainText('Registraste tu pago. No caduca mientras el estudio lo revise; te avisaremos por correo.');
    await expect(barra(page)).not.toContainText('faltan');
    await expect(page.getByText('Caducada')).toHaveCount(0);
    await expect(page.getByText('Pago por validar', { exact: true })).toBeVisible();
    await expect(page.getByRole('row', { name: /Al reservar/ })).toContainText('En validación');
    await expect(page.getByRole('link', { name: /Registrar pago/ })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Solicitar cancelación' })).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/reservas-detalle-validacion-${t.nombre}.png`, fullPage: true });
  });
}

test('detalle: último rechazo con su motivo y se puede registrar de nuevo', async ({ page }) => {
  await con(page, reserva({ cuotas: cuotas({ pagos: [pago({ estado: 'rechazado', motivo_rechazo: 'La captura no se lee', registrado_en: '2026-11-16T15:20:00Z' })] }) }));
  await ver(page);
  await expect(page.getByRole('row', { name: /Al reservar/ })).toContainText('Pago rechazado el 16 nov: La captura no se lee');
  await expect(page.getByRole('link', { name: 'Registrar pago' })).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-rechazo.png', fullPage: true });
});

test('detalle: confirmada con resto pendiente ofrece adelantar el pago (secundario)', async ({ page }) => {
  await con(page, reserva({ estado: 'confirmada', vence_pago: null, cuotas: cuotas(pagada, { pagable: true }) }));
  await ver(page);
  await expect(barra(page)).toContainText('Pagas el resto al terminar la sesión.');
  const enlace = page.getByRole('link', { name: 'Adelantar el pago del resto' });
  await expect(enlace).toHaveAttribute('href', `/app/reservas/pagar?id=${ID}&cuota=${C2}`);
  await expect(enlace).toHaveClass(/boton-secundario/);
  await expect(page.getByRole('row', { name: /Al reservar/ })).toContainText('Pagada');
  await sinViolaciones(page);
});

test('detalle: en curso y el resto en validación o pagado', async ({ page }) => {
  await con(page, reserva({ estado: 'en_curso', vence_pago: null, cuotas: cuotas(pagada, { pagable: true }) }));
  await ver(page);
  await expect(barra(page)).toContainText('En curso');
  await expect(barra(page)).toContainText('Pagas el resto al terminar.');
  await expect(page.getByRole('link', { name: 'Adelantar el pago del resto' })).toBeVisible();
  await con(page, reserva({ estado: 'confirmada', vence_pago: null, cuotas: cuotas(pagada, enValidacion) }));
  await ver(page);
  await expect(barra(page)).toContainText('Pago del resto en validación');
  await expect(page.getByRole('link', { name: /pago del resto|Registrar pago/ })).toHaveCount(0);
  await con(page, reserva({ estado: 'confirmada', vence_pago: null, cuotas: cuotas(pagada, pagada) }));
  await ver(page);
  await expect(barra(page)).toContainText('Pagada');
});

test('detalle: finalizada con saldo, con el resto en validación y todo pagado', async ({ page }) => {
  await con(page, reserva({ estado: 'finalizada', vence_pago: null, cuotas: cuotas(pagada, { pagable: true }) }));
  await ver(page);
  await expect(barra(page)).toContainText('Falta pagar el resto: S/ 207,50');
  await expect(page.getByRole('link', { name: 'Registrar pago' })).toHaveClass(/boton-primario/);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-finalizada-saldo.png', fullPage: true });
  await con(page, reserva({ estado: 'finalizada', vence_pago: null, cuotas: cuotas(pagada, enValidacion) }));
  await ver(page);
  await expect(barra(page)).toContainText('Pago del resto en validación');
  await con(page, reserva({ estado: 'finalizada', vence_pago: null, cuotas: cuotas(pagada, pagada) }));
  await ver(page);
  await expect(barra(page)).toContainText('Finalizada');
  await expect(barra(page)).toContainText('Pagada');
});

test('detalle: cancelada con la nota del estudio', async ({ page }) => {
  await con(page, reserva({ estado: 'cancelada', motivo_cancelacion: 'administrador', vence_pago: null, nota_cancelacion: 'Devolvemos S/ 207,50 por Yape en 48 h', cuotas: cuotas(pagada) }));
  await ver(page);
  await expect(barra(page)).toContainText('La canceló el estudio.');
  await expect(barra(page)).toContainText('Nota del estudio: Devolvemos S/ 207,50 por Yape en 48 h');
  await sinViolaciones(page);
});

test('detalle: el personal no registra pagos', async ({ page }) => {
  await comoRol(page, 'personal');
  await con(page, reserva({ cliente: 'Ana Pérez' }));
  await ver(page);
  await expect(page.getByRole('link', { name: /Registrar pago/ })).toHaveCount(0);
});

test('detalle: ?aviso=pago-registrado muestra el aviso con foco y quita el parámetro', async ({ page }) => {
  await con(page, reserva({ pago_por_validar: true, cuotas: cuotas(enValidacion) }));
  await ver(page, '&aviso=pago-registrado');
  const aviso = page.locator('[data-avisos] .aviso');
  await expect(aviso).toContainText('Pago registrado. Queda pendiente de validación.');
  await expect(aviso).toContainText('Te avisaremos por correo cuando el estudio lo revise.');
  await expect(aviso).toBeFocused();
  expect(page.url()).not.toContain('aviso=');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-detalle-aviso-pago.png', fullPage: true });
  await ver(page, '&aviso=otra-cosa');
  await expect(page.locator('[data-avisos] .aviso')).toHaveCount(0);
});

// --- Lista: columna PAGO ---
test('lista: la columna PAGO dice pago por validar, saldo, pagada o nada', async ({ page }) => {
  const lista = [
    reserva({ id: 'a', folio: 'A-1', pago_por_validar: true, cuotas: cuotas(enValidacion) }),
    reserva({ id: 'b', folio: 'B-2', estado: 'confirmada', vence_pago: null, inicio: '2027-01-10T10:00:00-05:00', fin: '2027-01-10T12:00:00-05:00', cuotas: cuotas(pagada) }),
    reserva({ id: 'c', folio: 'C-3', estado: 'en_curso', vence_pago: null, inicio: '2027-01-11T10:00:00-05:00', fin: '2027-01-11T12:00:00-05:00', cuotas: cuotas(pagada, enValidacion) }),
    reserva({ id: 'd', folio: 'D-4', estado: 'confirmada', vence_pago: null, inicio: '2027-01-12T10:00:00-05:00', fin: '2027-01-12T12:00:00-05:00', cuotas: cuotas(pagada, pagada) }),
    reserva({ id: 'e', folio: 'E-5', estado: 'finalizada', vence_pago: null, inicio: '2026-10-01T10:00:00-05:00', fin: '2026-10-01T11:00:00-05:00', cuotas: cuotas(pagada) }),
    reserva({ id: 'f', folio: 'F-6', estado: 'cancelada', motivo_cancelacion: 'administrador', vence_pago: null, inicio: '2026-09-01T10:00:00-05:00', fin: '2026-09-01T11:00:00-05:00', cuotas: cuotas(pagada) }),
  ];
  await simular(page, 'GET', '/reservas/mias', json(200, lista));
  await page.goto('/app/reservas/');
  const fila = (folio) => page.getByRole('row', { name: new RegExp(folio) });
  await expect(fila('A-1')).toContainText('En validación');
  await expect(fila('A-1')).not.toContainText('Antes del');
  await expect(fila('A-1')).not.toContainText('faltan');
  await expect(fila('B-2')).toContainText('Resto: S/ 207,50');
  await expect(fila('C-3')).toContainText('En validación');
  await expect(fila('D-4')).toContainText('Pagada');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reservas-lista-pagos.png', fullPage: true });
  await page.goto('/app/reservas/?ver=historial');
  await expect(fila('E-5')).toContainText('Resto: S/ 207,50');
  await expect(fila('F-6').getByRole('cell').nth(3)).toHaveText('—');
});
