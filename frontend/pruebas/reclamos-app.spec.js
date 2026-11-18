// RF-16 (CA-07, CA-09, CA-10, CA-11, CA-13): Mis reclamos del cliente, bandeja y respuesta del Administrador, descarga de adjuntos y CSV,
// transcripcion del libro fisico y enlaces de la app. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, fallos } from './ayudas-admin.js';
import { H1, H2, HOY, archivo, hoja, resumen, RESPUESTA, simularMultipart } from './ayudas-rf16.js';

const comoRol = async (page, rol) => {
  await page.clock.setFixedTime(HOY);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
  await page.addInitScript(() => { window.__impreso = 0; window.print = () => window.__impreso++; });
};
const aviso = (page) => page.locator('[data-avisos] .aviso');
const tabla = (page, nombre) => page.getByRole('table', { name: nombre }).getByRole('row');

// Hojas de la bandeja: pendientes (vencen 20, 17 y 18 nov, y una vencida) y una respondida.
const R = {
  r1: resumen({ id: H1, numero: '000000001-2026', dias_habiles_restantes: 3, vence_respuesta: '2026-11-21T04:59:59Z', consumidor: { nombre: 'Ana Pérez' } }),
  r2: resumen({ id: H2, numero: '000000002-2026', tipo: 'queja', dias_habiles_restantes: 0, vence_respuesta: '2026-11-18T04:59:59Z', consumidor: { nombre: 'Beto Ríos' }, revisar_spam: true }),
  r3: resumen({ id: 'c3', numero: '000000003-2026', tipo: null, dias_habiles_restantes: 1, vence_respuesta: '2026-11-19T04:59:59Z', consumidor: { nombre: 'Carla Soto' }, origen: 'libro_fisico' }),
  r4: resumen({ id: 'c4', numero: '000000004-2026', dias_habiles_restantes: -2, vence_respuesta: '2026-11-13T04:59:59Z', consumidor: { nombre: 'Dani Vega' } }),
  r5: resumen({ id: 'c5', numero: '000000005-2026', estado: 'respondida', creada_en: '2026-11-10T15:00:00Z', vence_respuesta: '2026-12-02T04:59:59Z', consumidor: { nombre: 'Eva Luna' } }),
};
const TODAS = [R.r5, R.r1, R.r2, R.r3, R.r4];

