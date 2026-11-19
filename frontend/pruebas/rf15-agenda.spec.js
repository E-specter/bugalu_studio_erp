// RF-15 etapa B: asesorias agendadas del profesional y del Administrador (spec RF-15-agenda). La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { json, errorApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { AID, PID, PID2, PROF, PROF2, comoCliente, filaAgenda } from './ayudas-rf15b.js';

const RUTA = '/app/asesorias/agenda';
const sinDesborde = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const lista = [
  filaAgenda(),
  filaAgenda({ id: 'x2', folio: 'A-2026-00002', estado: 'confirmada', inicio: '2026-12-01T10:00:00-05:00', fin: '2026-12-01T10:30:00-05:00', modalidad: 'presencial', encuentro_pendiente: false, vence_pago: undefined, cliente: { id: 'c2', nombre: 'Rosa Díaz', telefono: '999', correo: 'rosa@correo.com' } }),
];
const POR_CERRAR = [filaAgenda({ id: 'x3', folio: 'A-2026-00003', estado: 'confirmada', inicio: '2026-11-10T10:00:00-05:00', fin: '2026-11-10T11:00:00-05:00', por_cerrar: true, encuentro_pendiente: false })];
// Responde segun los parametros: por_cerrar, o el resto (proximas / historial).
const api = (page, { normales = lista, cerrar = POR_CERRAR } = {}) =>
  simular(page, 'GET', '/asesorias', (r) => {
    const q = new URL(r.request().url()).searchParams;
    return r.fulfill(json(200, q.get('por_cerrar') === 'true' ? cerrar : normales));
  });

for (const t of tamanos) {
  test(`agenda del profesional: proximas, aviso por cerrar y sin columna de profesional a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page, 'profesional');
    const vistas = await api(page);
    await page.goto(RUTA);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mis asesorías');
    await expect(page.locator('[data-salida] tbody tr')).toHaveCount(2);
    // Por fecha ascendente: la del 1 dic va antes que la del 18 dic.
    await expect(page.locator('[data-salida] tbody tr').first()).toContainText('A-2026-00002');
    const primera = page.locator('[data-salida] tbody tr').nth(1);
    await expect(primera).toContainText('A-2026-00001');
    await expect(primera).toContainText('Lu Beats');
    await expect(primera).toContainText('18 dic 2026');
    await expect(primera).toContainText('15:00–16:00');
    await expect(primera).toContainText('Pendiente de pago');
    await expect(page.locator('[data-salida] [data-profesional]')).toHaveCount(0);
    await expect(page.locator('[data-salida] th', { hasText: 'Profesional' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: /Ver asesoría A-2026-00001/ })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
    await expect(page.locator('[role="status"][data-anuncio]')).toHaveText('2 asesorías próximas');
    await expect(page.getByRole('link', { name: 'Próximas' })).toHaveAttribute('aria-current', 'true');
    await expect(page.getByRole('link', { name: 'Por cerrar (1)' })).toHaveAttribute('href', `${RUTA}?ver=por_cerrar`);
    await expect(page.getByText('Tienes 1 asesoría por cerrar. Marca si se realizaron o si el cliente no asistió.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver por cerrar' })).toBeVisible();
    await expect(page.locator('#agenda-profesional')).toBeHidden();
    await expect(page.getByRole('link', { name: 'Asesorías' }).first()).toHaveAttribute('aria-current', 'page');
    const proximas = vistas.find((v) => !v.url.searchParams.has('por_cerrar'));
    expect(proximas.url.searchParams.get('desde')).toBe('2026-11-15T15:00:00.000Z');
    expect(proximas.url.searchParams.has('id_profesional')).toBe(false);
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-agenda-profesional-${t.nombre}.png`, fullPage: true });
  });
}

test('agenda del Administrador: encabezado, selector de profesional y columna PROFESIONAL', async ({ page }) => {
  const consola = vigilarConsola(page);
  await comoCliente(page, 'administrador');
  await simular(page, 'GET', '/profesionales', json(200, [PROF, PROF2]));
  const vistas = await api(page);
  await page.goto(RUTA);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Asesorías agendadas');
  await expect(page.locator('.encabezado-indice')).toHaveText('[A15] ASESORÍAS / AGENDA');
  await expect(page.locator('.encabezado-ruta a', { hasText: 'Asesorías' })).toHaveAttribute('href', '/app/asesorias/');
  await expect(page.locator('.encabezado-ruta [aria-current="page"]')).toHaveText('Agendadas');
  await expect(page.getByRole('link', { name: 'Volver a profesionales' })).toHaveAttribute('href', '/app/asesorias/');
  await expect(page.locator('[data-salida] th', { hasText: 'Profesional' })).toHaveCount(1);
  await expect(page.locator('[data-salida] tbody tr').first()).toContainText('Ana Beat');
  await expect(page.getByText('Hay 1 asesoría por cerrar.')).toBeVisible();
  await expect(page.getByLabel('Profesional')).toHaveValue('');
  await expect(page.getByLabel('Profesional').locator('option')).toHaveText(['Todos', 'Ana Beat', 'Carla Ruiz']);
  await sinViolaciones(page);
  // Elegir un profesional navega con ?profesional= y la API recibe id_profesional.
  await page.getByLabel('Profesional').selectOption(PID2);
  await page.getByRole('button', { name: 'Filtrar' }).click();
  await expect(page).toHaveURL(new RegExp(`profesional=${PID2}`));
  await expect(page.getByLabel('Profesional')).toHaveValue(PID2);
  expect(vistas.at(-1).url.searchParams.get('id_profesional')).toBe(PID2);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/rf15-agenda-admin.png', fullPage: true });
});

