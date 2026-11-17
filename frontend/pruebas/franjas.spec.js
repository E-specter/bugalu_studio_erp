// RF-03 (CA-02, CA-03, CA-04, CA-07): franjas, cierres y parametros del Administrador. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const SALA = { id: 'sala-1', nombre: 'Sala La Molina' };
const SEMANA = '2026-W47'; // lunes 16 a domingo 22 nov 2026
const FRANJAS = [
  { id: 'f1', inicio: '2026-11-17T10:00:00-05:00', fin: '2026-11-17T14:00:00-05:00' },
  { id: 'f2', inicio: '2026-11-18T10:00:00-05:00', fin: '2026-11-18T14:00:00-05:00' },
];
const OCUPADOS = [{ inicio: '2026-11-18T10:00:00-05:00', fin: '2026-11-18T12:30:00-05:00', propia: false, detalle: { id_reserva: 'r1', cliente: 'Eva Soto', servicio: 'Grabación de voces', estado: 'Confirmada' } }];
const CIERRES = [{ id: 'c1', inicio: '2026-11-20T00:00:00-05:00', fin: '2026-11-21T00:00:00-05:00', motivo: 'Mantenimiento' }];
const disp = (extra = {}) => json(200, { limites: { desde: '2026-11-16T00:00:00-05:00', hasta: '2027-05-01T00:00:00-05:00' }, franjas: FRANJAS, ocupados: OCUPADOS, cierres: CIERRES, dias: [], ...extra });
const PARAMETROS = {
  dias_limite_pago: 3, horas_limite_pago: 24, anticipacion_minima_horas: 2, anticipacion_maxima_semanas: 8,
  porcentaje_adelanto: 50, horas_nivel_1: 48, horas_nivel_2: 24, porcentaje_penalizacion_nivel_2: 25, minutos_tolerancia_inasistencia: 15,
  dias_vigencia_credito: 30, reprogramaciones_nivel_1: 2, reprogramaciones_nivel_2: 1,
};

async function base(page, { disponibilidad = disp(), sugerencia = json(200, []) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z')); // "hoy" fijo: el domingo 15 nov 2026
  await comoAdministrador(page);
  await simular(page, 'GET', '/salas', json(200, [SALA]));
  const vistasDisp = await simular(page, 'GET', '/disponibilidad', disponibilidad);
  const vistasSug = await simular(page, 'GET', '/franjas/sugerencia', sugerencia);
  return { vistasDisp, vistasSug };
}
const f3 = (page) => page.getByRole('region', { name: /Cierres/ });
const f2 = (page) => page.getByRole('region', { name: /Publicar franjas/ });
const dia = (page, nombre) => page.getByRole('group', { name: nombre });

// --- 1. Semana con franjas publicadas ---
for (const t of tamanos) {
  test(`semana: publicadas, reservas, cierres y periodo a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const { vistasDisp } = await base(page);
    await page.goto(`/app/franjas?semana=${SEMANA}`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/franjas de sala/i);
    await expect(page.getByText('SEMANA DEL 16 AL 22 NOV 2026')).toBeVisible();
    expect(vistasDisp[0].url.searchParams.get('sala')).toBe('sala-1');
    expect(vistasDisp[0].url.searchParams.get('desde')).toBe('2026-11-16T00:00:00-05:00');
    expect(vistasDisp[0].url.searchParams.get('hasta')).toBe('2026-11-23T00:00:00-05:00');
    await expect(page.getByRole('link', { name: 'Semana anterior' })).toHaveAttribute('href', '/app/franjas?semana=2026-W46');
    await expect(page.getByRole('link', { name: 'Semana siguiente' })).toHaveAttribute('href', '/app/franjas?semana=2026-W48');
    await expect(page.getByRole('link', { name: 'Esta semana' })).toHaveAttribute('href', '/app/franjas');
    await expect(page.getByRole('link', { name: 'Parámetros de reserva' })).toHaveAttribute('href', '/app/franjas/parametros');
    const filas = page.getByRole('table', { name: 'Franjas publicadas' }).getByRole('row');
    await expect(filas).toHaveCount(3);
    await expect(filas.nth(1)).toContainText('MAR 17 NOV');
    await expect(filas.nth(1)).toContainText('10:00–14:00');
    await expect(filas.nth(2)).toContainText('1 reserva');
    await expect(page.getByRole('button', { name: 'Retirar franja del martes 17 de 10:00 a 14:00' })).not.toHaveAttribute('aria-disabled', 'true');
    const bloqueada = page.getByRole('button', { name: 'Retirar franja del miércoles 18 de 10:00 a 14:00' });
    await expect(bloqueada).toHaveAttribute('aria-disabled', 'true');
    await expect(bloqueada).toHaveAccessibleDescription('Tiene reservas vigentes');
    await expect(f3(page).getByRole('table', { name: 'Cierres de la semana' }).getByRole('row').nth(1)).toContainText('Todo el día');
    await expect(f3(page)).toContainText('Mantenimiento');
    await expect(f2(page).getByRole('group')).toHaveCount(7);
    await expect(f2(page).getByText('Para abrir horas extra, añade franjas y publícalas.')).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/franjas-semana-${t.nombre}.png`, fullPage: true });
  });
}

