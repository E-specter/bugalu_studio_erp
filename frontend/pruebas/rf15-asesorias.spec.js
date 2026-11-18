// RF-15 etapa A: directorio, perfil publico, ficha, horarios y administracion de profesionales. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, conSesion, silenciarApi, perfil, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, json, errorApi } from './ayudas-admin.js';

const IGV = { nombre: 'IGV', porcentaje: '18.00', incluido: true, base: '67.80', monto: '12.20' };
const PROF = {
  id: 'p1', nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat', foto_url: null, presentacion: 'Hola\nmundo',
  redes: [{ red: 'instagram', valor: '@ana' }, { red: 'spotify', valor: 'https://open.spotify.com/ana' }],
  especialidades: [{ id: 'e1', nombre: 'Producción' }], duraciones: [{ minutos: 30, precio: '80.00', igv: IGV }, { minutos: 60, precio: '140.00', igv: IGV }],
  activo: true, publicado: true,
};
const OTRO = { ...PROF, id: 'p2', nombre: 'Luis Mora', nombre_artistico: null, especialidades: [{ id: 'e2', nombre: 'Coros' }], duraciones: [{ minutos: 60, precio: '120.00', igv: IGV }] };
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const ESPS = [{ id: 'e1', nombre: 'Producción', activa: true }, { id: 'e2', nombre: 'Coros', activa: true }];
const DISP = (extra = {}) => ({
  limites: { desde: '2026-11-15T17:00:00-05:00', hasta: '2027-01-10T00:00:00-05:00' },
  horarios: [{ id: 'h1', inicio: '2026-11-17T10:00:00-05:00', fin: '2026-11-17T13:00:00-05:00' }],
  ocupados: [{ inicio: '2026-11-17T11:00:00-05:00', fin: '2026-11-17T12:00:00-05:00', propia: false }],
  dias: [{ fecha: '2026-11-17', minutos_libres: 120 }], duraciones: PROF.duraciones, ...extra,
});
// Texto visible de un aviso (titulo y texto juntos) o de un dato; nunca de la region viva oculta.
const dice = (page, t) => page.locator('.aviso, .gestion-vacio-titulo, .panel-titulo, .panel-ayuda, .gestion-periodo-titulo, .dir-linea, .dir-presentacion, .etiqueta, .carga-boton, .tarjeta-completo, td, th, dd, li, label, h1, h2, p:not([data-anuncio])').filter({ hasText: t }).first();
const hoy = (page) => page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z')); // domingo 15 nov 2026, 10:00 Lima
const comoProfesional = async (page, extra = {}) => {
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ id: 'p1', rol: 'profesional', ...extra })));
};
const fallosCarga = [
  ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible'))],
  ['red', (r) => r.abort('connectionrefused')],
  ['no-json', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' })],
];

// ---------- Directorio ----------
async function directorio(page, { lista = json(200, [PROF, OTRO]), esp = json(200, ESPS) } = {}) {
  await hoy(page);
  await silenciarApi(page);
  await simular(page, 'GET', '/especialidades-asesoria', esp);
  return simular(page, 'GET', '/profesionales', lista);
}

for (const t of tamanos) {
  test(`directorio: tarjetas, filtros y nota de IGV a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await directorio(page);
    await page.goto('/asesorias/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('PROFESIONALES DEL ESTUDIO');
    const lista = page.getByRole('list', { name: 'Profesionales' });
    await expect(page.locator('.dir-item')).toHaveCount(2);
    await expect(page.getByRole('link', { name: /^Ana Beat ?, ver perfil$/ })).toHaveAttribute('href', '/asesorias/profesional/?id=p1');
    await expect(lista.getByText('Ana Pérez')).toBeVisible();
    await expect(lista).toContainText('S/ 80,00');
    await expect(dice(page, '2 profesionales. Precios en soles con IGV incluido (18 %).')).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Filtrar por especialidad' }).getByRole('link')).toHaveCount(3);
    await expect(page.getByRole('link', { name: 'Todas' })).toHaveAttribute('aria-current', 'true');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-directorio-${t.nombre}.png`, fullPage: true });
  });
}

test('directorio: el filtro pide la especialidad, cambia la URL y deja el foco', async ({ page }) => {
  const vistas = await directorio(page, { lista: (r) => r.fulfill(json(200, new URL(r.request().url()).searchParams.get('especialidad') === 'e2' ? [OTRO] : [PROF, OTRO])) });
  await page.goto('/asesorias/');
  await page.getByRole('link', { name: 'Coros' }).click();
  await expect(page).toHaveURL(/\?especialidad=e2$/);
  await expect(page.locator('.dir-item')).toHaveCount(1);
  await expect(page.getByRole('link', { name: 'Coros' })).toBeFocused();
  await expect(page.getByRole('link', { name: 'Coros' })).toHaveAttribute('aria-current', 'true');
  await expect(page.locator('[data-anuncio]')).toHaveText('1 profesional en Coros.');
  expect(vistas.at(-1).url.searchParams.get('especialidad')).toBe('e2');
  expect(vistas.every((v) => !('authorization' in {}))).toBe(true);
});