test('agenda: POR CERRAR lleva a cerrar y mantiene el profesional elegido', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await simular(page, 'GET', '/profesionales', json(200, [PROF, PROF2]));
  const vistas = await api(page);
  await page.goto(`${RUTA}?ver=por_cerrar&profesional=${PID}`);
  await expect(page.getByRole('link', { name: 'Por cerrar (1)' })).toHaveAttribute('aria-current', 'true');
  await expect(page.getByRole('link', { name: /Ver asesoría A-2026-00003/ })).toHaveAttribute('href', '/app/asesorias/detalle?id=x3'); // Cerrar llega con la etapa C
  await expect(page.locator('[data-salida] tbody').getByText('Por cerrar', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Próximas' })).toHaveAttribute('href', `${RUTA}?profesional=${PID}`);
  expect(vistas[0].url.searchParams.get('por_cerrar')).toBe('true');
  expect(vistas[0].url.searchParams.get('id_profesional')).toBe(PID);
  await sinViolaciones(page);
});

test('agenda: HISTORIAL por mes filtra los estados cerrados y navega entre meses', async ({ page }) => {
  await comoCliente(page, 'profesional');
  const mes = [
    filaAgenda({ id: 'h1', folio: 'A-2026-00010', estado: 'realizada', inicio: '2026-11-03T10:00:00-05:00', fin: '2026-11-03T11:00:00-05:00' }),
    filaAgenda({ id: 'h2', folio: 'A-2026-00011', estado: 'cancelada', inicio: '2026-11-09T10:00:00-05:00', fin: '2026-11-09T11:00:00-05:00' }),
    filaAgenda({ id: 'h3', folio: 'A-2026-00012', estado: 'confirmada', inicio: '2026-11-30T10:00:00-05:00', fin: '2026-11-30T11:00:00-05:00' }),
  ];
  const vistas = await api(page, { normales: mes });
  await page.goto(`${RUTA}?ver=historial`);
  await expect(page.locator('[data-titulo-mes]')).toHaveText('noviembre 2026');
  // Solo realizada y cancelada; la más reciente primero.
  await expect(page.locator('[data-salida] tbody tr')).toHaveCount(2);
  await expect(page.locator('[data-salida] tbody tr').first()).toContainText('A-2026-00011');
  await expect(page.locator('[data-salida] tbody tr').first()).toContainText('Cancelada');
  await expect(page.locator('[data-salida] tbody tr').nth(1)).toContainText('Realizada');
  await expect(page.locator('[role="status"][data-anuncio]')).toHaveText('2 asesorías en noviembre 2026');
  const q = vistas.find((v) => v.url.searchParams.has('hasta')).url.searchParams;
  expect(q.get('desde')).toBe('2026-11-01T00:00:00-05:00');
  expect(q.get('hasta')).toBe('2026-11-30T23:59:59-05:00');
  await expect(page.getByRole('link', { name: 'Mes anterior' })).toHaveAttribute('href', `${RUTA}?ver=historial&mes=2026-10`);
  await expect(page.getByRole('link', { name: 'Mes siguiente' })).toHaveAttribute('href', `${RUTA}?ver=historial&mes=2026-12`);
  await sinViolaciones(page);
  // Mes sin asesorías: vacío con "Mes anterior".
  await api(page, { normales: [] });
  await page.goto(`${RUTA}?ver=historial&mes=2026-10`);
  await expect(page.locator('[data-vacio-titulo]')).toHaveText('No hay asesorías en octubre 2026.');
  await expect(page.locator('[data-vacio-accion] a')).toHaveAttribute('href', `${RUTA}?ver=historial&mes=2026-09`);
});

test('agenda: vacios del profesional, del Administrador y con profesional elegido', async ({ page }) => {
  await comoCliente(page, 'profesional');
  await api(page, { normales: [], cerrar: [] });
  await page.goto(RUTA);
  await expect(page.locator('[data-vacio-titulo]')).toHaveText('Aún no tienes asesorías agendadas');
  await expect(page.getByText('Cuando un artista agende en tus horarios, la verás aquí.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Mis horarios' })).toHaveAttribute('href', '/app/horarios/');
  await expect(page.getByRole('link', { name: /^Por cerrar/ })).toHaveText('Por cerrar (0)');
  await sinViolaciones(page);
  await page.goto(`${RUTA}?ver=por_cerrar`);
  await expect(page.locator('[data-vacio-titulo]')).toHaveText('No tienes asesorías por cerrar.');
  await expect(page.locator('[data-vacio-accion]')).toBeHidden();
});