test('semana sin franjas: llega con la plantilla sugerida y publica solo filas completas', async ({ page }) => {
  const consola = vigilarConsola(page);
  const { vistasSug } = await base(page, {
    disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }),
    sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }, { inicio: '2026-11-22T22:00:00-05:00', fin: '2026-11-23T00:00:00-05:00' }]),
  });
  const publicadas = await simular(page, 'POST', '/franjas', json(201, []));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await expect(page.getByText('No hay franjas publicadas esta semana')).toBeVisible();
  await expect(page.getByText('Abajo tienes una propuesta: edítala y publícala.')).toBeVisible();
  await expect(page.getByText('Te proponemos la última semana publicada. Cambia lo que haga falta antes de publicar.')).toBeVisible();
  expect(vistasSug[0].url.searchParams.get('semana')).toBe(SEMANA);
  expect(vistasSug[0].url.searchParams.get('sala')).toBe('sala-1');
  const lunes = dia(page, 'LUNES 16 NOV');
  await expect(lunes.getByLabel('Desde')).toHaveValue('10:00');
  await expect(lunes.getByLabel('Hasta')).toHaveValue('14:00');
  await expect(dia(page, 'DOMINGO 22 NOV').getByLabel('Hasta')).toHaveValue('00:00');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/franjas-plantilla-1440.png', fullPage: true });
  await dia(page, 'MARTES 17 NOV').getByRole('button', { name: 'Añadir franja al martes' }).click();
  await expect(dia(page, 'MARTES 17 NOV').getByLabel('Desde')).toBeFocused();
  await page.getByRole('button', { name: 'Publicar franjas' }).click(); // la fila vacia no cuenta
  await expect(page.getByText('Franjas publicadas. Ya se ven en el calendario.')).toBeVisible();
  expect(publicadas[0].cuerpo).toEqual({ id_sala: 'sala-1', franjas: [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }, { inicio: '2026-11-22T22:00:00-05:00', fin: '2026-11-23T00:00:00-05:00' }] });
  expect(consola).toEqual([]);
});

test('semana sin franjas ni sugerencia: aviso y editor vacio', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }) });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await expect(page.getByText('No hay una semana anterior que copiar. Añade las franjas de cada día.')).toBeVisible();
  await expect(f3(page).getByText('No hay cierres esta semana.')).toBeVisible();
  await sinViolaciones(page);
});

test('editor: quitar una fila devuelve el foco a Añadir franja de ese dia', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }]) });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Quitar franja de 10:00 a 14:00 del lunes' }).click();
  await expect(page.getByRole('button', { name: 'Añadir franja al lunes' })).toBeFocused();
  await expect(dia(page, 'LUNES 16 NOV').getByLabel('Desde')).toHaveCount(0);
});