test('directorio: vacio sin filtros y sin resultados con filtro', async ({ page }) => {
  await directorio(page, { lista: json(200, []) });
  await page.goto('/asesorias/');
  await expect(page.getByRole('heading', { name: 'Aún no hay profesionales publicados' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Filtrar por especialidad' })).toBeHidden();
  await sinViolaciones(page);
  await page.goto('/asesorias/?especialidad=e2');
  await expect(dice(page, 'Nadie ofrece Coros por ahora.').first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver todas las especialidades' })).toHaveAttribute('href', '/asesorias/');
  await expect(page.getByRole('link', { name: 'Coros' })).toBeVisible();
});

test('directorio: especialidad desconocida o 422 muestra todo, avisa y limpia la URL', async ({ page }) => {
  await directorio(page);
  await page.goto('/asesorias/?especialidad=zzz');
  await expect(dice(page, 'Esa especialidad ya no está disponible. Te mostramos todos los profesionales.')).toBeVisible();
  await expect(page).toHaveURL(/\/asesorias\/$/);
  await expect(page.locator('.dir-item')).toHaveCount(2);
  await page.unroute(`${API}/profesionales`).catch(() => {});
});

test('directorio: un fallo del catalogo de filtros no tapa la lista', async ({ page }) => {
  await directorio(page, { esp: json(503, { error: { codigo: 'x', mensaje: 'x' } }) });
  await page.goto('/asesorias/');
  await expect(page.locator('.dir-item')).toHaveCount(2);
  await expect(page.getByRole('navigation', { name: 'Filtrar por especialidad' })).toBeHidden();
});

for (const [n, r] of fallosCarga) {
  test(`directorio: ${n} muestra el error con Reintentar y devuelve el foco al titulo`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = true;
    await directorio(page, { lista: (x) => (falla ? r(x) : x.fulfill(json(200, [PROF]))) });
    await page.goto('/asesorias/');
    const textos = { 503: 'El directorio no responde. Inténtalo de nuevo en unos minutos.', red: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', 'no-json': 'Algo salió mal al cargar el directorio.' };
    await expect(page.locator('.aviso-error')).toContainText(textos[n]);
    await sinViolaciones(page);
    falla = false;
    await page.getByRole('button', { name: 'Reintentar' }).click();
    await expect(page.getByRole('list', { name: 'Profesionales' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    expect(consola).toEqual([]);
  });
}

test.describe('sin JS', () => {
  test.use({ javaScriptEnabled: false });
  test('directorio y perfil avisan que necesitan JavaScript', async ({ page }) => {
    await page.goto('/asesorias/');
    expect(await page.content()).toContain('El directorio necesita JavaScript');
    await page.goto('/asesorias/profesional/?id=p1');
    expect(await page.content()).toContain('Este perfil necesita JavaScript');
    await expect(page.getByRole('link', { name: 'Volver al directorio' })).toBeVisible();
  });
});

// ---------- Perfil publico ----------
async function perfilPublico(page, { prof = json(200, PROF), disp = json(200, DISP()) } = {}) {
  await hoy(page);
  await silenciarApi(page);
  const vistas = await simular(page, 'GET', '/profesionales/p1', prof);
  const vistasDisp = await simular(page, 'GET', '/profesionales/p1/disponibilidad', disp);
  return { vistas, vistasDisp };
}

for (const t of tamanos) {
  test(`perfil: identidad, precios, redes, horarios y Agendar deshabilitado a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const { vistasDisp } = await perfilPublico(page);
    await page.goto('/asesorias/profesional/?id=p1&fecha=2026-11-17');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Ana Beat');
    await expect(page).toHaveTitle('Ana Beat · Asesorías · Bugalú Studio');
    await expect(dice(page, 'Ana Pérez')).toBeVisible();
    await expect(page.locator('.dir-presentacion')).toHaveText('Hola\nmundo');
    await expect(page.getByRole('link', { name: /Spotify/ })).toHaveAttribute('href', 'https://open.spotify.com/ana');
    await expect(page.getByRole('list', { name: 'Redes' }).getByText('Instagram · @ana')).toBeVisible();
    const tabla = page.getByRole('table', { name: 'Precio de una asesoría con Ana Beat' });
    await expect(tabla.getByRole('columnheader', { name: 'INCLUYE IGV (18 %)' })).toBeAttached();
    await expect(tabla).toContainText('S/ 140,00');
    const agendar = page.getByRole('button', { name: 'Agendar asesoría' });
    await expect(agendar).toHaveAttribute('aria-disabled', 'true');
    await expect(agendar).toHaveAccessibleDescription('Disponible pronto: muy pronto podrás agendar en línea desde aquí.');
    await expect(dice(page, 'SEMANA DEL 16 AL 22 NOV 2026').first()).toBeVisible();
    expect(vistasDisp[0].url.searchParams.get('desde')).toBe('2026-11-16T00:00:00-05:00');
    await expect(dice(page, 'Horario de Lima')).toBeVisible();
    await expect(page.locator('[role="grid"]')).toHaveCount(0); // solo lectura
    await expect(page.locator('bugalu-calendario button[data-inicio]')).toHaveCount(0);
    if (t.ancho > 600) {
      await expect(page.getByRole('cell', { name: /martes 17 de noviembre, 10:00, libre/i })).toBeVisible();
      await expect(page.getByRole('cell', { name: /11:00 a 12:00, OCUPADO/i })).toBeVisible();
    }
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-perfil-${t.nombre}.png`, fullPage: true });
  });
}

test('perfil: sin id y 404 muestran el perfil no disponible', async ({ page }) => {
  await perfilPublico(page, { prof: json(404, { error: { codigo: 'no_encontrado', mensaje: 'x' } }) });
  for (const url of ['/asesorias/profesional/', '/asesorias/profesional/?id=p1']) {
    await page.goto(url);
    await expect(dice(page, 'Este perfil no existe o ya no está publicado.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver el directorio' })).toHaveAttribute('href', '/asesorias/');
  }
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf15-perfil-404-1440.png' });
});

for (const [n, r] of fallosCarga) {
  test(`perfil: ${n} del perfil y del calendario`, async ({ page }) => {
    await perfilPublico(page, { prof: r });
    await page.goto('/asesorias/profesional/?id=p1');
    await expect(page.locator('.aviso-error')).toContainText(/El perfil no responde|Sin conexión|Algo salió mal al cargar el perfil/);
    await page.unroute(`${API}/profesionales/p1`).catch(() => {});
  });
  test(`perfil: si falla solo el calendario (${n}), el perfil sigue`, async ({ page }) => {
    await perfilPublico(page, { disp: r });
    await page.goto('/asesorias/profesional/?id=p1');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Ana Beat');
    await expect(page.locator('bugalu-calendario .aviso-error')).toContainText(/Los horarios no responden|Sin conexión|Algo salió mal al cargar los horarios/);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  });
}

test('perfil: horarios con 401 se repiten sin sesion y avisan', async ({ page }) => {
  await conSesion(page);
  await hoy(page);
  await silenciarApi(page);
  await simular(page, 'GET', '/profesionales/p1', json(200, PROF));
  const vistas = await simular(page, 'GET', '/profesionales/p1/disponibilidad', (r) => r.fulfill(r.request().headers().authorization ? errorApi(401, 'no_autenticado') : json(200, DISP())));
  await page.goto('/asesorias/profesional/?id=p1');
  await expect(dice(page, 'Tu sesión caducó. Inicia sesión para ver tus asesorías en el calendario.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Iniciar sesión' })).toBeVisible();
  expect(vistas.length).toBe(2);
});

test('perfil: semana sin horarios, fecha invalida y mes', async ({ page }) => {
  await perfilPublico(page, { disp: json(200, DISP({ horarios: [], ocupados: [], dias: [] })) });
  await page.goto('/asesorias/profesional/?id=p1&fecha=basura');
  await expect(dice(page, 'Aún no hay horarios publicados')).toBeVisible();
  await expect(dice(page, 'Ana Beat publica su agenda semana a semana. Mira la siguiente o vuelve pronto.')).toBeVisible();
  await expect(dice(page, 'La fecha del enlace no es válida. Te mostramos esta semana.')).toBeVisible();
  await page.getByRole('link', { name: 'MES' }).click();
  await expect(dice(page, 'NOVIEMBRE 2026').first()).toBeVisible();
});

test('perfil: el calendario de asesoria teclado: sin paradas en la cuadricula', async ({ page }) => {
  await perfilPublico(page);
  await page.goto('/asesorias/profesional/?id=p1&fecha=2026-11-17');
  await page.getByRole('link', { name: 'Volver al directorio' }).focus();
  await page.keyboard.press('Tab'); // redes (enlace externo)
  await expect(page.getByRole('link', { name: /Spotify/ })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toBeFocused();
  await page.getByRole('button', { name: 'Agendar asesoría' }).click({ force: true }); // no hace nada
  await expect(page).toHaveURL(/profesional\/\?id=p1/);
});

// ---------- Ficha del profesional ----------
async function ficha(page, { prof = json(200, { ...PROF, publicado: false, activo: false, duraciones: [] }) } = {}) {
  await hoy(page);
  await comoProfesional(page);
  await simular(page, 'GET', '/especialidades-asesoria', json(200, ESPS));
  return simular(page, 'GET', '/profesionales/p1', prof);
}

for (const t of tamanos) {
  test(`ficha: carga, falta para publicar y navegacion del profesional a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await ficha(page);
    await page.goto('/app/ficha/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/ficha pública/i);
    await expect(page.getByLabel('Nombre artístico')).toHaveValue('Ana Beat');
    await expect(page.getByLabel('Producción')).toBeChecked();
    await expect(dice(page, 'Tu perfil aún no es público. Falta: que el Administrador active tu perfil, que el Administrador fije tus precios.')).toBeVisible();
    await expect(dice(page, 'SIN PUBLICAR')).toBeVisible();
    await expect(dice(page, 'No ofreces asesorías de 1 h')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver mi perfil público' })).toBeHidden();
    await expect(page.getByRole('link', { name: 'Ficha' }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Horarios' }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Asesorías' })).toHaveCount(0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-ficha-${t.nombre}.png`, fullPage: true });
  });
}