test('agenda del Administrador: vacio general y con un profesional elegido', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await simular(page, 'GET', '/profesionales', json(200, [PROF, PROF2]));
  await api(page, { normales: [], cerrar: [] });
  await page.goto(RUTA);
  await expect(page.locator('[data-vacio-titulo]')).toHaveText('Aún no hay asesorías agendadas');
  await page.goto(`${RUTA}?profesional=${PID2}`);
  await expect(page.locator('[data-vacio-titulo]')).toHaveText('Carla Ruiz no tiene asesorías próximas.');
  await expect(page.getByRole('link', { name: 'Ver todos' })).toHaveAttribute('href', RUTA);
  await sinViolaciones(page);
});

test('agenda: filtros inválidos o un 422 vuelven a PRÓXIMAS con un aviso', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await simular(page, 'GET', '/profesionales', json(200, [PROF]));
  await api(page);
  for (const consulta of ['ver=x', 'ver=historial&mes=2026-13', 'profesional=no-es-uuid', `profesional=${PID2}`]) {
    await page.goto(`${RUTA}?${consulta}`);
    await expect(page.getByText('El filtro del enlace no es válido. Te mostramos las próximas.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Próximas' })).toHaveAttribute('aria-current', 'true');
    expect(new URL(page.url()).search).toBe('');
  }
  // La API rechaza el rango: se reintenta con los valores por defecto.
  await simular(page, 'GET', '/asesorias', (r) => (new URL(r.request().url()).searchParams.has('hasta') ? r.fulfill(errorApi(422, 'rango_invalido')) : r.fulfill(json(200, lista))));
  await page.goto(`${RUTA}?ver=historial`);
  await expect(page.getByText('El filtro del enlace no es válido. Te mostramos las próximas.')).toBeVisible();
  await expect(page.locator('[data-salida] tbody tr')).toHaveCount(2);
});

const fallos = [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: 'Tu sesión no es válida. Inicia sesión para continuar.', enlace: ['Ir al acceso interno', `/acceso/interno?volver=${encodeURIComponent(RUTA)}`] },
  { n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: 'Esta sección es para profesionales de asesoría y el Administrador.', enlace: ['Volver al inicio', '/app/'] },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];
for (const f of fallos) {
  test(`agenda: ${f.n} muestra su estado sin pantalla en blanco`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoCliente(page, 'profesional');
    await simular(page, 'GET', '/asesorias', f.r);
    await page.goto(RUTA);
    await expect(page.locator('[data-salida]')).toContainText(f.texto);
    if (f.enlace) await expect(page.locator('[data-salida]').getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1]);
    await expect(page.locator('[data-controles]')).toBeHidden();
    if (f.reintentar) {
      await simular(page, 'GET', '/asesorias', json(200, lista));
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.locator('[data-salida] tbody tr')).toHaveCount(2);
    }
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('agenda: un cliente ve SIN PERMISO sin pedir asesorías', async ({ page }) => {
  await comoCliente(page, 'cliente');
  const vistas = await api(page);
  await page.goto(RUTA);
  await expect(page.locator('[data-salida]')).toContainText('[403]');
  await expect(page.locator('[data-salida]')).toContainText('Esta sección es para profesionales de asesoría y el Administrador.');
  expect(vistas).toHaveLength(0);
  await page.screenshot({ path: 'pruebas/capturas/rf15-agenda-403.png', fullPage: true });
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('agenda: el contenido estático avisa de que necesita JavaScript', async ({ page }) => {
    await page.goto(RUTA);
    expect(await page.content()).toContain('Esta sección necesita JavaScript');
    await expect(page.locator('bugalu-agenda [data-salida]')).toBeHidden();
    await expect(page.locator('bugalu-agenda noscript .aviso-titulo')).toBeVisible();
    await expect(page.locator('bugalu-agenda [data-controles]')).toBeHidden();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mis asesorías');
    await expect(page.getByRole('link', { name: 'Volver a profesionales' })).toBeHidden();
  });
});