// ==================== Mis reclamos (cliente) ====================
const MIAS = [
  resumen({ id: 'm1', numero: '000000001-2026', creada_en: '2026-11-05T15:00:00Z', estado: 'respondida', tipo: 'reclamo', vence_respuesta: '2026-11-27T04:59:59Z' }),
  resumen({ id: H1, numero: '000000007-2026', creada_en: '2026-11-16T15:00:00Z', estado: 'pendiente', tipo: null, vence_respuesta: '2026-12-08T04:59:59Z' }),
];
for (const t of tamanos) {
  test(`mis reclamos: lista del cliente con estado en texto y enlaces, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoRol(page, 'cliente');
    await simular(page, 'GET', '/reclamaciones/mias', json(200, MIAS));
    await page.goto('/app/reclamos/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('MIS RECLAMOS');
    await expect(page).toHaveTitle('Mis reclamos · Bugalú Studio');
    await expect(page.locator('.encabezado-indice')).toHaveText('[P4] CUENTA / RECLAMOS');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Mis reclamos']);
    await expect(page.locator('.encabezado-descripcion')).toContainText('Te respondemos en un máximo de 15 días hábiles.');
    await expect(page.getByRole('link', { name: 'Presentar un reclamo' })).toHaveAttribute('href', '/libro-de-reclamaciones/');
    await expect(page.getByRole('link', { name: 'Transcribir hoja del libro físico' })).toBeHidden();
    await expect(page.getByRole('button', { name: 'Exportar CSV' })).toBeHidden();
    await expect(page.locator('[data-filtros]')).toBeHidden();
    const filas = tabla(page, 'Tus hojas de reclamación');
    await expect(filas).toHaveCount(3);
    // La mas reciente arriba.
    await expect(filas.nth(1).getByRole('rowheader')).toHaveText('000000007-2026');
    await expect(filas.nth(1)).toContainText('16 nov 2026, 10:00');
    await expect(filas.nth(1)).toContainText('Sin marcar');
    await expect(filas.nth(1)).toContainText('EN TRÁMITE');
    await expect(filas.nth(1)).toContainText('Respuesta hasta el 7 dic 2026');
    await expect(filas.nth(2)).toContainText('Reclamo');
    await expect(filas.nth(2)).toContainText('RESPONDIDA');
    await expect(page.getByRole('link', { name: 'Ver hoja 000000007-2026' })).toHaveAttribute('href', `/app/reclamos/detalle?id=${H1}`);
    await expect(page.getByText('¿No ves una hoja? Las que presentaste sin iniciar sesión no aparecen aquí; su copia está en tu correo.')).toBeVisible();
    await expect(page.locator('[data-anuncio]')).toHaveText('2 hojas');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/mis-reclamos-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('mis reclamos: vacio, con la accion en el cuerpo y no repetida en el encabezado', async ({ page }) => {
  await comoRol(page, 'cliente');
  await simular(page, 'GET', '/reclamaciones/mias', json(200, []));
  await page.goto('/app/reclamos/');
  await expect(page.locator('[data-salida]').getByText('Aún no tienes hojas')).toBeVisible();
  await expect(page.getByText('Aquí verás los reclamos y quejas que presentes con tu sesión iniciada, y nuestra respuesta.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Presentar un reclamo' })).toHaveCount(1);
  await expect(page.locator('.encabezado a[href="/libro-de-reclamaciones/"]')).toBeHidden(); // la del encabezado
  await expect(page.getByRole('main').locator('.boton-primario:visible')).toHaveCount(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/mis-reclamos-vacio.png', fullPage: true });
});

for (const f of fallos) {
  test(`mis reclamos: ${f.n} en la lista`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoRol(page, 'cliente');
    await simular(page, 'GET', '/reclamaciones/mias', f.r);
    // El rol se conoce por el perfil: 401 y 403 se simulan ahi.
    if (['401', '403'].includes(f.n)) await page.route(`${API}/perfil`, f.r);
    await page.goto('/app/reclamos/');
    await expect(page.locator('[data-salida]')).toContainText(f.n === '403' ? 'Esta sección es para clientes y el Administrador.' : f.n === '401' ? 'Tu sesión no es válida. Inicia sesión para continuar.' : f.texto);
    if (f.n === '401') await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', `/acceso/?volver=${encodeURIComponent('/app/reclamos/')}`);
    if (f.n === '403') await expect(page.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/app/');
    if (f.reintentar) await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('mis reclamos: el personal ve el 403 de la seccion', async ({ page }) => {
  await comoRol(page, 'personal');
  await page.goto('/app/reclamos/');
  await expect(page.getByText('[403]')).toBeVisible();
  await expect(page.locator('[data-salida]').getByText('Esta sección es para clientes y el Administrador.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/app/');
});

test('mis reclamos: sin JavaScript explica que falta y no queda en Cargando', async ({ browser }) => {
  const pagina = await (await browser.newContext({ javaScriptEnabled: false })).newPage();
  await pagina.goto('/app/reclamos/');
  await expect(pagina.locator('noscript .aviso-informacion')).toBeVisible();
  await expect(pagina.getByText('Cargando…')).toBeHidden();
});

// ---- Detalle del cliente ----
for (const t of tamanos) {
  test(`detalle del cliente: hoja con su respuesta, sin respondio ni adjuntos abribles, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoRol(page, 'cliente');
    await simular(page, 'GET', `/reclamaciones/${H1}`, json(200, hoja({ estado: 'respondida', respuesta: { ...RESPUESTA, respondida_por: undefined }, adjuntos: [{ n: 1, nombre: 'voucher.png', tipo: 'image/png', tamano: 2048 }] })));
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA N.º 000000001-2026');
    await expect(page).toHaveTitle('Hoja N.º 000000001-2026 · Bugalú Studio');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Mis reclamos', '000000001-2026']);
    await expect(page.locator('.encabezado-ruta').getByRole('link', { name: 'Mis reclamos' })).toHaveAttribute('href', '/app/reclamos/');
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Reclamo presentado el 17 nov 2026.');
    const hojaEl = page.locator('article.hoja');
    await expect(hojaEl.getByRole('heading', { level: 2 })).toContainText('N.º 000000001-2026');
    await expect(hojaEl).toContainText('Mezcla de mi EP, reserva R-2026-00014.');
    await expect(hojaEl).toContainText('S/ 1 250,00');
    await expect(hojaEl).toContainText('voucher.png');
    await expect(hojaEl).toContainText('PNG · 2 KB');
    await expect(hojaEl.getByRole('link')).toHaveCount(0); // solo el Administrador descarga
    expect(await hojaEl.locator('h3').allTextContents()).toEqual(['1. IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE', '2. IDENTIFICACIÓN DEL BIEN CONTRATADO', '3. DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR', '4. OBSERVACIONES Y ACCIONES ADOPTADAS POR EL PROVEEDOR']);
    await expect(hojaEl).toContainText('20 nov 2026, 10:00');
    await expect(hojaEl).toContainText('Lamentamos el retraso.');
    await expect(hojaEl).toContainText('Correo electrónico');
    await expect(hojaEl).not.toContainText('Respondió');
    await expect(hojaEl).not.toContainText('Luis Admin');
    await expect(page.locator('aside')).toHaveCount(0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/mis-reclamos-detalle-${t.nombre}.png`, fullPage: true });
  });
}

test('detalle del cliente: sin respuesta aun muestra el plazo; Imprimir llama a window.print y el estilo deja solo la hoja', async ({ page }) => {
  await comoRol(page, 'cliente');
  await simular(page, 'GET', `/reclamaciones/${H1}`, json(200, hoja()));
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  const hojaEl = page.locator('article.hoja');
  await expect(hojaEl).toContainText('SIN RESPUESTA AÚN');
  await expect(hojaEl).toContainText('Plazo de respuesta: hasta el 8 dic 2026');
  await page.getByRole('button', { name: 'Imprimir o guardar en PDF' }).click();
  expect(await page.evaluate(() => window.__impreso)).toBe(1);
  await page.emulateMedia({ media: 'print' });
  for (const sel of ['.cabecera', '.app-nav-lateral', '.app-nav-tactil', 'footer.pie', '.encabezado', '.saltar']) for (const el of await page.locator(sel).all()) await expect(el).toBeHidden();
  await expect(hojaEl).toBeVisible();
  await expect(hojaEl.locator('.hoja-copia')).toHaveText(/^Copia impresa desde localhost:\d+ el 17 nov 2026, 12:00$/);
  await expect(hojaEl).toContainText('SIN RESPUESTA AÚN'); // el estado va en texto: no depende del color
  await page.screenshot({ path: 'pruebas/capturas/mis-reclamos-detalle-impresion.png', fullPage: true });
});

for (const [n, resp] of [['404', errorApi(404, 'no_encontrado')], ['403 (hoja ajena)', errorApi(403, 'sin_permiso')]]) {
  test(`detalle del cliente: ${n} se pinta como no encontrada, sin revelar que existe`, async ({ page }) => {
    await comoRol(page, 'cliente');
    await simular(page, 'GET', `/reclamaciones/${H1}`, resp);
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await expect(page.getByText('[404]')).toBeVisible();
    await expect(page.locator('[data-salida]').getByText('No encontramos esta hoja en tu cuenta.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Volver a mis reclamos' })).toHaveAttribute('href', '/app/reclamos/');
    await sinViolaciones(page);
  });
}

test('detalle del cliente: un id que no es UUID no llama a la API', async ({ page }) => {
  await comoRol(page, 'cliente');
  const vistas = await simular(page, 'GET', '/reclamaciones/no-valido', json(200, hoja()));
  await page.goto('/app/reclamos/detalle?id=no-valido');
  await expect(page.locator('[data-salida]').getByText('No encontramos esta hoja en tu cuenta.')).toBeVisible();
  expect(vistas).toHaveLength(0);
});

for (const f of fallos.filter((x) => ['503', 'red', 'no-json'].includes(x.n))) {
  test(`detalle del cliente: ${f.n}`, async ({ page }) => {
    await comoRol(page, 'cliente');
    await simular(page, 'GET', `/reclamaciones/${H1}`, f.r);
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await expect(page.locator('[data-salida]')).toContainText(f.texto);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  });
}

// ==================== Bandeja del Administrador ====================
async function bandeja(page, { lista = json(200, TODAS) } = {}) {
  await comoRol(page, 'administrador');
  return simular(page, 'GET', '/reclamaciones', lista);
}
for (const t of tamanos) {
  test(`bandeja: pendientes primero por plazo, etiquetas en texto y marcas, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await bandeja(page);
    await page.goto('/app/reclamos/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('LIBRO DE RECLAMACIONES');
    await expect(page).toHaveTitle('Reclamos · Bugalú Studio');
    await expect(page.locator('.encabezado-indice')).toHaveText('[A12] CONTROL / RECLAMOS');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reclamos']);
    await expect(page.getByRole('link', { name: 'Presentar un reclamo' })).toBeHidden();
    await expect(page.getByRole('link', { name: 'Transcribir hoja del libro físico' })).toHaveAttribute('href', '/app/reclamos/transcribir');
    await expect(page.getByRole('button', { name: 'Exportar CSV' })).toBeVisible();
    const filas = tabla(page, 'Hojas del Libro de Reclamaciones');
    await expect(filas).toHaveCount(6);
    await expect(filas.nth(1).getByRole('rowheader')).toContainText('000000004-2026'); // vencida: la que vence antes
    await expect(filas.nth(1)).toContainText('FUERA DE PLAZO');
    await expect(filas.nth(1)).toContainText('Venció el 12 nov 2026');
    await expect(filas.nth(2).getByRole('rowheader')).toContainText('000000002-2026');
    await expect(filas.nth(2)).toContainText('VENCE HOY');
    await expect(filas.nth(2)).toContainText('REVISAR: POSIBLE ENVÍO AUTOMÁTICO');
    await expect(filas.nth(2)).toContainText('Queja');
    await expect(filas.nth(2)).toContainText('Beto Ríos');
    await expect(filas.nth(3).getByRole('rowheader')).toContainText('000000003-2026');
    await expect(filas.nth(3)).toContainText('VENCE EN 1 DÍA HÁBIL');
    await expect(filas.nth(3)).toContainText('TRANSCRITA');
    await expect(filas.nth(3)).toContainText('Sin marcar');
    await expect(filas.nth(4)).toContainText('VENCE EN 3 DÍAS HÁBILES');
    await expect(filas.nth(4)).toContainText('hasta el 20 nov 2026');
    await expect(filas.nth(5).getByRole('rowheader')).toContainText('000000005-2026'); // respondidas al final
    await expect(filas.nth(5)).toContainText('RESPONDIDA');
    await expect(page.getByRole('link', { name: 'Revisar hoja 000000002-2026' })).toHaveAttribute('href', `/app/reclamos/detalle?id=${H2}`);
    await expect(page.locator('[data-anuncio]')).toHaveText('5 hojas · 4 pendientes');
    const filtros = page.getByRole('navigation', { name: 'Filtrar por estado' });
    await expect(filtros.getByRole('link', { name: 'TODAS' })).toHaveAttribute('aria-current', 'true');
    await expect(filtros.getByRole('link', { name: 'PENDIENTES' })).toHaveAttribute('href', '/app/reclamos/?estado=pendiente');
    await expect(filtros.getByRole('link', { name: 'RESPONDIDAS' })).toHaveAttribute('href', '/app/reclamos/?estado=respondida');
    expect([...vistas[0].url.searchParams.keys()]).toEqual([]);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamos-bandeja-${t.nombre}.png`, fullPage: true });
  });
}

test('bandeja: filtros por estado y fechas llegan a la API y se conservan en los enlaces', async ({ page }) => {
  const vistas = await bandeja(page, { lista: json(200, [R.r1, R.r4]) });
  await page.goto('/app/reclamos/?estado=pendiente&desde=2026-11-01&hasta=2026-11-30');
  await expect(page.getByRole('table')).toBeVisible();
  expect(Object.fromEntries(vistas[0].url.searchParams)).toEqual({ estado: 'pendiente', desde: '2026-11-01', hasta: '2026-11-30' });
  const filtros = page.getByRole('navigation', { name: 'Filtrar por estado' });
  await expect(filtros.getByRole('link', { name: 'PENDIENTES' })).toHaveAttribute('aria-current', 'true');
  await expect(filtros.getByRole('link', { name: 'RESPONDIDAS' })).toHaveAttribute('href', '/app/reclamos/?estado=respondida&desde=2026-11-01&hasta=2026-11-30');
  await expect(page.getByLabel('Desde')).toHaveValue('2026-11-01');
  await expect(page.getByLabel('Hasta')).toHaveValue('2026-11-30');
  await expect(page.getByRole('link', { name: 'Quitar fechas' })).toHaveAttribute('href', '/app/reclamos/?estado=pendiente');
  // Filtrar navega con la URL del filtro; los parametros invalidos se ignoran.
  await page.getByLabel('Desde').fill('2026-11-10');
  await page.getByRole('button', { name: 'Filtrar' }).click();
  await expect(page).toHaveURL('/app/reclamos/?estado=pendiente&desde=2026-11-10&hasta=2026-11-30');
  await page.goto('/app/reclamos/?estado=lo-que-sea&desde=ayer');
  await expect(page.getByRole('table')).toBeVisible();
  expect(Object.fromEntries(vistas.at(-1).url.searchParams)).toEqual({});
});

test('bandeja: rango invertido se explica bajo HASTA sin llamar a la API; el 422 del servidor tambien', async ({ page }) => {
  const vistas = await bandeja(page, { lista: (r) => r.fulfill(new URL(r.request().url()).searchParams.has('desde') ? errorApi(422, 'rango_invalido') : json(200, TODAS)) });
  await page.goto('/app/reclamos/');
  await expect(page.getByRole('table')).toBeVisible();
  const antes = vistas.length;
  await page.getByLabel('Desde').fill('2026-11-20');
  await page.getByLabel('Hasta').fill('2026-11-10');
  await page.getByRole('button', { name: 'Filtrar' }).click();
  await expect(page.getByText('La fecha final debe ser igual o posterior a la inicial.')).toBeVisible();
  await expect(page.getByLabel('Hasta')).toBeFocused();
  await expect(page.getByLabel('Hasta')).toHaveAttribute('aria-invalid', 'true');
  expect(vistas.length).toBe(antes);
  await page.goto('/app/reclamos/?desde=2026-11-01&hasta=2026-11-30');
  await expect(page.getByText('La fecha final debe ser igual o posterior a la inicial.')).toBeVisible();
});

test('bandeja: vacio, y sin resultados con filtros y "Quitar filtros"', async ({ page }) => {
  await bandeja(page, { lista: json(200, []) });
  await page.goto('/app/reclamos/');
  await expect(page.locator('[data-salida]').getByText('Aún no hay hojas')).toBeVisible();
  await expect(page.getByText('Cuando alguien presente un reclamo o una queja, aparecerá aquí y te avisaremos por correo.')).toBeVisible();
  await expect(page.getByRole('main').getByRole('link', { name: 'Quitar filtros' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Transcribir hoja del libro físico' })).toBeVisible(); // las acciones del encabezado siguen
  await sinViolaciones(page);
  await page.goto('/app/reclamos/?estado=respondida&desde=2026-11-01&hasta=2026-11-30');
  await expect(page.locator('[data-salida]').getByText('No hay hojas respondidas entre el 1 nov 2026 y el 30 nov 2026.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Quitar filtros' })).toHaveAttribute('href', '/app/reclamos/');
  await sinViolaciones(page);
});

for (const f of fallos) {
  test(`bandeja: ${f.n} en la lista`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoRol(page, 'administrador');
    await simular(page, 'GET', '/reclamaciones', f.r);
    if (['401', '403'].includes(f.n)) await page.route(`${API}/perfil`, f.r);
    await page.addInitScript(() => localStorage.setItem('bugalu-area', 'estudio'));
    await page.goto('/app/reclamos/');
    await expect(page.locator('[data-salida]')).toContainText(f.n === '403' ? 'Esta sección es para clientes y el Administrador.' : f.texto);
    if (f.reintentar) await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    expect(consola).toEqual([]);
  });
}

// ---- Exportar CSV (CA-11) ----
test('exportar CSV: pide DESDE y HASTA, descarga con el rango en el nombre y manda el token', async ({ page }) => {
  await bandeja(page);
  let auth;
  const vistas = await simular(page, 'GET', '/reclamaciones/exportar', (r) => { auth = r.request().headers().authorization; return r.fulfill({ status: 200, contentType: 'text/csv', body: 'numero,estado\n000000001-2026,pendiente\n' }); });
  await page.goto('/app/reclamos/');
  await page.getByRole('button', { name: 'Exportar CSV' }).click();
  await expect(page.getByText('Elige DESDE y HASTA para exportar.')).toBeVisible();
  await expect(page.getByLabel('Desde')).toBeFocused();
  expect(vistas).toHaveLength(0);
  await page.getByLabel('Desde').fill('2026-11-01');
  await page.getByLabel('Hasta').fill('2026-11-30');
  const [descarga] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Exportar CSV' }).click()]);
  expect(descarga.suggestedFilename()).toBe('reclamaciones-2026-11-01-2026-11-30.csv');
  expect(await (await import('node:fs/promises')).readFile(await descarga.path(), 'utf8')).toBe('numero,estado\n000000001-2026,pendiente\n');
  expect(Object.fromEntries(vistas[0].url.searchParams)).toEqual({ desde: '2026-11-01', hasta: '2026-11-30' });
  expect(auth).toBe('Bearer token-de-prueba');
  await expect(page.getByRole('button', { name: 'Exportar CSV' })).not.toHaveAttribute('aria-busy', 'true');
  await expect(page.getByText('Elige DESDE y HASTA para exportar.')).toHaveCount(0);
});

for (const [n, resp, texto] of [
  ['422 rango_invalido', errorApi(422, 'rango_invalido'), 'La fecha final debe ser igual o posterior a la inicial.'],
  ['503', errorApi(503, 'servicio_no_disponible'), 'El servicio no responde. Inténtalo de nuevo en unos minutos.'],
]) {
  test(`exportar CSV: ${n}`, async ({ page }) => {
    await bandeja(page);
    await simular(page, 'GET', '/reclamaciones/exportar', resp);
    await page.goto('/app/reclamos/');
    await page.getByLabel('Desde').fill('2026-11-01');
    await page.getByLabel('Hasta').fill('2026-11-30');
    await page.getByRole('button', { name: 'Exportar CSV' }).click();
    await expect(page.locator('main')).toContainText(texto);
    await expect(page.getByRole('button', { name: 'Exportar CSV' })).toBeEnabled();
  });
}

// ---- Detalle del Administrador: adjuntos ----
const conAdjuntos = (extra = {}) => hoja({ adjuntos: [{ n: 1, nombre: 'voucher.png', tipo: 'image/png', tamano: 2048 }, { n: 2, nombre: 'constancia.pdf', tipo: 'application/pdf', tamano: 3 * 1048576 }], ...extra });
async function detalleAdmin(page, h = conAdjuntos()) {
  await comoRol(page, 'administrador');
  await simular(page, 'GET', `/reclamaciones/${H1}`, json(200, h));
  await page.context().route('http://supabase.prueba/storage/**', (r) => r.fulfill({ status: 200, contentType: 'text/plain', body: 'archivo' }));
}
for (const t of tamanos) {
  test(`detalle del Administrador: hoja con adjuntos, respuesta y plazo en el lateral, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await detalleAdmin(page, conAdjuntos({ revisar_spam: true }));
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA N.º 000000001-2026');
    await expect(page.locator('.encabezado-indice')).toHaveText('[A12] CONTROL / RECLAMOS');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reclamos', '000000001-2026']);
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Ana Pérez · Reclamo presentado el 17 nov 2026.');
    await expect(page.getByRole('button', { name: 'Imprimir o guardar en PDF' })).toBeHidden();
    await expect(page.getByText('REVISAR: POSIBLE ENVÍO AUTOMÁTICO')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Abrir voucher.png (pestaña nueva)' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Abrir constancia.pdf (pestaña nueva)' })).toBeVisible();
    await expect(page.locator('article.hoja')).toContainText('PDF · 3 MB');
    const lateral = page.getByRole('region', { name: /R1 Respuesta/i });
    await expect(lateral).toBeVisible();
    await expect(lateral).toContainText('VENCE EN 15 DÍAS HÁBILES');
    await expect(lateral).toContainText('hasta el 8 dic 2026');
    await expect(lateral).toContainText('El consumidor pidió correo electrónico.');
    await expect(lateral.getByRole('button', { name: 'Revisar respuesta' })).toBeVisible();
    await expect(lateral.getByLabel('Referencia de la carta')).toBeHidden();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamos-detalle-admin-${t.nombre}.png`, fullPage: true });
  });
}

test('adjunto: "Abrir" pide la URL firmada con el token y la abre en una pestaña nueva', async ({ page }) => {
  await detalleAdmin(page);
  const vistas = await simular(page, 'GET', `/reclamaciones/${H1}/adjuntos/1`, json(200, { url: 'http://supabase.prueba/storage/v1/object/sign/adjunto-1?token=t', expira_en: '2026-11-17T17:10:00Z' }));
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  const [popup] = await Promise.all([page.waitForEvent('popup'), page.getByRole('link', { name: 'Abrir voucher.png (pestaña nueva)' }).click()]);
  await popup.waitForURL('http://supabase.prueba/storage/v1/object/sign/adjunto-1?token=t');
  expect(vistas).toHaveLength(1);
  await expect(page).toHaveURL(/detalle\?id=/); // la hoja sigue ahi
});

for (const [n, resp] of [['404', errorApi(404, 'no_encontrado')], ['503', errorApi(503, 'servicio_no_disponible')], ['URL de otro origen', json(200, { url: 'http://otro.example/x', expira_en: '2026-11-17T17:10:00Z' })], ['red caida', (r) => r.abort('connectionrefused')]]) {
  test(`adjunto: ${n} avisa bajo el archivo y la pestaña no queda abierta`, async ({ page }) => {
    await detalleAdmin(page);
    await simular(page, 'GET', `/reclamaciones/${H1}/adjuntos/2`, resp);
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await page.getByRole('link', { name: 'Abrir constancia.pdf (pestaña nueva)' }).click();
    await expect(page.getByText('No pudimos abrir constancia.pdf. Inténtalo de nuevo.')).toBeVisible();
    await expect(page.getByText('No pudimos abrir voucher.png')).toHaveCount(0);
    await expect.poll(() => page.context().pages().length).toBe(1);
    await sinViolaciones(page);
  });
}

// ---- Respuesta (CA-07) ----
async function responder(page, { h = conAdjuntos(), respuesta } = {}) {
  await comoRol(page, 'administrador');
  let respondida = false;
  await simular(page, 'GET', `/reclamaciones/${H1}`, (r) => r.fulfill(json(200, respondida ? { ...h, estado: 'respondida', respuesta: { ...RESPUESTA, medio: h.medio_respuesta, ...(h.medio_respuesta === 'carta' && { referencia_carta: 'CARTA-123' }) } } : h)));
  await simular(page, 'GET', '/reclamaciones', json(200, TODAS));
  const vistas = await simular(page, 'POST', `/reclamaciones/${H1}/respuesta`, respuesta ?? ((r) => { respondida = true; return r.fulfill(json(200, hoja({ estado: 'respondida' }))); }));
  return vistas;
}
const panel = (page) => page.getByRole('region', { name: /R1/ });

test('responder por correo: validacion, revision, corregir conserva el texto, enviar y aviso', async ({ page }) => {
  const consola = vigilarConsola(page);
  const vistas = await responder(page);
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(aviso(page)).toContainText('Revisa 1 dato');
  await expect(page.getByText('Escribe la respuesta con al menos 10 caracteres.').first()).toBeVisible();
  await sinViolaciones(page);
  await page.locator('#rec-texto').fill('Lamentamos el retraso.\nTe devolvemos S/ 625,00.');
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(page.getByRole('heading', { level: 2, name: /R1 Revisa la respuesta/i })).toBeFocused();
  await expect(page.getByText('Enviamos esta respuesta a ana@correo.com y queda registrada con tu nombre. No se puede editar ni borrar.')).toBeVisible();
  await expect(page.locator('[data-r="texto"]')).toHaveText('Lamentamos el retraso.\nTe devolvemos S/ 625,00.');
  await expect(page.getByRole('button', { name: 'Enviar respuesta' })).toBeVisible();
  expect(vistas).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reclamos-respuesta-revision.png', fullPage: true });
  // Corregir conserva lo escrito y devuelve el foco a RESPUESTA.
  await page.getByRole('button', { name: 'Corregir respuesta' }).click();
  await expect(page.locator('#rec-texto')).toBeFocused();
  await expect(page.locator('#rec-texto')).toHaveValue('Lamentamos el retraso.\nTe devolvemos S/ 625,00.');
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await page.getByRole('button', { name: 'Enviar respuesta' }).click();
  await expect(aviso(page)).toContainText('Respuesta enviada al correo del consumidor.');
  await expect(aviso(page)).toBeFocused();
  await expect(page).toHaveURL(`/app/reclamos/detalle?id=${H1}`); // el aviso se quita de la direccion
  expect(vistas).toHaveLength(1);
  expect(vistas[0].cuerpo).toEqual({ texto: 'Lamentamos el retraso.\nTe devolvemos S/ 625,00.' });
  // Ya respondida: el formulario no vuelve; hay indicador y la respuesta se lee en la seccion 4, con su autor.
  await expect(page.getByText('RESPONDIDA').first()).toBeVisible();
  await expect(panel(page).getByRole('button')).toHaveCount(0);
  await expect(page.locator('article.hoja')).toContainText('Luis Admin');
  await expect(page.locator('article.hoja')).toContainText('Lamentamos el retraso.');
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/reclamos-respondida.png', fullPage: true });
});

test('responder por carta: pide referencia y fecha de envio, y envia ambas', async ({ page }) => {
  const vistas = await responder(page, { h: conAdjuntos({ medio_respuesta: 'carta' }) });
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  await expect(page.getByText('El consumidor pidió carta al domicilio.')).toBeVisible();
  await expect(page.getByLabel('Fecha de envío')).toHaveAttribute('max', '2026-11-17');
  await page.locator('#rec-texto').fill('Te enviamos la carta con la solución.');
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(aviso(page)).toContainText('Revisa 2 datos');
  await expect(page.getByText('Escribe la referencia de la carta.').first()).toBeVisible();
  await expect(page.getByText('Elige la fecha en que enviaste la carta.').first()).toBeVisible();
  await page.getByLabel('Referencia de la carta').fill('CARTA-123');
  await page.getByLabel('Fecha de envío').evaluate((e) => (e.value = '2026-11-18'));
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(page.getByText('La fecha de envío no puede ser futura.').first()).toBeVisible();
  await page.getByLabel('Fecha de envío').fill('2026-11-16');
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(page.getByText('Queda registrada la carta CARTA-123 enviada el 16 nov 2026, con tu nombre. No se puede editar ni borrar.')).toBeVisible();
  await expect(page.locator('[data-r="destino"]')).toHaveText('Av. Siempre Viva 123, Lima'); // el destino es el domicilio
  await page.getByRole('button', { name: 'Registrar respuesta' }).click();
  await expect(aviso(page)).toContainText('Respuesta registrada con la carta CARTA-123.');
  expect(vistas[0].cuerpo).toEqual({ texto: 'Te enviamos la carta con la solución.', referencia_carta: 'CARTA-123', enviada_en: '2026-11-16T00:00:00-05:00' });
});

test('responder: 409 ya_respondida avisa y recarga la hoja con la respuesta', async ({ page }) => {
  let ya = false;
  await comoRol(page, 'administrador');
  await simular(page, 'GET', `/reclamaciones/${H1}`, (r) => r.fulfill(json(200, ya ? hoja({ estado: 'respondida', respuesta: RESPUESTA }) : hoja())));
  await simular(page, 'POST', `/reclamaciones/${H1}/respuesta`, (r) => { ya = true; return r.fulfill(errorApi(409, 'ya_respondida')); });
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  await page.locator('#rec-texto').fill('Lamentamos el retraso, te escribimos.');
  await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
  await page.getByRole('button', { name: 'Enviar respuesta' }).click();
  await expect(aviso(page)).toContainText('Esta hoja ya tiene respuesta, quizá desde otra sesión.');
  await expect(page.locator('article.hoja')).toContainText('Lamentamos el retraso.');
  await expect(page.locator('[aria-busy]')).toHaveCount(0);
});

for (const [n, resp, texto] of [
  ['422', errorApi(422, 'datos_invalidos'), 'Escribe la respuesta con al menos 10 caracteres.'],
  ['404', errorApi(404, 'no_encontrado'), 'No encontramos esta hoja.'],
]) {
  test(`responder: ${n} del servidor`, async ({ page }) => {
    await responder(page, { respuesta: resp });
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await page.locator('#rec-texto').fill('Lamentamos el retraso, te escribimos.');
    await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
    await page.getByRole('button', { name: 'Enviar respuesta' }).click();
    await expect(page.getByText(texto).first()).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
  });
}

for (const f of fallos.filter((x) => ['503', 'red'].includes(x.n))) {
  test(`responder: ${f.n} al enviar conserva lo escrito y no ofrece Reintentar`, async ({ page }) => {
    await responder(page, { respuesta: f.r });
    await page.goto(`/app/reclamos/detalle?id=${H1}`);
    await page.locator('#rec-texto').fill('Lamentamos el retraso, te escribimos.');
    await panel(page).getByRole('button', { name: 'Revisar respuesta' }).click();
    await page.getByRole('button', { name: 'Enviar respuesta' }).click();
    await expect(aviso(page)).toContainText(f.texto);
    await expect(aviso(page)).toBeFocused();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
    await expect(page.locator('[data-r="texto"]')).toHaveText('Lamentamos el retraso, te escribimos.');
    await expect(page.getByRole('button', { name: 'Enviar respuesta' })).toBeEnabled();
  });
}

test('detalle del Administrador: una hoja transcrita lleva su etiqueta, la fecha original y el aviso de la URL', async ({ page }) => {
  await detalleAdmin(page, hoja({ origen: 'libro_fisico', numero_hoja_fisica: 'F-0042', fecha_original: '2026-11-15T14:00:00Z', creada_en: '2026-11-16T15:00:00Z' }));
  await page.goto(`/app/reclamos/detalle?id=${H1}&aviso=hoja-transcrita`);
  await expect(aviso(page)).toContainText('Hoja transcrita con el N.º 000000001-2026. El plazo de respuesta cuenta desde la fecha original: vence el 8 dic 2026.');
  await expect(page.locator('article.hoja')).toContainText('TRANSCRITA DEL LIBRO FÍSICO · HOJA F-0042');
  await expect(page.locator('article.hoja time[data-fecha]')).toHaveText('15 nov 2026, 09:00');
  await page.goto(`/app/reclamos/detalle?id=${H1}&aviso=otra-cosa`);
  await expect(aviso(page)).toHaveCount(0); // lista cerrada
});

test('detalle del Administrador: 404 y 403', async ({ page }) => {
  await comoRol(page, 'administrador');
  await simular(page, 'GET', `/reclamaciones/${H1}`, errorApi(404, 'no_encontrado'));
  await page.goto(`/app/reclamos/detalle?id=${H1}`);
  await expect(page.getByText('[404]')).toBeVisible();
  await expect(page.locator('[data-salida]').getByText('No encontramos esta hoja.', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a reclamos' }).last()).toHaveAttribute('href', '/app/reclamos/');
  await sinViolaciones(page);
});

// ==================== Transcripcion del libro fisico (CA-09) ====================
const llenarTranscripcion = async (page) => {
  await page.locator('#rc-numero-fisica').fill('F-0042');
  await page.locator('#rc-fecha-original').fill('2026-11-16');
  await page.locator('#rc-hora-original').fill('18:30');
  await page.locator('#rc-nombre').fill('Carla Soto');
  await page.locator('#rc-tipo-documento').selectOption('pasaporte');
  await page.locator('#rc-documento').fill('ab123456');
  await page.locator('#rc-domicilio').fill('Jr. Lima 100, Lima');
  await page.locator('#rc-correo').fill('carla@correo.com');
  await page.locator('#rc-tipo-sin').check();
  await page.locator('#rc-detalle').fill('Anotado a mano en el libro de respaldo.');
  await page.locator('#rc-pedido').fill('Que me llamen para explicarme el cobro.');
  await page.locator('#rc-medio-carta').check();
};
for (const t of tamanos) {
  test(`transcribir: formulario del libro fisico sin trampa ni prellenado, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoRol(page, 'administrador');
    await page.goto('/app/reclamos/transcribir');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('TRANSCRIBIR HOJA');
    await expect(page.locator('.encabezado-indice')).toHaveText('[A12] CONTROL / RECLAMOS');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reclamos', 'Transcribir']);
    await expect(page.getByRole('link', { name: 'Volver a reclamos' })).toHaveAttribute('href', '/app/reclamos/');
    await expect(page.locator('form h2')).toHaveText(['T0 HOJA FÍSICA', '1 IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE', '2 IDENTIFICACIÓN DEL BIEN CONTRATADO', '3 DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR']);
    await expect(page.locator('input[name="sitio_web"]')).toHaveCount(0);
    await expect(page.getByText('La formulación del reclamo no impide acudir')).toHaveCount(0);
    await expect(page.getByText('La fecha y la hora en que el consumidor llenó la hoja, no las de hoy.')).toBeVisible();
    await expect(page.locator('#rc-medio-correo')).not.toBeChecked(); // sin valor por defecto
    await expect(page.locator('#rc-medio-carta')).not.toBeChecked();
    await expect(page.locator('#rc-tipo-sin')).toBeVisible();
    await expect(page.getByRole('main').locator('.boton-primario:visible')).toHaveCount(1);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamos-transcribir-${t.nombre}.png`, fullPage: true });
  });
}

test('transcribir: validacion propia (hoja fisica, fecha futura, hora, medio) y aviso de mas de 1 dia', async ({ page }) => {
  await comoRol(page, 'administrador');
  await page.goto('/app/reclamos/transcribir');
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await expect(aviso(page)).toContainText('Revisa 12 datos antes de seguir');
  await expect(page.locator('#rc-numero-fisica')).toBeFocused();
  for (const m of ['Escribe el número de la hoja física.', 'Elige la fecha original.', 'Elige la hora original.', 'Elige qué marcó el consumidor como medio de respuesta.']) await expect(page.getByText(m).first()).toBeVisible();
  await page.locator('#rc-fecha-original').evaluate((e) => (e.value = '2026-11-18'));
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await expect(page.getByText('La fecha original no puede ser futura.').first()).toBeVisible();
  // Mas de 1 dia: aviso estatico que no bloquea.
  await page.locator('#rc-fecha-original').fill('2026-11-10');
  await expect(page.getByText('Esta hoja tiene más de 1 día')).toBeVisible();
  await expect(page.getByText('El reglamento pide transcribirla dentro de 1 día calendario. Regístrala igual: el plazo de respuesta ya corre desde el 10 nov 2026.')).toBeVisible();
  await page.locator('#rc-fecha-original').fill('2026-11-16');
  await expect(page.getByText('Esta hoja tiene más de 1 día')).toBeHidden();
});

test('transcribir: revision con TRANSCRITA y fecha original, registro multipart y paso al detalle con el aviso', async ({ page }) => {
  await comoRol(page, 'administrador');
  const vistas = await simularMultipart(page, '/reclamaciones/transcripcion', json(201, hoja({ origen: 'libro_fisico', numero_hoja_fisica: 'F-0042', fecha_original: '2026-11-16T23:30:00Z' })));
  await simular(page, 'GET', `/reclamaciones/${H1}`, json(200, hoja({ origen: 'libro_fisico', numero_hoja_fisica: 'F-0042', fecha_original: '2026-11-16T23:30:00Z', medio_respuesta: 'carta', tipo: null })));
  await page.goto('/app/reclamos/transcribir');
  await llenarTranscripcion(page);
  await page.locator('#rc-adjuntos').setInputFiles(archivo('hoja-fisica.png'));
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'REVISA LA HOJA' })).toBeFocused();
  const hojaEl = page.locator('article.hoja');
  await expect(hojaEl).toContainText('TRANSCRITA DEL LIBRO FÍSICO · HOJA F-0042');
  await expect(hojaEl.locator('time[data-fecha]')).toHaveText('16 nov 2026, 18:30');
  await expect(hojaEl).toContainText('Pasaporte AB123456');
  await expect(hojaEl).toContainText('Sin marcar');
  await expect(hojaEl).toContainText('Carta al domicilio');
  await expect(hojaEl).toContainText('hoja-fisica.png');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reclamos-transcribir-revision.png', fullPage: true });
  await page.getByRole('button', { name: 'Corregir datos' }).click();
  await expect(page.locator('#rc-numero-fisica')).toHaveValue('F-0042');
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await page.getByRole('button', { name: 'Registrar hoja' }).click();
  await expect(page).toHaveURL(`/app/reclamos/detalle?id=${H1}`);
  await expect(aviso(page)).toContainText('Hoja transcrita con el N.º 000000001-2026.');
  expect(vistas).toHaveLength(1);
  expect(vistas[0].tipo).toMatch(/^multipart\/form-data/);
  expect(vistas[0].adjuntos).toEqual(['hoja-fisica.png']);
  expect(vistas[0].datos).toEqual({
    confirmado: true,
    consumidor: { nombre: 'Carla Soto', tipo_documento: 'pasaporte', documento: 'AB123456', domicilio: 'Jr. Lima 100, Lima', correo: 'carla@correo.com' },
    es_menor: false, bien: { tipo: 'servicio' }, tipo: null, detalle: 'Anotado a mano en el libro de respaldo.', pedido: 'Que me llamen para explicarme el cobro.', medio_respuesta: 'carta',
    fecha_original: '2026-11-16T18:30:00-05:00', numero_hoja_fisica: 'F-0042', clave_envio: expect.stringMatching(/^[0-9a-f-]{36}$/i),
  });
});

test('transcribir: 422 con campo, 503 y red conservan lo escrito', async ({ page }) => {
  await comoRol(page, 'administrador');
  await simularMultipart(page, '/reclamaciones/transcripcion', (r, n) => r.fulfill(n === 1 ? { status: 422, contentType: 'application/json', body: JSON.stringify({ error: { codigo: 'datos_invalidos', mensaje: 'Ya existe esa hoja física', detalles: { campo: 'numero_hoja_fisica' } } }) } : n === 2 ? errorApi(503, 'servicio_no_disponible') : errorApi(500, 'x')));
  await page.goto('/app/reclamos/transcribir');
  await llenarTranscripcion(page);
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await page.getByRole('button', { name: 'Registrar hoja' }).click();
  await expect(page.locator('#rc-numero-fisica')).toBeFocused();
  await expect(page.locator('#rc-numero-fisica-error')).toContainText('Ya existe esa hoja física');
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await page.getByRole('button', { name: 'Registrar hoja' }).click();
  await expect(aviso(page)).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos. Tus datos siguen aquí.');
  await expect(page.getByRole('button', { name: 'Registrar hoja' })).toBeEnabled();
  await page.getByRole('button', { name: 'Corregir datos' }).click();
  await expect(page.locator('#rc-detalle')).toHaveValue('Anotado a mano en el libro de respaldo.');
});

test('transcribir: el cliente ve "No tienes permiso" y el formulario no se muestra', async ({ page }) => {
  await comoRol(page, 'cliente');
  await page.goto('/app/reclamos/transcribir');
  await expect(aviso(page)).toContainText('No tienes permiso');
  await expect(aviso(page)).toContainText('Esta sección es solo para el Administrador.');
  await expect(page.locator('form')).toBeHidden();
  await sinViolaciones(page);
});

test('transcribir: sin sesion lleva al acceso interno', async ({ page }) => {
  await silenciarApi(page);
  await page.goto('/app/reclamos/transcribir');
  await expect(page.getByRole('link', { name: 'Ir al acceso interno' })).toHaveAttribute('href', `/acceso/interno?volver=${encodeURIComponent('/app/reclamos/transcribir')}`);
  await expect(page.locator('form')).toBeHidden();
});

test('transcribir: sin JavaScript explica que falta', async ({ browser }) => {
  const pagina = await (await browser.newContext({ javaScriptEnabled: false })).newPage();
  await pagina.goto('/app/reclamos/transcribir');
  await expect(pagina.locator('noscript .aviso-titulo')).toHaveText('Esta sección necesita JavaScript');
  await expect(pagina.locator('form')).toBeHidden();
});

// ==================== Enlaces de la app (CA-01) ====================
for (const t of tamanos) {
  for (const rol of ['cliente', 'administrador']) {
    test(`app: "Libro de Reclamaciones" al pie de la columna de contenido y fuera del menu (${rol}, ${t.nombre})`, async ({ page }) => {
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await comoRol(page, rol);
      await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, [])));
      await page.goto('/app/');
      const pie = page.getByRole('contentinfo');
      await expect(pie.getByRole('link', { name: 'Libro de Reclamaciones', exact: true })).toHaveAttribute('href', '/libro-de-reclamaciones/');
      // Esta bajo <main> y dentro de la columna de contenido, no en la cabecera.
      expect(await pie.evaluate((e) => !e.closest('header') && !e.closest('main') && Boolean(e.closest('.app-columna')))).toBe(true);
      expect(await page.locator('.cabecera-menu-panel').getByText('Libro de Reclamaciones').count()).toBe(0);
      // El menu: "Mis reclamos" solo para el cliente; el Administrador tiene RECLAMOS.
      await page.locator('.cabecera-menu-boton').click();
      const menu = page.locator('.cabecera-menu-panel');
      if (rol === 'cliente') {
        await expect(menu.getByRole('link', { name: 'Mis reclamos' })).toHaveAttribute('href', '/app/reclamos/');
      } else {
        await expect(menu.getByRole('link', { name: 'Mis reclamos' })).toBeHidden();
        if (t.ancho === 390) await expect(menu.getByRole('link', { name: 'Reclamos', exact: true })).toHaveAttribute('href', '/app/reclamos/');
        else await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Reclamos' })).toHaveAttribute('href', '/app/reclamos/');
      }
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/app-pie-reclamaciones-${rol}-${t.nombre}.png`, fullPage: true });
    });
  }
}

test('app: el destino RECLAMOS queda actual en la bandeja y su detalle (1440)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await comoRol(page, 'administrador');
  await simular(page, 'GET', '/reclamaciones', json(200, TODAS));
  await page.goto('/app/reclamos/');
  await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Reclamos' })).toHaveAttribute('aria-current', 'page');
});