test('ficha: guardar envia el PATCH, vacios como null, y avisa que ya esta en el directorio', async ({ page }) => {
  await ficha(page);
  let nuevo = false;
  const patches = await simular(page, 'PATCH', '/profesionales/p1', (r) => r.fulfill(json(200, { ...PROF, publicado: true })));
  await page.goto('/app/ficha/');
  await page.getByLabel('Nombre artístico').fill('');
  await page.getByRole('button', { name: 'Añadir red' }).click();
  await page.getByRole('group', { name: 'Red 3' }).getByLabel('Usuario o enlace').fill('@nueva');
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(dice(page, 'Ficha guardada. Ya está en el directorio.')).toBeVisible();
  expect(patches[0].cuerpo).toEqual({ nombre_artistico: null, presentacion: 'Hola\nmundo', redes: [{ red: 'instagram', valor: '@ana' }, { red: 'spotify', valor: 'https://open.spotify.com/ana' }, { red: 'instagram', valor: '@nueva' }], especialidades: ['e1'] });
  void nuevo;
});

test('ficha: validacion, resumen y 422 de especialidad inactiva', async ({ page }) => {
  await ficha(page);
  await simular(page, 'PATCH', '/profesionales/p1', json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'especialidades' } } }));
  await page.goto('/app/ficha/');
  await page.getByLabel('Nombre artístico').evaluate((e) => (e.value = 'x'.repeat(81))); // fill respetaria maxlength
  await page.getByLabel('Producción').uncheck();
  await page.getByRole('button', { name: 'Añadir red' }).click();
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(dice(page, /Revisa \d+ campos/)).toBeVisible();
  await expect(dice(page, 'El nombre artístico admite hasta 80 caracteres.')).toBeVisible();
  await expect(dice(page, 'Elige al menos una especialidad.')).toBeVisible();
  await expect(dice(page, 'Escribe tu usuario o el enlace.')).toBeVisible();
  await sinViolaciones(page);
  await page.getByLabel('Nombre artístico').fill('Ana');
  await page.getByLabel('Producción').check();
  await page.getByRole('group', { name: 'Red 3' }).getByLabel('Usuario o enlace').fill('@a');
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(dice(page, 'Una especialidad ya no está disponible y la quitamos. Revisa y vuelve a guardar.')).toBeVisible();
  await expect(page.getByLabel('Nombre artístico')).toHaveValue('Ana');
});

test('ficha: maximo de 5 redes', async ({ page }) => {
  await ficha(page);
  await page.goto('/app/ficha/');
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Añadir red' }).click();
  await expect(dice(page, 'Máximo 5 redes.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Añadir red' })).toBeHidden();
  await page.getByRole('button', { name: 'Quitar red 5' }).click();
  await expect(page.getByRole('button', { name: 'Añadir red' })).toBeVisible();
});

test('ficha: catalogo vacio', async ({ page }) => {
  await ficha(page);
  await simular(page, 'GET', '/especialidades-asesoria', json(200, []));
  await page.goto('/app/ficha/');
  await expect(dice(page, 'Aún no hay especialidades. El Administrador debe crearlas antes de que elijas.')).toBeVisible();
});

