// RF-03 (CA-05, CA-06, CA-08, CA-09) y base de RF-04: calendario semanal y mensual, agenda del personal y navegacion por rol.
// La API se simula con page.route contra el contrato; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const SALA = { id: 'sala-1', nombre: 'La Molina' };
const R1 = '11111111-1111-4111-8111-111111111111';
const t = (dia, hora) => `2026-11-${dia}T${hora}:00-05:00`;
const detalle = { id_reserva: R1, cliente: 'Ana Pérez', servicio: 'Grabación', estado: 'confirmada' };

// Semana del 16 al 22: miercoles 18 10-14 (ocupado 11:00-12:30), jueves 19 10-14 (cierre 12-14), viernes 20 10-12 (reserva propia 10-11).
const disponibilidad = ({ conDetalle = false, propia = false } = {}) => ({
  limites: { desde: t('16', '10:00'), hasta: '2026-12-15T10:00:00-05:00' },
  franjas: [
    { id: 'f1', inicio: t('18', '10:00'), fin: t('18', '14:00') },
    { id: 'f2', inicio: t('19', '10:00'), fin: t('19', '14:00') },
    { id: 'f3', inicio: t('20', '10:00'), fin: t('20', '12:00') },
  ],
  ocupados: [
    { inicio: t('18', '11:00'), fin: t('18', '12:30'), propia: false, ...(conDetalle && { detalle }) },
    { inicio: t('20', '10:00'), fin: t('20', '11:00'), propia, ...(conDetalle && { detalle: { ...detalle, id_reserva: 'r2', cliente: 'Eva Soto', servicio: 'Mezcla', estado: 'pre_reservada' } }) },
  ],
  cierres: [{ id: 'c1', inicio: t('19', '12:00'), fin: t('19', '14:00'), motivo: 'Feriado' }],
  dias: ['16', '17', '18', '19', '20', '21', '22'].map((d) => ({ fecha: `2026-11-${d}`, minutos_libres: { 18: 90, 19: 90, 20: 30 }[d] ?? 0 })),
});
const VACIA = { limites: { desde: t('16', '10:00'), hasta: '2026-12-15T10:00:00-05:00' }, franjas: [], ocupados: [], cierres: [], dias: [] };
const RESERVA = (extra = {}) => ({ id: R1, folio: 'RSV-0012', estado: 'confirmada', inicio: t('18', '11:00'), fin: t('18', '12:00'), sala: 'La Molina', servicio: 'Grabación', cliente: 'Ana Pérez', ...extra });

// Monta la API: `rol` null = visitante (sin sesion). Devuelve las peticiones a /disponibilidad.
async function montar(page, { rol = null, disp = disponibilidad({ conDetalle: rol === 'personal' || rol === 'administrador' }), salas = [SALA], mias = [], reservas = [], retraso = 0 } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  if (rol) await conSesion(page);
  await silenciarApi(page);
  const vistas = [];
  if (rol) await page.route(`${API}/perfil`, async (r) => { await new Promise((x) => setTimeout(x, retraso)); await r.fulfill(perfil({ rol })); });
  await page.route(`${API}/salas`, (r) => r.fulfill(typeof salas === 'function' ? salas() : json(200, salas)));
  await page.route(`${API}/disponibilidad?**`, (r) => {
    vistas.push(new URL(r.request().url()).searchParams);
    return typeof disp === 'function' ? disp(r) : r.fulfill(json(200, disp));
  });
  await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, mias)));
  await page.route(`${API}/reservas?**`, (r) => {
    vistas.push(new URL(r.request().url()).searchParams);
    return r.fulfill(typeof reservas === 'function' ? reservas() : json(200, reservas));
  });
  return vistas;
}

const SEMANA = '/reservar/?fecha=2026-11-16';
const libre = (page, dia, hora) => page.getByRole('button', { name: `${dia}, ${hora}, libre` });
const anuncio = (page) => page.locator('bugalu-calendario [data-anuncio]');
// Los textos de estado: dentro del calendario (el anuncio oculto repite el aviso).
const ver = (page, texto, op) => page.locator('bugalu-calendario [data-salida], bugalu-calendario [data-avisos]').getByText(texto, op);
const titulo = (page) => page.locator('bugalu-calendario h2').first();

// --- 1. Semana, modo reserva ---