test('editor: validacion por fila y resumen con enlaces', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }]) });
  const llamadas = await simular(page, 'POST', '/franjas', json(201, []));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  const lunes = dia(page, 'LUNES 16 NOV');
  await lunes.getByRole('button', { name: 'Añadir franja al lunes' }).click(); // segunda fila
  const filas = lunes.getByRole('group');
  await filas.nth(1).getByLabel('Hasta').fill('09:00'); // sin inicio
  await lunes.getByRole('button', { name: 'Añadir franja al lunes' }).click(); // tercera
  await filas.nth(2).getByLabel('Desde').fill('12:00'); // cruza con 10-14 y termina antes
  await filas.nth(2).getByLabel('Hasta').fill('12:15'); // no es en punto ni y media
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByText('Revisa 2 franjas')).toBeVisible();
  await expect(filas.nth(1)).toContainText('Elige la hora de inicio.');
  await expect(filas.nth(2)).toContainText('Usa horas en punto o y media.');
  await expect(filas.nth(1).getByLabel('Desde')).toHaveAttribute('aria-invalid', 'true');
  expect(llamadas).toHaveLength(0);
  await filas.nth(1).getByLabel('Desde').fill('08:00');
  await filas.nth(1).getByLabel('Hasta').fill('11:00');
  await filas.nth(2).getByLabel('Hasta').fill('13:00');
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(filas.nth(1)).toContainText('Se cruza con la franja de 10:00–14:00 del mismo día.');
  await expect(filas.nth(2)).toContainText('Se cruza con la franja de 10:00–14:00 del mismo día.');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/franjas-validacion-1440.png', fullPage: true });
  expect(llamadas).toHaveLength(0);
});

test('editor: hora de fin anterior a la de inicio', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T14:00:00-05:00', fin: '2026-11-16T10:00:00-05:00' }]) });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(dia(page, 'LUNES 16 NOV')).toContainText('La hora de fin debe ser posterior a la de inicio.');
});

test('publicar: 409 franja_solapada explica y conserva las filas', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }]) });
  await simular(page, 'POST', '/franjas', json(409, { error: { codigo: 'franja_solapada', mensaje: 'x' } }));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  const aviso = page.getByText('Una de las franjas se cruza con otra ya publicada. Revisa las horas y vuelve a publicar.');
  await expect(aviso).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(dia(page, 'LUNES 16 NOV').getByLabel('Desde')).toHaveValue('10:00');
  await expect(page.getByRole('button', { name: 'Publicar franjas' })).toBeEnabled();
  await sinViolaciones(page);
});

test('publicar: carga bloquea los otros envios', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }]) });
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'POST', '/franjas', async (r) => { await llega; await r.fulfill(json(201, [])); });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(page.getByRole('button', { name: 'Publicando…' })).toBeDisabled();
  await expect(f3(page).getByRole('button', { name: 'Registrar cierre' })).toBeDisabled();
  soltar();
  await expect(page.getByText('Franjas publicadas.')).toBeVisible();
});