const fichaFallos = [
  ['401', (r) => r.fulfill(errorApi(401, 'no_autenticado')), 'Tu sesión no es válida. Inicia sesión para continuar.', 'Ir al acceso interno'],
  ['403', (r) => r.fulfill(errorApi(403, 'sin_permiso')), 'Esta sección es para los profesionales de asesoría.', 'Volver al inicio'],
  ['404', (r) => r.fulfill(errorApi(404, 'no_encontrado')), 'Tu cuenta ya no tiene ficha de profesional. Si crees que es un error, habla con el Administrador.', 'Volver al inicio'],
  ['503', (r) => r.fulfill(errorApi(503, 'x')), 'El servicio no responde. Inténtalo de nuevo en unos minutos.', 'Reintentar'],
  ['red', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.', 'Reintentar'],
  ['no-json', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>x</h1>' }), 'Algo salió mal. Inténtalo de nuevo.', 'Reintentar'],
];
for (const [n, r, texto, accion] of fichaFallos) {
  test(`ficha: ${n}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await ficha(page, { prof: r });
    await page.goto('/app/ficha/');
    await expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
    await expect(page.getByRole('main').getByText(accion, { exact: true }).first()).toBeVisible();
    if (n === '403') await expect(dice(page, '[403]')).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('ficha: un cliente sin rol de profesional ve el 403', async ({ page }) => {
  await ficha(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
  await page.goto('/app/ficha/');
  await expect(dice(page, 'Esta sección es para los profesionales de asesoría.')).toBeVisible();
});

test('ficha: foto, validacion en el navegador, subir, errores 413 y 422, y quitar', async ({ page }) => {
  await ficha(page);
  let foto = null;
  await simular(page, 'PUT', '/profesionales/p1/foto', (r) => r.fulfill(json(200, { ...PROF, foto_url: 'http://api.prueba/f.png' })));
  const quitadas = await simular(page, 'DELETE', '/profesionales/p1/foto', { status: 204 });
  await page.route('http://api.prueba/f.png', (r) => r.abort());
  await page.goto('/app/ficha/');
  const entrada = page.locator('input[type=file]');
  await entrada.setInputFiles({ name: 'grande.png', mimeType: 'image/png', buffer: Buffer.alloc(2 * 1048576 + 10) });
  await expect(dice(page, 'La foto pesa más de 2 MB. Elige una más liviana.')).toBeVisible();
  await entrada.setInputFiles({ name: 'x.gif', mimeType: 'image/gif', buffer: Buffer.alloc(10) });
  await expect(dice(page, 'Elige una foto JPG, PNG o WebP.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Subir foto' })).toBeHidden();
  await entrada.setInputFiles({ name: 'retrato.png', mimeType: 'image/png', buffer: PNG });
  await expect(page.getByRole('button', { name: 'Subir foto' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'Foto elegida: retrato.png' })).toBeAttached();
  await expect(page.getByRole('img', { name: 'Vista previa de la foto elegida' })).toBeAttached();
  await sinViolaciones(page);
  await page.getByRole('button', { name: 'Subir foto' }).click();
  await expect(dice(page, 'Foto actualizada.')).toBeVisible();
  await expect(dice(page, 'Cambiar foto')).toBeVisible();
  await page.getByRole('button', { name: 'Quitar foto' }).click();
  await expect(dice(page, 'Foto quitada. Se mostrarán tus iniciales.')).toBeVisible();
  expect(quitadas.length).toBe(1);
  void foto;
});

test('ficha: 413 y 422 del servidor al subir', async ({ page }) => {
  await ficha(page);
  let n = 0;
  await simular(page, 'PUT', '/profesionales/p1/foto', (r) => r.fulfill(++n === 1 ? errorApi(413, 'archivo_muy_grande') : errorApi(422, 'formato_no_admitido')));
  await page.goto('/app/ficha/');
  const entrada = page.locator('input[type=file]');
  await entrada.setInputFiles({ name: 'a.png', mimeType: 'image/png', buffer: Buffer.alloc(100) });
  await page.getByRole('button', { name: 'Subir foto' }).click();
  await expect(dice(page, 'La foto pesa más de 2 MB. Elige una más liviana.')).toBeVisible();
  await entrada.setInputFiles({ name: 'b.png', mimeType: 'image/png', buffer: Buffer.alloc(100) });
  await page.getByRole('button', { name: 'Subir foto' }).click();
  await expect(dice(page, 'Elige una foto JPG, PNG o WebP.')).toBeVisible();
});

test.describe('sin JS (app)', () => {
  test.use({ javaScriptEnabled: false });
  test('ficha, horarios y administracion avisan', async ({ page }) => {
    for (const ruta of ['/app/ficha/', '/app/horarios/', '/app/asesorias/', '/app/asesorias/especialidades', '/app/asesorias/profesional?id=p1']) {
      await page.goto(ruta);
      expect(await page.content()).toContain('Esta sección necesita JavaScript');
    }
  });
});

// ---------- Horarios ----------
const SEMANA = '2026-W47';
async function horarios(page, { disp = json(200, DISP({ horarios: [], ocupados: [], dias: [] })), sug = json(200, [{ inicio: '2026-11-17T10:00:00-05:00', fin: '2026-11-17T12:00:00-05:00' }]) } = {}) {
  await hoy(page);
  await comoProfesional(page);
  await simular(page, 'GET', '/profesionales/p1', json(200, { ...PROF, publicado: false }));
  const vistas = await simular(page, 'GET', '/profesionales/p1/disponibilidad', disp);
  await simular(page, 'GET', '/profesionales/p1/horarios/sugerencia', sug);
  return vistas;
}

for (const t of tamanos) {
  test(`horarios: semana con bloques y sin publicar a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await horarios(page, { disp: json(200, DISP({ ocupados: [{ inicio: '2026-11-17T11:00:00-05:00', fin: '2026-11-17T12:00:00-05:00', propia: false }] })) });
    await page.goto(`/app/horarios/?semana=${SEMANA}`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/mis horarios/i);
    await expect(dice(page, 'SEMANA DEL 16 AL 22 NOV 2026')).toBeVisible();
    await expect(dice(page, 'Tu perfil aún no es público: los artistas no verán estos horarios hasta que lo sea.')).toBeVisible();
    const fila = page.getByRole('table', { name: 'Horarios publicados' }).getByRole('row').nth(1);
    await expect(fila).toContainText('MAR 17 NOV');
    await expect(fila).toContainText('10:00–13:00');
    await expect(fila).toContainText('1 asesoría');
    const bloqueado = page.getByRole('button', { name: 'Retirar bloque del martes 17 de 10:00 a 13:00' });
    await expect(bloqueado).toHaveAttribute('aria-disabled', 'true');
    await expect(bloqueado).toHaveAccessibleDescription('Tiene asesorías agendadas');
    await expect(page.getByRole('link', { name: 'Semana anterior' })).toHaveAttribute('href', '/app/horarios/?semana=2026-W46');
    await expect(dice(page, 'Para sumar horas, añade bloques y publícalos.')).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-horarios-${t.nombre}.png`, fullPage: true });
  });
}

test('horarios: sugerencia, publicar, y 409 solapado conserva las filas', async ({ page }) => {
  await horarios(page);
  let n = 0;
  const posts = await simular(page, 'POST', '/profesionales/p1/horarios', (r) => r.fulfill(++n === 1 ? errorApi(409, 'horario_solapado') : json(201, [])));
  await page.goto(`/app/horarios/?semana=${SEMANA}`);
  await expect(dice(page, 'No hay horarios publicados esta semana')).toBeVisible();
  await expect(dice(page, 'Te proponemos tu última semana publicada. Cambia lo que haga falta antes de publicar.')).toBeVisible();
  const martes = page.getByRole('group', { name: 'MARTES 17 NOV' });
  await expect(martes.getByLabel('Desde')).toHaveValue('10:00');
  await martes.getByRole('button', { name: 'Añadir bloque al martes' }).click();
  await expect(martes.getByLabel('Desde').nth(1)).toBeFocused();
  await martes.getByLabel('Desde').nth(1).fill('11:00');
  await martes.getByLabel('Hasta').nth(1).fill('13:00');
  await page.getByRole('button', { name: 'Publicar horarios' }).click();
  await expect(dice(page, 'Se cruza con el bloque de 10:00–12:00 del mismo día.')).toBeVisible();
  await expect(dice(page, /Revisa \d+ bloques?/)).toBeVisible();
  await martes.getByLabel('Desde').nth(1).fill('12:00');
  await page.getByRole('button', { name: 'Publicar horarios' }).click();
  await expect(dice(page, 'Uno de los bloques se cruza con otro ya publicado. Revisa las horas y vuelve a publicar.')).toBeVisible();
  await expect(martes.getByLabel('Desde').nth(1)).toHaveValue('12:00');
  await page.getByRole('button', { name: 'Publicar horarios' }).click();
  await expect(dice(page, 'Horarios publicados.')).toBeVisible();
  expect(posts[1].cuerpo).toEqual({ horarios: [{ inicio: '2026-11-17T10:00:00-05:00', fin: '2026-11-17T12:00:00-05:00' }, { inicio: '2026-11-17T12:00:00-05:00', fin: '2026-11-17T13:00:00-05:00' }] });
  await sinViolaciones(page);
});

test('horarios: hora pasada, quitar devuelve el foco, sin sugerencia y semana pasada', async ({ page }) => {
  await horarios(page, { sug: json(200, []) });
  await page.goto('/app/horarios/?semana=2026-W45');
  await expect(dice(page, 'Esta semana ya pasó.')).toBeVisible();
  await page.goto('/app/horarios/?semana=2026-W46'); // la semana de hoy: solo queda el domingo 15
  await expect(dice(page, 'No hay una semana anterior que copiar. Añade los bloques de cada día.')).toBeVisible();
  const domingo = page.getByRole('group', { name: 'DOMINGO 15 NOV' });
  await domingo.getByRole('button', { name: 'Añadir bloque al domingo' }).click();
  await domingo.getByLabel('Desde').fill('08:00');
  await domingo.getByLabel('Hasta').fill('09:00');
  await page.getByRole('button', { name: 'Publicar horarios' }).click();
  await expect(dice(page, 'Esa hora ya pasó. Elige una hora futura.')).toBeVisible();
  await page.getByRole('button', { name: 'Quitar bloque de 08:00 a 09:00 del domingo' }).click();
  await expect(domingo.getByRole('button', { name: 'Añadir bloque al domingo' })).toBeFocused();
  await page.getByRole('button', { name: 'Publicar horarios' }).click();
  await expect(dice(page, 'Añade al menos un bloque')).toBeVisible();
});

test('horarios: retirar, 409 con asesorias y bloque inexistente', async ({ page }) => {
  await horarios(page, { disp: json(200, DISP({ ocupados: [] })) });
  let n = 0;
  await simular(page, 'DELETE', '/profesionales/p1/horarios/h1', (r) => {
    n++;
    return r.fulfill(n === 1 ? json(409, { error: { codigo: 'horario_con_asesorias', mensaje: 'x', detalles: { asesorias: [{ id: 'a1', folio: 'A-2026-00001', inicio: '2026-11-17T11:00:00-05:00' }] } } }) : n === 2 ? errorApi(404, 'no_encontrado') : { status: 204 });
  });
  await page.goto(`/app/horarios/?semana=${SEMANA}`);
  const retirar = page.getByRole('button', { name: /Retirar bloque del martes 17/ });
  await retirar.click();
  await expect(dice(page, 'Este bloque tiene asesorías agendadas. Pide al Administrador que las cancele o reprograme antes de retirarlo.')).toBeVisible();
  await expect(dice(page, 'A-2026-00001 · 17 nov, 11:00')).toBeVisible();
  await retirar.click();
  await expect(dice(page, 'Ese bloque ya no existe. Actualizamos la semana.')).toBeVisible();
  await retirar.click();
  await expect(dice(page, 'Bloque retirado.')).toBeVisible();
});

test('horarios: semana invalida y 422 rango', async ({ page }) => {
  await horarios(page);
  await page.goto('/app/horarios/?semana=basura');
  await expect(dice(page, 'La semana del enlace no es válida. Te mostramos esta semana.')).toBeVisible();
});

for (const [n, r, texto] of fichaFallos.filter(([n]) => n !== '404')) {
  test(`horarios: ${n}`, async ({ page }) => {
    await horarios(page, { disp: r });
    await page.goto(`/app/horarios/?semana=${SEMANA}`);
    await expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
  });
}

// ---------- Administracion ----------
const FILA = (p, extra = {}) => ({ ...p, activo: true, publicado: true, ...extra });
async function admin(page) {
  await hoy(page);
  await comoAdministrador(page);
}

for (const t of tamanos) {
  test(`admin: lista de profesionales a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await admin(page);
    await simular(page, 'GET', '/profesionales', json(200, [FILA(PROF), FILA(OTRO, { activo: false, publicado: false, duraciones: [] }), FILA({ ...OTRO, id: 'p3', nombre: 'Eva Soto', duraciones: [] }, { publicado: false })]));
    await page.goto('/app/asesorias/?aviso=profesional-asignado');
    await expect(dice(page, 'Rol asignado. Completa su ficha y fija sus precios para publicarlo.')).toBeVisible();
    const filas = page.getByRole('table', { name: 'Profesionales' }).getByRole('row');
    await expect(filas).toHaveCount(4);
    await expect(filas.nth(1)).toContainText('PUBLICADO');
    await expect(filas.nth(1)).toContainText('S/ 140,00');
    await expect(filas.nth(2)).toContainText('INACTIVO');
    await expect(filas.nth(3)).toContainText('SIN PUBLICAR');
    await expect(page.getByRole('link', { name: 'Editar ficha de Ana Beat' })).toHaveAttribute('href', '/app/asesorias/profesional?id=p1');
    await expect(page.getByRole('link', { name: 'Horarios de Ana Beat' })).toHaveAttribute('href', '/app/asesorias/horarios?id=p1');
    if (t.ancho > 600) await expect(page.getByRole('link', { name: 'Asesorías' }).first()).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-admin-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('admin: lista vacia, crear mi ficha (201, 409 perfil_existente, 422)', async ({ page }) => {
  await admin(page);
  await simular(page, 'GET', '/profesionales', json(200, []));
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ id: 'adm1', rol: 'administrador' })));
  let n = 0;
  const posts = await simular(page, 'POST', '/profesionales', (r) => r.fulfill(++n === 1 ? errorApi(409, 'perfil_existente') : n === 2 ? errorApi(422, 'rol_no_admitido') : json(201, { ...PROF, id: 'adm1' })));
  await simular(page, 'GET', '/profesionales/adm1', json(200, { ...PROF, id: 'adm1', publicado: false }));
  await simular(page, 'GET', '/especialidades-asesoria', json(200, ESPS));
  await page.goto('/app/asesorias/');
  await expect(dice(page, 'Aún no hay profesionales')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Asignar rol de profesional' }).last()).toBeVisible();
  await sinViolaciones(page);
  const crear = page.getByRole('button', { name: 'Crear mi ficha', exact: true });
  await crear.click();
  await expect(dice(page, 'Ya tienes una ficha de profesional')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Editar mi ficha' })).toHaveAttribute('href', '/app/asesorias/profesional?id=adm1');
  await crear.click();
  await expect(dice(page, 'Solo una cuenta de Administrador o de profesional puede tener ficha.')).toBeVisible();
  await crear.click();
  await expect(page).toHaveURL(/profesional\?id=adm1/);
  expect(posts[2].cuerpo).toEqual({ id_usuario: 'adm1' });
});

test('admin: Crear mi ficha esta en la cabecera y solo se ve si aun no hay ficha propia', async ({ page }) => {
  await admin(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ id: 'adm1', rol: 'administrador' })));
  await simular(page, 'GET', '/profesionales', json(200, [FILA(PROF)]));
  await page.goto('/app/asesorias/');
  const crear = page.locator('.encabezado-acciones').getByRole('button', { name: 'Crear mi ficha', exact: true });
  await expect(crear).toBeVisible();
  await page.screenshot({ path: 'pruebas/capturas/rf15-admin-crear-ficha-1440.png', fullPage: true });
  await sinViolaciones(page);
  const con = await page.context().newPage();
  await admin(con);
  await con.route(`${API}/perfil`, (r) => r.fulfill(perfil({ id: 'p1', rol: 'administrador' })));
  await simular(con, 'GET', '/profesionales', json(200, [FILA(PROF)]));
  await con.goto('/app/asesorias/');
  await expect(con.getByRole('table', { name: 'Profesionales' })).toBeVisible();
  await expect(con.getByRole('button', { name: 'Crear mi ficha', exact: true })).toBeHidden();
});