for (const tm of tamanos) {
  test(`semana (reserva): estados con texto y horas libres, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    const vistas = await montar(page, { rol: 'cliente', disp: disponibilidad({ propia: true }), mias: [RESERVA({ id: R1, folio: 'RSV-0012', inicio: t('20', '10:00'), fin: t('20', '10:30') })] });
    await page.goto(SEMANA);
    await expect(titulo(page)).toHaveText(/semana del 16 al 22 nov 2026/i);
    await expect(ver(page, 'Horario de Lima')).toBeVisible();
    await expect(ver(page, 'SALA · LA MOLINA', { exact: false }).first()).toBeVisible();
    expect(vistas[0].get('sala')).toBe('sala-1');
    expect(vistas[0].get('desde')).toBe('2026-11-16T00:00:00-05:00');
    expect(vistas[0].get('hasta')).toBe('2026-11-23T00:00:00-05:00');
    await expect(anuncio(page)).toHaveText('Semana del 16 al 22 nov 2026: 3 h 30 min libres.');
    // En movil la semana es una lista de dias: se abre el dia para ver sus bloques.
    if (tm.ancho < 600) await page.getByText('MIÉ 18 NOV · 1 h 30 min libres').click();
    await expect(libre(page, 'miércoles 18 de noviembre', '10:00')).toBeVisible();
    await expect(libre(page, 'miércoles 18 de noviembre', '12:30')).toBeVisible();
    await expect(libre(page, 'miércoles 18 de noviembre', '10:30')).toHaveCount(0); // margen de preparacion
    await expect(libre(page, 'jueves 19 de noviembre', '11:30')).toHaveCount(0);
    if (tm.ancho < 600) for (const d of ['JUE 19 NOV', 'VIE 20 NOV']) await page.getByText(new RegExp(`^${d}`)).click();
    const visible = page.locator('bugalu-calendario').getByText(/^(LIBRE|OCUPADO|CERRADO|NO RESERVABLE|TU RESERVA)/);
    const textos = (await visible.allTextContents()).map((x) => x.trim());
    for (const estado of ['LIBRE', 'OCUPADO', 'CERRADO', 'NO RESERVABLE', 'TU RESERVA']) expect(textos.some((x) => x.startsWith(estado)), estado).toBe(true);
    await expect(ver(page, 'Feriado').filter({ visible: true }).first()).toBeVisible();
    await expect(ver(page, 'RSV-0012').filter({ visible: true }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /tu reserva RSV-0012/ })).toHaveAttribute('href', `/app/reservas/detalle?id=${R1}`);
    if (tm.ancho > 600) {
      await expect(page.getByRole('columnheader', { name: /MIÉ 18/ })).toContainText('1 h 30 min libres');
      await expect(page.getByRole('columnheader', { name: /LUN 16/ })).toContainText('Sin horas libres');
    } else {
      await expect(ver(page, 'MIÉ 18 NOV · 1 h 30 min libres')).toBeVisible();
    }
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/calendario-semana-${tm.nombre}.png`, fullPage: true });
  });
}

test('semana (reserva): elegir un inicio emite el evento, anuncia y marca aria-pressed', async ({ page }) => {
  await montar(page);
  await page.goto(`${SEMANA}&duracion=60`);
  await page.evaluate(() => document.querySelector('bugalu-calendario').addEventListener('calendario-inicio', (e) => (window.__ev = e.detail)));
  await libre(page, 'miércoles 18 de noviembre', '12:30').click();
  expect(await page.evaluate(() => window.__ev)).toEqual({ inicio: '2026-11-18T12:30:00-05:00', minutosMaximos: 60 });
  await expect(anuncio(page)).toHaveText('Inicio: miércoles 18 nov, 12:30. Hasta 1 h disponibles.');
  await expect(page.getByRole('button', { name: 'miércoles 18 de noviembre, 12:30, libre' })).toHaveAttribute('aria-pressed', 'true');
  await expect(ver(page, 'INICIO', { exact: true })).toBeVisible();
  await libre(page, 'miércoles 18 de noviembre', '10:00').click();
  expect((await page.evaluate(() => window.__ev)).minutosMaximos).toBe(30);
  await expect(libre(page, 'miércoles 18 de noviembre', '12:30')).toHaveAttribute('aria-pressed', 'false');
});