test('publicar: error de red conserva los datos y no ofrece Reintentar', async ({ page }) => {
  await base(page, { disponibilidad: disp({ franjas: [], ocupados: [], cierres: [] }), sugerencia: json(200, [{ inicio: '2026-11-16T10:00:00-05:00', fin: '2026-11-16T14:00:00-05:00' }]) });
  await simular(page, 'POST', '/franjas', (r) => r.abort('connectionrefused'));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(page.getByText('Sin conexión. Revisa tu red y vuelve a intentarlo.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await expect(dia(page, 'LUNES 16 NOV').getByLabel('Desde')).toHaveValue('10:00');
});

// --- 2. Retirar franja ---
test('retirar: borra la franja, recarga y avisa', async ({ page }) => {
  await base(page);
  const borrados = await simular(page, 'DELETE', '/franjas/f1', { status: 204, body: '' });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Retirar franja del martes 17 de 10:00 a 14:00' }).click();
  await expect(page.getByText('Franja retirada.')).toBeVisible();
  expect(borrados).toHaveLength(1);
});

test('retirar: la franja con reservas no llama a la API', async ({ page }) => {
  await base(page);
  const borrados = await simular(page, 'DELETE', '/franjas/f2', { status: 204, body: '' });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Retirar franja del miércoles 18 de 10:00 a 14:00' }).click({ force: true });
  expect(borrados).toHaveLength(0);
});

test('retirar: 409 franja_con_reservas y 404', async ({ page }) => {
  await base(page);
  await simular(page, 'DELETE', '/franjas/f1', json(409, { error: { codigo: 'franja_con_reservas', mensaje: 'x' } }));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Retirar franja del martes 17 de 10:00 a 14:00' }).click();
  await expect(page.getByText('Esta franja tiene reservas vigentes. Cancélalas o espera a que terminen antes de retirarla.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await sinViolaciones(page);
  await page.route(/\/franjas\/f1$/, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
  await page.getByRole('button', { name: 'Retirar franja del martes 17 de 10:00 a 14:00' }).click();
  await expect(page.getByText('Esa franja ya no existe. Actualizamos la semana.')).toBeVisible();
});

// --- 3. Cierres ---
test('cierre: dia entero con motivo', async ({ page }) => {
  await base(page, { disponibilidad: disp({ cierres: [] }) });
  const cierres = await simular(page, 'POST', '/cierres', json(201, { id: 'c9' }));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await f3(page).getByRole('button', { name: 'Registrar cierre' }).click();
  await expect(f3(page).getByText('Elige la fecha.')).toBeVisible();
  await expect(f3(page).getByText('Escribe el motivo; lo verán los clientes en el calendario.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  expect(cierres).toHaveLength(0);
  await f3(page).getByLabel('Fecha').fill('2026-11-24');
  await f3(page).getByLabel('Motivo').fill('Feriado');
  await f3(page).getByRole('button', { name: 'Registrar cierre' }).click();
  await expect(page.getByText('Cierre registrado.')).toBeVisible();
  expect(cierres[0].cuerpo).toEqual({ id_sala: 'sala-1', inicio: '2026-11-24T00:00:00-05:00', fin: '2026-11-25T00:00:00-05:00', motivo: 'Feriado' });
});

test('cierre: por horas pide desde y hasta', async ({ page }) => {
  await base(page, { disponibilidad: disp({ cierres: [] }) });
  const cierres = await simular(page, 'POST', '/cierres', json(201, { id: 'c9' }));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await expect(f3(page).getByLabel('Desde')).toBeHidden();
  await f3(page).getByLabel('Todo el día').uncheck();
  await f3(page).getByLabel('Fecha').fill('2026-11-19');
  await f3(page).getByLabel('Desde').fill('15:00');
  await f3(page).getByLabel('Hasta').fill('14:00');
  await f3(page).getByLabel('Motivo').fill('Mantenimiento');
  await f3(page).getByRole('button', { name: 'Registrar cierre' }).click();
  await expect(f3(page).getByText('La hora de fin debe ser posterior a la de inicio.')).toBeVisible();
  await f3(page).getByLabel('Hasta').fill('17:00');
  await f3(page).getByRole('button', { name: 'Registrar cierre' }).click();
  await expect(page.getByText('Cierre registrado.')).toBeVisible();
  expect(cierres[0].cuerpo).toMatchObject({ inicio: '2026-11-19T15:00:00-05:00', fin: '2026-11-19T17:00:00-05:00' });
});

test('cierre: 409 cierre_con_reservas lista las reservas y conserva los datos', async ({ page }) => {
  await base(page, { disponibilidad: disp({ cierres: [] }) });
  await simular(page, 'POST', '/cierres', json(409, { error: { codigo: 'cierre_con_reservas', mensaje: 'x', detalles: { reservas: [{ id: 'r1', folio: 'BG-0001', inicio: '2026-11-18T10:00:00-05:00', cliente: 'Eva Soto' }, { id: 'r2', folio: 'BG-0002', inicio: '2026-11-18T15:30:00-05:00', cliente: 'Luis Mora' }] } } }));
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await f3(page).getByLabel('Fecha').fill('2026-11-18');
  await f3(page).getByLabel('Motivo').fill('Feriado');
  await f3(page).getByRole('button', { name: 'Registrar cierre' }).click();
  await expect(page.getByText('No puedes cerrar ese horario: tiene 2 reservas vigentes. Resuélvelas antes de cerrarlo.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByRole('link', { name: /BG-0001/ })).toHaveAttribute('href', '/app/reservas/detalle?id=r1');
  await expect(page.getByRole('link', { name: /BG-0002/ })).toContainText('18 nov, 15:30');
  await expect(page.getByRole('link', { name: /BG-0002/ })).toContainText('Luis Mora');
  await expect(f3(page).getByLabel('Motivo')).toHaveValue('Feriado');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/franjas-cierre-con-reservas-1440.png', fullPage: true });
});

test('cierre: quitar cierre', async ({ page }) => {
  await base(page);
  const borrados = await simular(page, 'DELETE', '/cierres/c1', { status: 204, body: '' });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Quitar cierre del 20 nov' }).click();
  await expect(page.getByText('Cierre quitado.')).toBeVisible();
  expect(borrados).toHaveLength(1);
});

// --- 4. Semana invalida y fallos ---
test('semana invalida en el enlace: usa esta semana y avisa', async ({ page }) => {
  const { vistasDisp } = await base(page);
  await page.goto('/app/franjas?semana=hola');
  await expect(page.getByText('La semana del enlace no es válida. Te mostramos esta semana.')).toBeVisible();
  expect(vistasDisp).toHaveLength(1);
});

test('disponibilidad 422 rango_invalido: mismo aviso', async ({ page }) => {
  await base(page, { disponibilidad: errorApi(422, 'rango_invalido') });
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await expect(page.getByText('La semana del enlace no es válida. Te mostramos esta semana.')).toBeVisible();
});

for (const [nombre, ruta, camino] of [['semana', `/app/franjas?semana=${SEMANA}`, '/salas'], ['parametros', '/app/franjas/parametros', '/parametros']]) {
  for (const f of fallos) {
    test(`${nombre}: respuesta ${f.n} al cargar`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await comoAdministrador(page);
      await simular(page, 'GET', camino, f.r);
      await page.goto(ruta);
      await expect(page.getByRole('main')).toContainText(f.texto);
      if (f.extra) await expect(page.getByRole('main')).toContainText(f.extra);
      if (f.enlace) await expect(page.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1](ruta));
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
      await expect(page.locator('[aria-busy]')).toHaveCount(0);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/franjas-${nombre}-error-${f.n}-1440.png`, fullPage: true });
    });
  }
}

test('semana: carga con aria-busy y Reintentar vuelve a pedir', async ({ page }) => {
  await comoAdministrador(page);
  let n = 0;
  await simular(page, 'GET', '/salas', (r) => (n++ === 0 ? r.fulfill(errorApi(503, 'x')) : r.fulfill(json(200, [SALA]))));
  await simular(page, 'GET', '/disponibilidad', disp());
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('table', { name: 'Franjas publicadas' })).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/app/franjas', '/app/franjas/parametros']) {
    test(`${ruta} explica que hace falta JS`, async ({ page }) => {
      await page.goto(ruta);
      expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-franjas [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await expect(page.getByText('Cargando…')).toBeHidden();
      if (ruta.endsWith('s') || ruta.endsWith('franjas')) await page.screenshot({ path: 'pruebas/capturas/franjas-sin-js-1440.png', fullPage: true });
    });
  }
});

// --- 5. Parametros ---
for (const t of tamanos) {
  test(`parametros: valores actuales y guardado a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoAdministrador(page);
    await simular(page, 'GET', '/parametros', json(200, PARAMETROS));
    const parches = await simular(page, 'PATCH', '/parametros', json(200, { ...PARAMETROS, anticipacion_minima_horas: 3 }));
    await page.goto('/app/franjas/parametros');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/parámetros de reserva/i);
    await expect(page.getByRole('link', { name: 'Volver a franjas' })).toHaveAttribute('href', '/app/franjas');
    await expect(page.getByLabel('Días antes del inicio')).toHaveValue('3');
    await expect(page.getByLabel('Horas desde la solicitud')).toHaveValue('24');
    await expect(page.getByLabel('Anticipación mínima (horas)')).toHaveValue('2');
    await expect(page.getByLabel('Anticipación máxima (semanas)')).toHaveValue('8');
    await expect(page.getByText('Lo más tarde que se puede reservar antes del inicio.')).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/franjas-parametros-${t.nombre}.png`, fullPage: true });
    await page.getByLabel('Anticipación mínima (horas)').fill('3'); // la anticipacion no es sensible: se guarda en un paso
    await page.getByRole('button', { name: 'Guardar parámetros' }).click();
    await expect(page.getByText('Parámetros guardados. La anticipación ya vale en el calendario; los plazos de pago, en las reservas nuevas.')).toBeVisible();
    expect(parches[0].cuerpo).toEqual({ ...PARAMETROS, anticipacion_minima_horas: 3 });
    await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveCount(0);
    await expect(page.getByLabel('Anticipación mínima (horas)')).toHaveValue('3');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('parametros: enteros mayores que 0, con error bajo el campo', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/parametros', json(200, PARAMETROS));
  const parches = await simular(page, 'PATCH', '/parametros', json(200, PARAMETROS));
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Días antes del inicio').fill('0');
  await page.getByLabel('Anticipación máxima (semanas)').fill('2.5');
  await page.getByRole('button', { name: 'Guardar parámetros' }).click();
  await expect(page.getByText('Escribe un número entero mayor que 0.')).toHaveCount(2);
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByLabel('Días antes del inicio')).toHaveAttribute('aria-invalid', 'true');
  expect(parches).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/franjas-parametros-errores-1440.png', fullPage: true });
});

test('parametros: 422 de la API se muestra en el campo', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/parametros', json(200, PARAMETROS));
  await simular(page, 'PATCH', '/parametros', json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'horas_limite_pago' } } }));
  await page.goto('/app/franjas/parametros');
  await page.getByRole('button', { name: 'Guardar parámetros' }).click();
  await expect(page.getByLabel('Horas desde la solicitud')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByText('Escribe un número entero mayor que 0.')).toBeVisible();
});

test('parametros: 403 al guardar sustituye la vista', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/parametros', json(200, PARAMETROS));
  await simular(page, 'PATCH', '/parametros', errorApi(403, 'sin_permiso'));
  await page.goto('/app/franjas/parametros');
  await page.getByRole('button', { name: 'Guardar parámetros' }).click();
  await expect(page.getByRole('main')).toContainText('Esta sección es solo para el Administrador.');
});

// --- Revision visual TAREA-RF04-6 ---
test('B2: en el panel lateral la tabla es tarjeta a 1440 y los botones no se parten', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  const tabla = f3(page).getByRole('table', { name: 'Cierres de la semana' });
  await expect(tabla.getByRole('row').nth(1)).toBeVisible();
  expect(await tabla.getByRole('row').nth(1).evaluate((e) => getComputedStyle(e).display)).toBe('block');
  const quitar = f3(page).getByRole('button', { name: /Quitar cierre/ });
  const altura = await quitar.evaluate((e) => e.getBoundingClientRect().height);
  const linea = await quitar.evaluate((e) => parseFloat(getComputedStyle(e).lineHeight) || 24);
  expect(altura).toBeLessThan(linea * 3); // una o dos lineas, nunca letra a letra
  const motivo = f3(page).getByText('Mantenimiento', { exact: true });
  expect(await motivo.evaluate((e) => { const r = document.createRange(); r.selectNodeContents(e); return r.getClientRects().length; })).toBe(1); // una sola linea, sin partir la palabra
});

test('N10: el boton con aria-disabled se ve deshabilitado', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto(`/app/franjas?semana=${SEMANA}`);
  const b = page.getByRole('button', { name: 'Retirar franja del miércoles 18 de 10:00 a 14:00' });
  await expect(b).toHaveAttribute('aria-disabled', 'true');
  const token = await page.evaluate(() => { const s = Object.assign(document.createElement('div'), { style: 'opacity:var(--efecto-opacidad-capa)' }); document.body.append(s); const o = getComputedStyle(s).opacity; s.remove(); return o; });
  expect(await b.evaluate((e) => getComputedStyle(e).opacity)).toBe(token);
  expect(await b.evaluate((e) => getComputedStyle(e).cursor)).toBe('not-allowed');
});

for (const tm of tamanos) {
  test(`N9: barra de periodo como la del calendario a ${tm.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await base(page);
    await page.goto(`/app/franjas?semana=${SEMANA}`);
    const barra = page.getByRole('navigation', { name: 'Semana' });
    const titulo = page.getByText('SEMANA DEL 16 AL 22 NOV 2026');
    const [ant, hoy, sig] = ['Semana anterior', 'Esta semana', 'Semana siguiente'].map((n) => barra.getByRole('link', { name: n }));
    const [t, a, h, s] = await Promise.all([titulo, ant, hoy, sig].map((l) => l.boundingBox()));
    expect(t.y + t.height).toBeLessThanOrEqual(a.y + 1); // titulo encima
    if (tm.ancho > 1000) {
      expect(a.x).toBeLessThan(h.x);
      expect(h.x).toBeLessThan(s.x);
    }
    const tactil = await page.evaluate(() => { const e = Object.assign(document.createElement('div'), { style: 'block-size:var(--medida-control-tactil)' }); document.body.append(e); const v = e.getBoundingClientRect().height; e.remove(); return v; });
    for (const c of [a, h, s]) expect(c.height).toBeGreaterThanOrEqual(tactil - 0.5);
    await page.screenshot({ path: `pruebas/capturas/franjas-semana-periodo-${tm.nombre}.png`, fullPage: true });
  });
}