test('profesional sin nombre ni nombre artistico se muestra como "Profesional"', async ({ page }) => {
  await admin(page);
  const SIN = { ...PROF, id: 'p9', nombre: undefined, nombre_artistico: null };
  await simular(page, 'GET', '/profesionales', json(200, [FILA(SIN)]));
  await simular(page, 'GET', '/profesionales/p9', json(200, SIN));
  await simular(page, 'GET', '/especialidades-asesoria', json(200, ESPS));
  await simular(page, 'GET', '/impuestos', IMPUESTOS);
  await page.goto('/app/asesorias/');
  await expect(page.getByRole('link', { name: 'Editar ficha de Profesional' })).toBeVisible();
  await page.goto('/app/asesorias/profesional?id=p9');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/ficha de profesional/i);
  await expect(page.locator('body')).not.toContainText('undefined');
  await directorio(page, { lista: json(200, [SIN]) });
  await page.goto('/asesorias/');
  await expect(page.locator('[data-mostrado]').first()).toHaveText('Profesional');
  await simular(page, 'GET', '/profesionales/p9', json(200, SIN));
  await page.goto('/asesorias/profesional/?id=p9');
  await expect(page).toHaveTitle(/^Profesional ·/);
  await expect(page.locator('body')).not.toContainText('undefined');
});