test('semana (reserva): axe con un inicio seleccionado, en escritorio y movil', async ({ page }) => {
  for (const tm of tamanos) {
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montar(page);
    await page.goto(`${SEMANA}&inicio=${encodeURIComponent('2026-11-19T10:00:00-05:00')}&duracion=60`);
    if (tm.ancho < 600) await page.getByText('JUE 19 NOV · 1 h 30 min libres').click();
    await expect(page.locator('bugalu-calendario button[data-inicio][aria-pressed="true"]').locator('visible=true').first()).toBeVisible();
    await sinViolaciones(page);
  }
});

test('semana (reserva): inicio y duracion de la URL restauran la seleccion', async ({ page }) => {
  await montar(page);
  await page.goto(`${SEMANA}&inicio=${encodeURIComponent('2026-11-19T10:00:00-05:00')}&duracion=60`);
  await expect(page.getByRole('button', { name: 'jueves 19 de noviembre, 10:00, libre' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'jueves 19 de noviembre, 10:30, en tu selección' })).toBeVisible();
  await expect(ver(page, 'TU SELECCIÓN')).toBeVisible();
});

test('semana (reserva): los datos de otras personas no se pintan aunque lleguen', async ({ page }) => {
  await montar(page, { disp: disponibilidad({ conDetalle: true }) });
  await page.goto(SEMANA);
  await expect(ver(page, 'OCUPADO').first()).toBeVisible();
  await expect(ver(page, 'Ana Pérez')).toHaveCount(0);
  await expect(ver(page, 'Grabación')).toHaveCount(0);
});

test('periodo pasado: sus horas se marcan PASADO con texto', async ({ page }) => {
  const pasado = { ...VACIA, franjas: [{ id: 'f0', inicio: t('09', '10:00'), fin: t('09', '12:00') }], dias: [{ fecha: '2026-11-09', minutos_libres: 0 }] };
  await montar(page, { disp: pasado });
  await page.goto('/reservar/?fecha=2026-11-09');
  await expect(ver(page, 'PASADO').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /libre/ })).toHaveCount(0);
});

// --- 2. Teclado ---

test('semana (reserva): foco itinerante con flechas, Inicio, Fin y cambio de semana con RePag/AvPag', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Las otras semanas traen una sola franja futura (lunes 10:00-12:00).
  const otra = (desde) => ({ ...VACIA, franjas: [{ id: 'fx', inicio: `${desde.slice(0, 10)}T10:00:00-05:00`, fin: `${desde.slice(0, 10)}T12:00:00-05:00` }], dias: [] });
  await montar(page, { disp: (r) => { const desde = new URL(r.request().url()).searchParams.get('desde'); return r.fulfill(json(200, desde.startsWith('2026-11-16') ? disponibilidad() : otra(desde))); } });
  await page.goto(SEMANA);
  const p10 = libre(page, 'miércoles 18 de noviembre', '10:00');
  await expect(p10).toHaveAttribute('tabindex', '0');
  await expect(page.locator('bugalu-calendario [role="grid"] [tabindex="0"]')).toHaveCount(1);
  await p10.focus();
  await page.keyboard.press('ArrowDown');
  await expect(libre(page, 'miércoles 18 de noviembre', '12:30')).toBeFocused();
  await page.keyboard.press('End');
  await expect(libre(page, 'miércoles 18 de noviembre', '13:00')).toBeFocused();
  await page.keyboard.press('ArrowRight'); // la hora mas cercana del dia vecino
  await expect(libre(page, 'jueves 19 de noviembre', '11:00')).toBeFocused();
  await page.keyboard.press('Home');
  await expect(libre(page, 'jueves 19 de noviembre', '10:00')).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(p10).toBeFocused();
  await page.keyboard.press('ArrowUp'); // ya es la primera: se queda
  await expect(p10).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(p10).toHaveAttribute('aria-pressed', 'true');
  await page.keyboard.press('PageDown');
  await expect(titulo(page)).toHaveText(/semana del 23 al 29 nov 2026/i);
  await expect(page).toHaveURL(/fecha=2026-11-23/);
  await expect(page.getByRole('button', { name: 'lunes 23 de noviembre, 10:00, libre' })).toBeFocused(); // el foco sigue en la cuadricula
  await page.keyboard.press('PageUp');
  await expect(titulo(page)).toHaveText(/semana del 16 al 22 nov 2026/i);
});

test('periodo: Anterior, Hoy y Siguiente son enlaces que cambian la semana sin recargar y conservan el foco', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await montar(page);
  await page.goto(SEMANA);
  const siguiente = page.getByRole('link', { name: 'Semana siguiente' });
  await expect(siguiente).toHaveAttribute('href', /vista=semana&fecha=2026-11-23/);
  await siguiente.focus();
  await siguiente.click();
  await expect(titulo(page)).toHaveText(/semana del 23 al 29 nov 2026/i);
  await expect(page.getByRole('link', { name: 'Semana siguiente' })).toBeFocused();
  await expect(anuncio(page)).toContainText('Semana del 23 al 29 nov 2026');
  await page.getByRole('link', { name: 'Esta semana' }).click();
  await expect(titulo(page)).toHaveText(/semana del 9 al 15 nov 2026/i);
  await page.goBack();
  await expect(titulo(page)).toHaveText(/semana del 23 al 29 nov 2026/i);
});

// --- 3. Mes ---

for (const tm of tamanos) {
  test(`mes: cada dia dice sus horas libres y abre su semana, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    const vistas = await montar(page);
    await page.goto('/reservar/?vista=mes&fecha=2026-11-18');
    await expect(titulo(page)).toHaveText(/noviembre 2026/i);
    expect(vistas[0].get('desde')).toBe('2026-10-26T00:00:00-05:00');
    expect(vistas[0].get('hasta')).toBe('2026-12-07T00:00:00-05:00');
    await expect(page.locator('bugalu-calendario [role="grid"] a')).toHaveCount(42);
    const dia = page.getByRole('link', { name: /miércoles 18 de noviembre, 1 h 30 min libres ?, abrir semana/i });
    await expect(dia).toHaveAttribute('href', /vista=semana&fecha=2026-11-18/);
    await expect(page.getByRole('link', { name: /lunes 16 de noviembre, sin horario ?, abrir semana/i })).toBeVisible();
    await expect(anuncio(page)).toHaveText('Noviembre 2026: 3 h 30 min libres.');
    await expect(page.locator('bugalu-calendario [role="grid"] [tabindex="0"]')).toHaveCount(1);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/calendario-mes-${tm.nombre}.png`, fullPage: true });
    await dia.click();
    await expect(titulo(page)).toHaveText(/semana del 16 al 22 nov 2026/i);
    await expect(page).toHaveURL(/vista=semana&fecha=2026-11-18/);
  });
}

test('mes: el cierre de todo el dia dice Cerrado y el teclado recorre dias y meses', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const disp = { ...disponibilidad(), franjas: [{ id: 'f2', inicio: t('19', '10:00'), fin: t('19', '14:00') }], cierres: [{ id: 'c1', inicio: t('19', '09:00'), fin: t('19', '15:00'), motivo: 'Feriado' }], ocupados: [] };
  await montar(page, { disp });
  await page.goto('/reservar/?vista=mes&fecha=2026-11-18');
  await expect(page.getByRole('link', { name: /jueves 19 de noviembre, cerrado ?, abrir semana/i })).toBeVisible();
  const hoy = page.getByRole('link', { name: /domingo 15 de noviembre/ });
  await expect(hoy).toHaveAttribute('aria-current', 'date');
  const primero = page.locator('bugalu-calendario [role="grid"] [tabindex="0"]');
  await primero.focus();
  const nombre = () => primero.evaluate((e) => document.activeElement.dataset.fecha);
  await page.keyboard.press('ArrowRight');
  expect(await nombre()).toBe('2026-11-19');
  await page.keyboard.press('ArrowDown');
  expect(await nombre()).toBe('2026-11-26');
  await page.keyboard.press('PageDown');
  await expect(titulo(page)).toHaveText(/diciembre 2026/i);
});

// --- 4. Modo personal ---

for (const tm of tamanos) {
  test(`agenda (personal): cliente, servicio y estado de cada reserva, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montar(page, { rol: 'personal' });
    await page.goto('/app/agenda/?vista=semana&fecha=2026-11-16');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/agenda de sala/i);
    await expect(page.locator('.encabezado')).toContainText('[R1] SALA / AGENDA');
    await expect(titulo(page)).toHaveText(/semana del 16 al 22 nov 2026/i);
    const enlace = page.getByRole('link', { name: /Ana Pérez/ });
    await expect(enlace).toHaveAttribute('href', `/app/reservas/detalle?id=${R1}`);
    await expect(enlace).toContainText('Grabación');
    await expect(enlace).toContainText('Confirmada');
    await expect(page.getByRole('link', { name: /Eva Soto/ })).toContainText('Pre-reservada');
    // Sin foco itinerante: los enlaces siguen el Tab.
    await expect(page.locator('bugalu-calendario [role="grid"]')).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Lista' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/calendario-agenda-${tm.nombre}.png`, fullPage: true });
  });
}