test('admin ficha: sin especialidades marcadas no se envia nada y da el error de 1 a 5', async ({ page }) => {
  await fichaAdmin(page);
  const patches = await simular(page, 'PATCH', '/profesionales/p1', json(200, PROF));
  await page.goto('/app/asesorias/profesional?id=p1');
  await page.getByLabel('Producción').uncheck();
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(dice(page, 'Elige al menos una especialidad.')).toBeVisible();
  expect(patches).toHaveLength(0);
});

test('inicio: el profesional no ve destinos de cliente ni de personal', async ({ page }) => {
  await comoProfesional(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/app/');
  await expect(page.locator('.app-nav-lateral').getByRole('link', { name: 'Ficha' })).toBeVisible();
  const visibles = await page.locator('main a:visible, .app-nav-lateral a:visible, .app-nav-tactil a:visible').evaluateAll((a) => a.map((x) => x.getAttribute('href')));
  for (const ruta of ['/app/reservas/', '/app/agenda/', '/app/pagos/', '/app/reclamos/', '/app/usuarios/', '/app/asesorias/']) expect(visibles).not.toContain(ruta);
});

for (const [n, r, texto] of [['401', fichaFallos[0][1], fichaFallos[0][2]], ['403', fichaFallos[1][1], 'Esta sección es solo para el Administrador.'], ...fichaFallos.slice(3).map(([a, b, c]) => [a, b, c])]) {
  test(`admin: lista ${n}`, async ({ page }) => {
    await admin(page);
    await simular(page, 'GET', '/profesionales', r);
    await page.goto('/app/asesorias/');
    await expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
  });
}

test('admin: especialidades, crear, 409, renombrar, desactivar y activar', async ({ page }) => {
  const consola = vigilarConsola(page);
  await admin(page);
  let catalogo = [{ id: 'e1', nombre: 'Producción', activa: true }];
  await simular(page, 'GET', '/especialidades-asesoria', (r) => r.fulfill(json(200, catalogo)));
  const posts = await simular(page, 'POST', '/especialidades-asesoria', (r) => {
    const { nombre } = r.request().postDataJSON();
    if (nombre === 'produccion') return r.fulfill(errorApi(409, 'especialidad_duplicada'));
    catalogo = [...catalogo, { id: 'e2', nombre, activa: true }];
    return r.fulfill(json(201, catalogo[1]));
  });
  const patches = await simular(page, 'PATCH', '/especialidades-asesoria/e2', (r) => {
    const c = r.request().postDataJSON();
    catalogo = catalogo.map((e) => (e.id === 'e2' ? { ...e, ...c } : e));
    return r.fulfill(json(200, catalogo[1]));
  });
  await page.goto('/app/asesorias/especialidades');
  await expect(dice(page, 'ACTIVA')).toBeVisible();
  await page.screenshot({ path: 'pruebas/capturas/rf15-admin-especialidades-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Crear especialidad' }).click();
  await expect(dice(page, 'Escribe el nombre.').first()).toBeVisible();
  await page.getByLabel('Nombre').fill('produccion');
  await page.getByRole('button', { name: 'Crear especialidad' }).click();
  await expect(dice(page, 'Ya existe una especialidad con ese nombre (sin contar mayúsculas ni tildes).').first()).toBeVisible();
  await page.getByLabel('Nombre').fill('Coros');
  await page.getByRole('button', { name: 'Crear especialidad' }).click();
  await expect(dice(page, 'Especialidad creada.')).toBeVisible();
  expect(posts.at(-1).cuerpo).toEqual({ nombre: 'Coros' });
  await page.getByRole('link', { name: 'Renombrar Coros' }).click();
  await expect(page).toHaveURL(/editar=e2/);
  await expect(page.getByLabel('Nombre')).toBeFocused();
  await expect(page.getByLabel('Nombre')).toHaveValue('Coros');
  await sinViolaciones(page);
  await page.getByLabel('Nombre').fill('Coros y voces');
  await page.getByRole('button', { name: 'Guardar nombre' }).click();
  await expect(dice(page, 'Nombre guardado.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Renombrar Coros y voces' })).toBeFocused();
  await page.getByRole('button', { name: 'Desactivar Coros y voces' }).click();
  await expect(dice(page, 'Coros y voces desactivada: ya no se muestra en perfiles ni filtros.')).toBeVisible();
  await expect(dice(page, 'INACTIVA')).toBeVisible();
  await page.getByRole('button', { name: 'Activar Coros y voces' }).click();
  await expect(dice(page, 'Coros y voces activada.')).toBeVisible();
  expect(patches.map((p) => p.cuerpo)).toEqual([{ nombre: 'Coros y voces' }, { activa: false }, { activa: true }]);
  await page.goto('/app/asesorias/especialidades?editar=zzz');
  await expect(dice(page, 'Esa especialidad ya no existe. Actualizamos la lista.')).toBeVisible();
  expect(consola).toEqual([]);
});