test('agenda (personal): la vista Lista trae las reservas del periodo en una tabla', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const vistas = await montar(page, { rol: 'personal', reservas: [RESERVA(), RESERVA({ id: 'r2', folio: 'RSV-0013', cliente: 'Eva Soto', servicio: 'Mezcla', estado: 'pre_reservada', inicio: t('20', '10:00'), fin: t('20', '12:00') })] });
  await page.goto('/app/agenda/?vista=lista&fecha=2026-11-16');
  await expect(page.getByRole('table')).toBeVisible();
  const lista = vistas.find((v) => !v.has('sala'));
  expect(lista.get('desde')).toBe('2026-11-16T00:00:00-05:00');
  expect(lista.get('hasta')).toBe('2026-11-23T00:00:00-05:00');
  await expect(page.getByRole('row')).toHaveCount(3);
  await expect(page.getByRole('row').nth(1)).toContainText('RSV-0012');
  await expect(page.getByRole('row').nth(1)).toContainText('18 nov, 11:00–12:00');
  await expect(page.getByRole('row').nth(1)).toContainText('Ana Pérez');
  await expect(page.getByRole('link', { name: 'Ver reserva RSV-0013' })).toHaveAttribute('href', '/app/reservas/detalle?id=r2');
  await expect(anuncio(page)).toHaveText('2 reservas en este periodo.');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/calendario-lista-escritorio.png', fullPage: true });
});

test('agenda (personal): Lista sin reservas', async ({ page }) => {
  await montar(page, { rol: 'personal', reservas: [] });
  await page.goto('/app/agenda/?vista=lista&fecha=2026-11-16');
  await expect(ver(page, 'No hay reservas en este periodo.')).toBeVisible();
});

test('agenda: en movil, sin vista en la URL abre Lista', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await montar(page, { rol: 'personal', reservas: [RESERVA()] });
  await page.goto('/app/agenda/?fecha=2026-11-16');
  await expect(page.getByRole('link', { name: 'Ver reserva RSV-0012' })).toBeVisible();
});

// --- 5. Estados ---

const caidas = [
  ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El calendario no responde. Inténtalo de nuevo en unos minutos.'],
  ['red caida', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.'],
  ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<html>proxy</html>' }), 'Algo salió mal al cargar el calendario.'],
];
for (const [nombre, respuesta, texto] of caidas) {
  test(`error ${nombre}: aviso con Reintentar y foco al titulo`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = true;
    await montar(page, { disp: (r) => (falla ? respuesta(r) : r.fulfill(json(200, disponibilidad()))) });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(SEMANA);
    await expect(ver(page, texto)).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/calendario-error-${nombre.replace(' ', '-')}.png` });
    falla = false;
    await page.getByRole('button', { name: 'Reintentar' }).click();
    await expect(libre(page, 'miércoles 18 de noviembre', '10:00')).toBeVisible();
    await expect(titulo(page)).toBeFocused();
    expect(consola.filter((x) => !/Failed to load resource|ERR_/.test(x))).toEqual([]);
  });
}

test('error de salas: tambien muestra el aviso con Reintentar', async ({ page }) => {
  await montar(page, { salas: () => errorApi(503, 'x') });
  await page.goto(SEMANA);
  await expect(ver(page, 'El calendario no responde.')).toBeVisible();
});

test('401 en la agenda: sesion no valida con enlace al acceso interno', async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  await silenciarApi(page);
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [SALA])));
  await page.goto('/app/agenda/?fecha=2026-11-16');
  await expect(ver(page, 'Tu sesión no es válida')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ir al acceso interno' })).toHaveAttribute('href', /^\/acceso\/interno\?volver=%2Fapp%2Fagenda%2F/);
  await sinViolaciones(page);
});

test('401 en /reservar: aviso de sesion caducada con enlace para iniciar sesion', async ({ page }) => {
  await montar(page, { rol: 'cliente', disp: (r) => r.fulfill(errorApi(401, 'no_autenticado')) });
  await page.goto(SEMANA);
  await expect(ver(page, 'Tu sesión caducó. Inicia sesión para ver tus reservas en el calendario.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Iniciar sesión' })).toHaveAttribute('href', /^\/acceso\?volver=/);
});

test('403: un cliente en la agenda ve SIN PERMISO y no se piden datos', async ({ page }) => {
  const vistas = await montar(page, { rol: 'cliente' });
  await page.goto('/app/agenda/?fecha=2026-11-16');
  await expect(ver(page, 'La agenda es solo para el equipo del estudio.')).toBeVisible();
  await expect(page.getByRole('heading', { name: /sin permiso/i })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/app/');
  expect(vistas).toEqual([]);
  await sinViolaciones(page);
});

test('403 de la API en Lista: SIN PERMISO', async ({ page }) => {
  await montar(page, { rol: 'personal', reservas: () => errorApi(403, 'prohibido') });
  await page.goto('/app/agenda/?vista=lista&fecha=2026-11-16');
  await expect(ver(page, 'La agenda es solo para el equipo del estudio.')).toBeVisible();
});

test('404 de la sala: aviso con enlace a la sala de La Molina', async ({ page }) => {
  await montar(page, { disp: (r) => r.fulfill(errorApi(404, 'sala_no_encontrada')), salas: [SALA, { id: 'sala-2', nombre: 'Cabina' }] });
  await page.goto('/reservar/?sala=otra&fecha=2026-11-16');
  await expect(ver(page, 'No encontramos esa sala.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver la sala de La Molina' })).toHaveAttribute('href', /^\/reservar\/(\?(?!.*sala=).*)?$/);
});

test('fecha invalida: muestra la semana actual con un aviso', async ({ page }) => {
  await montar(page);
  await page.goto('/reservar/?fecha=basura');
  await expect(ver(page, 'La fecha del enlace no es válida. Te mostramos esta semana.')).toBeVisible();
  await expect(titulo(page)).toHaveText(/semana del 9 al 15 nov 2026/i);
});

test('vacio: sin franjas publicadas ofrece ver la semana siguiente', async ({ page }) => {
  await montar(page, { disp: VACIA });
  await page.goto(SEMANA);
  await expect(ver(page, 'Aún no hay horarios publicados')).toBeVisible();
  await expect(ver(page, 'Publicamos la agenda semana a semana. Mira la siguiente semana o vuelve pronto.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver semana siguiente' })).toHaveAttribute('href', /fecha=2026-11-23/);
  await expect(page.getByRole('link', { name: 'Publicar franjas de esta semana' })).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/calendario-vacio.png' });
});

test('vacio: el Administrador ademas puede publicar las franjas de la semana', async ({ page }) => {
  await montar(page, { rol: 'administrador', disp: VACIA });
  await page.goto('/app/agenda/?fecha=2026-11-16');
  await expect(page.getByRole('link', { name: 'Publicar franjas de esta semana' })).toHaveAttribute('href', '/app/franjas/?semana=2026-W47');
});

test('carga: aria-busy y texto Cargando semana…', async ({ page }) => {
  await montar(page, { disp: async (r) => { await new Promise((x) => setTimeout(x, 600)); await r.fulfill(json(200, disponibilidad())); } });
  await page.goto(SEMANA);
  await expect(ver(page, 'Cargando semana…')).toBeVisible();
  await expect(page.locator('bugalu-calendario [aria-busy="true"]')).toHaveCount(1);
  await expect(libre(page, 'miércoles 18 de noviembre', '10:00')).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/reservar/', '/app/agenda/']) {
    test(`${ruta}: noscript explica que hace falta JS`, async ({ page }) => {
      await page.goto(ruta);
      // Playwright ignora el texto de <noscript>: se comprueba en el HTML y en lo que se ve.
      expect(await page.content()).toContain('El calendario necesita JavaScript. Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-calendario [data-salida]')).toBeHidden();
      await expect(page.locator('bugalu-calendario noscript .aviso-titulo')).toBeVisible();
      await page.screenshot({ path: `pruebas/capturas/calendario-sin-js-${ruta.includes('agenda') ? 'agenda' : 'reservar'}.png`, fullPage: true });
    });
  }
});

// --- 6. Zoom 200 % ---

for (const vista of ['semana', 'mes']) {
  test(`zoom 200 %: la vista ${vista} no desborda ni corta`, async ({ page }) => {
    await page.setViewportSize({ width: 720, height: 450 }); // 1440 px a 200 %
    await montar(page);
    await page.goto(`/reservar/?vista=${vista}&fecha=2026-11-18`);
    await expect(titulo(page)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await sinViolaciones(page);
  });
}

// --- 7. Navegacion por rol ---

test.describe('navegacion por rol', () => {
  const visibles = (page) => page.locator('.lateral-destino:visible, .tactil-destino:visible').locator('.lateral-etiqueta, .tactil-etiqueta').allTextContents();

  test('cliente: RESERVAS; sin AGENDA', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await montar(page, { rol: 'cliente' });
    await page.goto('/app/');
    await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Reservas' })).toHaveAttribute('href', '/app/reservas/');
    expect(await visibles(page)).toEqual(['Inicio', 'Reservas']);
  });

  test('personal: AGENDA con enlace y actual en /app/agenda/', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await montar(page, { rol: 'personal' });
    await page.goto('/app/agenda/?fecha=2026-11-16');
    await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Agenda' })).toHaveAttribute('aria-current', 'page');
    expect(await visibles(page)).toEqual(['Inicio', 'Agenda']);
  });

  test('administrador (escritorio): Agenda, Accesos, Usuarios, Franjas y Tarifas', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await montar(page, { rol: 'administrador' });
    await page.goto('/app/');
    await expect(page.locator('.lateral-destino:visible')).toHaveCount(6);
    expect(await visibles(page)).toEqual(['Inicio', 'Agenda', 'Accesos', 'Usuarios', 'Franjas', 'Tarifas']);
    const nav = page.getByRole('navigation', { name: 'Principal' });
    await expect(nav.getByRole('link', { name: 'Franjas' })).toHaveAttribute('href', '/app/franjas/');
    await expect(nav.getByRole('link', { name: 'Tarifas' })).toHaveAttribute('href', '/app/tarifas/');
    for (const e of await visibles(page)) expect(e.trim().length).toBeLessThanOrEqual(9);
  });

  test('administrador (movil): cinco destinos en la barra y Tarifas en el menu', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await montar(page, { rol: 'administrador' });
    await page.goto('/app/');
    await expect(page.locator('.tactil-destino:visible')).toHaveCount(5);
    expect(await visibles(page)).toEqual(['Inicio', 'Agenda', 'Accesos', 'Usuarios', 'Franjas']);
    await page.getByText('Menú', { exact: true }).click();
    await expect(page.locator('.cabecera-menu-panel').getByRole('link', { name: 'Tarifas' })).toHaveAttribute('href', '/app/tarifas/');
    await sinViolaciones(page);
  });

  test('estado neutro: mientras llega el rol solo se pinta Inicio', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await montar(page, { rol: 'administrador', retraso: 800 });
    await page.goto('/app/');
    expect(await visibles(page)).toEqual(['Inicio']);
    await expect(page.locator('.lateral-destino:visible')).toHaveCount(6);
  });
});

// --- Revision visual TAREA-RF04-6, B1: lo que va dentro de la celda ocupada lleva fondo opaco, nunca sobre las rayas ---
for (const [modo, rol, selector] of [['reserva', null, '.cal-celda[data-estado="ocupado"] > .etiqueta'], ['personal', 'personal', '.cal-celda[data-estado="ocupado"] > .cal-enlace']]) {
  test(`ocupado (${modo}): el texto va sobre fondo opaco de color-fondo-superficie con relleno espacio-1`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await montar(page, { rol });
    await page.goto(rol ? '/app/agenda/?vista=semana&fecha=2026-11-16' : SEMANA);
    const interior = page.locator(`bugalu-calendario ${selector}`).first();
    await expect(interior).toBeVisible();
    const esperado = await page.evaluate(() => {
      const s = Object.assign(document.createElement('div'), { style: 'background:var(--color-fondo-superficie);padding:var(--espacio-1)' });
      document.body.append(s);
      const c = getComputedStyle(s);
      const r = { fondo: c.backgroundColor, relleno: c.paddingTop };
      s.remove();
      return r;
    });
    const real = await interior.evaluate((e) => ({ fondo: getComputedStyle(e).backgroundColor, relleno: getComputedStyle(e).paddingTop }));
    expect(real).toEqual(esperado);
  });
}