test('admin: especialidades vacio y 422', async ({ page }) => {
  await admin(page);
  await simular(page, 'GET', '/especialidades-asesoria', json(200, []));
  await simular(page, 'POST', '/especialidades-asesoria', errorApi(422, 'datos_invalidos'));
  await page.goto('/app/asesorias/especialidades');
  await expect(dice(page, 'Aún no hay especialidades')).toBeVisible();
  await page.getByLabel('Nombre').fill('ab');
  await page.getByRole('button', { name: 'Crear especialidad' }).click();
  await expect(dice(page, 'Usa de 2 a 60 caracteres.').first()).toBeVisible();
});

const IMPUESTOS = json(200, { porcentaje_igv: '18.00', precios_incluyen_igv: true });
const PREVIA = { token: 't1', expira_en: '2026-11-15T15:10:00Z', palabra: 'CONFIRMAR', recurso: 'profesional', id_recurso: 'p1', nombre_recurso: 'Ana Beat', cambios: [{ campo: 'precio_30', anterior: '80.00', nuevo: '90.00' }, { campo: 'precio_60', anterior: '140.00', nuevo: 'no_ofrece' }], impacto: { operaciones_vigentes: 0, ejemplos: [{ concepto: 'Asesoría de 30 min', tipo: 'importe', antes: '80.00', despues: '90.00' }] } };
async function fichaAdmin(page) {
  await admin(page);
  await simular(page, 'GET', '/profesionales/p1', json(200, PROF));
  await simular(page, 'GET', '/especialidades-asesoria', json(200, ESPS));
  await simular(page, 'GET', '/impuestos', IMPUESTOS);
}

test('admin ficha: estado y precios, validacion y flujo con barreras', async ({ page }) => {
  const consola = vigilarConsola(page);
  await fichaAdmin(page);
  // El mock rechaza la forma vieja (precio_30 / texto no_ofrece) con 422, como el backend (extra="forbid").
  const previas = await simular(page, 'POST', '/cambios-sensibles/previsualizar', (r) => {
    const { cambios } = r.request().postDataJSON();
    const valido = Object.keys(cambios).join() === 'precios' && Object.values(cambios.precios).every((v) => v === null || typeof v === 'number');
    return r.fulfill(valido ? json(200, PREVIA) : errorApi(422, 'datos_invalidos'));
  });
  const confirmaciones = await simular(page, 'POST', '/cambios-sensibles/confirmar', json(200, { recurso: 'profesional', id_recurso: 'p1', valor: {}, cambios: [] }));
  const patches = await simular(page, 'PATCH', '/profesionales/p1', json(200, PROF));
  await page.goto('/app/asesorias/profesional?id=p1');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/ficha de ana beat/i);
  await expect(page.getByLabel('Activo')).toBeChecked();
  await expect(page.getByLabel('Precio 30 min (S/)')).toHaveValue('80,00');
  await expect(dice(page, 'Lo que paga el cliente, con IGV (18 %) incluido.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Horarios de Ana Beat' })).toHaveAttribute('href', '/app/asesorias/horarios?id=p1');
  await expect(dice(page, 'Los precios valen para las asesorías nuevas; las ya agendadas guardan el suyo.')).toBeVisible();
  await page.screenshot({ path: 'pruebas/capturas/rf15-admin-ficha-1440.png', fullPage: true });
  await page.getByLabel('Precio 30 min (S/)').fill('0');
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(dice(page, 'Escribe un importe mayor que 0, con hasta dos decimales, como 80,00.')).toBeVisible();
  await page.getByLabel('Precio 30 min (S/)').fill('90');
  await page.getByLabel('Precio 1 h (S/)').fill('');
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(previas[0].cuerpo).toEqual({ recurso: 'profesional', id_recurso: 'p1', cambios: { precios: { 30: 90, 60: null } } });
  await expect(page.getByRole('rowheader', { name: 'PRECIO 1 H' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'No ofrece' })).toBeVisible();
  await expect(dice(page, 'Se aplica solo a asesorías nuevas. 0 asesorías vigentes conservan sus condiciones.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf15-admin-revision-1440.png', fullPage: true });
  await page.getByLabel('Escribe CONFIRMAR').fill('CONFIRMAR');
  await page.getByRole('button', { name: 'Aplicar cambio' }).click();
  await expect(dice(page, 'Ficha de Ana Beat guardada.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=profesional');
  expect(confirmaciones[0].cuerpo).toEqual({ token: 't1', palabra: 'CONFIRMAR' });
  expect(patches[0].cuerpo.activo).toBe(true);
  expect(patches[0].cuerpo.precios).toBeUndefined();
  expect(consola).toEqual([]);
});

test('admin ficha: sin precios cambiados un 428 abre la misma revision', async ({ page }) => {
  await fichaAdmin(page);
  let n = 0;
  const previas = await simular(page, 'POST', '/cambios-sensibles/previsualizar', json(200, PREVIA));
  await simular(page, 'PATCH', '/profesionales/p1', (r) => r.fulfill(++n === 1 ? json(428, { error: { codigo: 'confirmacion_requerida', mensaje: 'x', detalles: { campos: ['precio_30'] } } }) : json(200, PROF)));
  await page.goto('/app/asesorias/profesional?id=p1');
  await page.getByLabel('Nombre artístico').fill('Ana B');
  await page.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(previas[0].cuerpo.cambios).toEqual({ precios: { 30: 80 } });
  await page.getByRole('button', { name: 'Cancelar' }).click();
  await expect(dice(page, 'No se aplicó ningún cambio.')).toBeVisible();
});

test('admin ficha: activar sin precio queda sin publicar; 404 y 403', async ({ page }) => {
  await admin(page);
  await simular(page, 'GET', '/profesionales/p1', json(200, { ...PROF, activo: true, publicado: false, duraciones: [], especialidades: [] }));
  await simular(page, 'GET', '/especialidades-asesoria', json(200, ESPS));
  await simular(page, 'GET', '/impuestos', IMPUESTOS);
  await page.goto('/app/asesorias/profesional?id=p1');
  await expect(dice(page, 'El perfil de Ana Beat aún no es público. Falta: que elija al menos una especialidad, fijar sus precios.')).toBeVisible();
  await page.goto('/app/asesorias/profesional');
  await expect(dice(page, 'No encontramos a este profesional.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a profesionales' }).last()).toHaveAttribute('href', '/app/asesorias/');
});

test('admin horarios: por el profesional, con su nombre y su ficha', async ({ page }) => {
  await admin(page);
  await simular(page, 'GET', '/profesionales/p1', json(200, PROF));
  await simular(page, 'GET', '/profesionales/p1/disponibilidad', json(200, DISP()));
  await simular(page, 'GET', '/profesionales/p1/horarios/sugerencia', json(200, []));
  await page.goto('/app/asesorias/horarios?id=p1&semana=2026-W47');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/horarios de ana beat/i);
  await expect(page.getByRole('link', { name: 'Volver a la ficha de Ana Beat' })).toHaveAttribute('href', '/app/asesorias/profesional?id=p1');
  await expect(page.getByRole('link', { name: 'Semana siguiente' })).toHaveAttribute('href', '/app/asesorias/horarios?id=p1&semana=2026-W48');
  await sinViolaciones(page);
});

// ---------- Usuarios y navegacion ----------
const U9 = '00000000-0000-4000-8000-000000000009';
const U8 = '00000000-0000-4000-8000-000000000008';
const USUARIO = { id: U9, nombre: 'Eva Soto', correo: 'eva@correo.com', rol: 'personal', especialidad: 'Mezcla', documento: null };
async function usuarios(page) {
  await admin(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ id: 'adm1', rol: 'administrador' })));
  await simular(page, 'GET', '/usuarios', json(200, [USUARIO, { ...USUARIO, id: U8, nombre: 'Nico Ruiz', rol: 'profesional' }]));
  await simular(page, 'GET', `/usuarios/${U9}/aceptaciones`, json(200, []));
}

test('usuarios: filtro Profesionales y opcion Profesional artistico', async ({ page }) => {
  await usuarios(page);
  const patches = await simular(page, 'PATCH', `/usuarios/${U9}`, json(200, { ...USUARIO, rol: 'profesional' }));
  await page.goto('/app/usuarios?rol=profesional');
  await expect(page.getByRole('link', { name: 'Profesionales' }).first()).toHaveAttribute('aria-current', 'true');
  await page.goto(`/app/usuarios/editar?id=${U9}`);
  await expect(page.getByRole('textbox', { name: 'Especialidad' })).toBeVisible();
  await page.getByLabel('Profesional artístico').check();
  await expect(dice(page, 'Da asesorías y publica sus horarios. Entra con correo y contraseña.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Especialidad' })).toBeHidden();
  await sinViolaciones(page);
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await expect(page).toHaveURL(/\/app\/asesorias\/\?aviso=profesional-asignado|\/app\/asesorias\/$/);
  expect(patches[0].cuerpo).toEqual({ rol: 'profesional' });
});

test('usuarios: 409 profesional_con_asesorias conserva los datos', async ({ page }) => {
  await usuarios(page);
  await simular(page, 'PATCH', `/usuarios/${U8}`, errorApi(409, 'profesional_con_asesorias'));
  await page.goto(`/app/usuarios/editar?id=${U8}`);
  await expect(page.getByLabel('Profesional artístico')).toBeChecked();
  await page.getByLabel('Personal del estudio').check();
  await page.getByRole('textbox', { name: 'Especialidad' }).fill('Mezcla');
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await expect(dice(page, 'Nico Ruiz tiene asesorías pendientes o confirmadas. Cancélalas o espera a que terminen antes de quitarle el rol.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Especialidad' })).toHaveValue('Mezcla');
});

test('usuarios: 409 cliente_con_operaciones conserva los datos', async ({ page }) => {
  await usuarios(page);
  await simular(page, 'PATCH', `/usuarios/${U9}`, errorApi(409, 'cliente_con_operaciones'));
  await page.goto(`/app/usuarios/editar?id=${U9}`);
  await page.getByLabel('Profesional artístico').check();
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await expect(dice(page, 'Eva Soto tiene reservas, créditos, pagos o devoluciones vivos')).toBeVisible();
  await expect(dice(page, 'Espera a que terminen o resuélvelos antes de asignarle el rol de profesional.')).toBeVisible();
  await expect(page.getByLabel('Profesional artístico')).toBeChecked();
});

test('navegacion: cada rol ve sus destinos de asesorias', async ({ page }) => {
  await hoy(page);
  await comoAdministrador(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/app/');
  const lateral = page.locator('.app-nav-lateral');
  await expect(lateral.getByRole('link', { name: 'Asesorías' })).toBeVisible();
  await expect(lateral.getByRole('link', { name: 'Ficha' })).toBeHidden();
  const p = await page.context().newPage();
  await comoProfesional(p);
  await p.setViewportSize({ width: 390, height: 844 });
  await p.goto('/app/');
  const tactil = p.locator('.app-nav-tactil');
  await expect(tactil.getByRole('link', { name: 'Ficha' })).toBeVisible();
  await expect(tactil.getByRole('link', { name: 'Horarios' })).toBeVisible();
  await expect(tactil.getByRole('link', { name: 'Asesorías' })).toBeHidden();
});

test('catalogo: avatar, tarjeta de profesional y foto de perfil', async ({ page }) => {
  await page.goto('/catalogo');
  await expect(page.getByRole('heading', { name: 'Tarjeta de profesional' })).toBeVisible();
  await expect(page.getByRole('link', { name: /^Ana Beat ?, ver perfil$/ })).toBeVisible();
  await sinViolaciones(page);
  for (const t of tamanos) {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await page.locator('#g-tarjeta-profesional').screenshot({ path: `pruebas/capturas/rf15-tarjeta-${t.nombre}.png` });
  }
});
