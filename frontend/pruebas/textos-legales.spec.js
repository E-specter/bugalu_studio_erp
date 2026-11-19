// RF-17 (CA-01, CA-02, CA-14 y decision 4): textos legales publicos, administracion de versiones y documentos repetidos. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos, API, perfil } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const LISTA = [
  { tipo: 'terminos_uso', version: '1.0.0', tipo_cambio: 'mayor', vigente_desde: '2026-12-01T00:00:00-05:00', resumenes: { registro: 'Reglas de uso.' }, programada: false },
  { tipo: 'terminos_uso', version: '1.1.0', tipo_cambio: 'menor', vigente_desde: '2026-12-15T00:00:00-05:00', resumenes: { registro: 'Reglas de uso, con aclaraciones.' }, programada: true },
  { tipo: 'politica_privacidad', version: '1.2.3', tipo_cambio: 'parche', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes: { pago: 'Cómo tratamos tus datos.' }, programada: false },
];
const HTML = '<h2>Quiénes somos</h2><p>Aural Perú E.I.R.L. <a href="https://bugalu.studio">sitio</a></p><ul><li>Uno</li><li>Dos</li></ul>';
const texto = (extra = {}) => ({ ...LISTA[0], contenido: '## Quiénes somos', contenido_html: HTML, publicado_en: '2026-11-10T10:00:00-05:00', resumen_cambios: null, ...extra });
const HOY = new Date('2026-11-15T15:00:00Z'); // domingo 15 nov 2026, Lima

async function publica(page, { lista = json(200, LISTA), version = (r) => r.fulfill(json(200, texto())) } = {}) {
  await page.clock.setFixedTime(HOY);
  await page.route(`${API}/**`, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
  const vistas = { lista: await simular(page, 'GET', '/textos-legales', lista) };
  vistas.versiones = [];
  await page.route((u) => /^\/api\/v1\/textos-legales\/[^/]+\/versiones\/[^/]+$/.test(u.pathname), (r) => {
    vistas.versiones.push(new URL(r.request().url()).pathname);
    return version(r);
  });
  return vistas;
}

// --- 1. Pagina publica de un texto ---
for (const t of tamanos) {
  test(`publico: texto vigente con version, resumen, prosa y pie a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await publica(page);
    await page.goto('/legal/terminos-de-uso/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^términos de uso$/i);
    await expect(page.getByText('VERSIÓN 1.0.0 · VIGENTE DESDE 1 DIC 2026')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /en pocas palabras/i })).toBeVisible();
    await expect(page.getByText('Reglas de uso.', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'Quiénes somos' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'sitio' })).toHaveAttribute('href', 'https://bugalu.studio');
    // Hay una programada: aviso antes del resumen.
    await expect(page.getByText('Desde el 15 dic 2026 rige la versión 1.1.0.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Leer la versión 1.1.0' })).toHaveAttribute('href', '/legal/terminos-de-uso/?version=1.1.0');
    expect(vistas.versiones).toEqual(['/api/v1/textos-legales/terminos_uso/versiones/1.0.0']);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    // Pie publico completo.
    const pie = page.getByRole('contentinfo');
    await expect(pie.getByRole('navigation', { name: 'Legal' }).getByRole('link')).toHaveText(['Términos de uso', 'Política de privacidad', 'Condiciones de contratación', 'Textos legales', 'Libro de Reclamaciones']);
    await expect(pie.getByRole('link', { name: 'Libro de Reclamaciones' })).toHaveAttribute('href', '/libro-de-reclamaciones/');
    await expect(pie).toContainText('RUC 20615656128');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/textos-legales-publico-${t.nombre}.png`, fullPage: true });
  });
}

test('publico: una version antigua avisa y enlaza a la vigente', async ({ page }) => {
  const vistas = await publica(page, { version: (r) => r.fulfill(json(200, texto({ version: '0.9.0', vigente_desde: '2026-10-01T00:00:00-05:00' }))) });
  await page.goto('/legal/terminos-de-uso/?version=0.9.0');
  await expect(page.getByText('VERSIÓN 0.9.0 · VIGENTE DESDE 1 OCT 2026')).toBeVisible();
  await expect(page.getByText('Estás leyendo la versión 0.9.0, que ya no está vigente.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Leer la versión vigente (1.0.0)' })).toHaveAttribute('href', '/legal/terminos-de-uso/');
  expect(vistas.versiones).toEqual(['/api/v1/textos-legales/terminos_uso/versiones/0.9.0']);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/textos-legales-antigua-1440.png', fullPage: true });
});

test('publico: sin programada no hay aviso', async ({ page }) => {
  await publica(page, { lista: json(200, [LISTA[0]]) });
  await page.goto('/legal/terminos-de-uso/');
  await expect(ver(page, 'VERSIÓN 1.0.0')).toBeVisible();
  await expect(page.locator('.aviso')).toHaveCount(0);
});

test('publico: version inexistente es 404 de la vista, con enlace a la vigente', async ({ page }) => {
  const consola = vigilarConsola(page);
  await publica(page, { version: (r) => r.fulfill(errorApi(404, 'no_encontrado')) });
  await page.goto('/legal/terminos-de-uso/?version=9.9.9');
  await expect(page.getByText('No existe la versión 9.9.9 de este texto.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Leer la versión vigente' })).toHaveAttribute('href', '/legal/terminos-de-uso/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  expect(await page.locator('[data-salida] > .aviso').evaluate((e) => getComputedStyle(e).maxWidth)).not.toBe('none'); // N6: el aviso de estado respeta la medida de lectura
  await page.screenshot({ path: 'pruebas/capturas/textos-legales-404-1440.png', fullPage: true });
});

test('publico: una version mal escrita ni siquiera llega a la API', async ({ page }) => {
  const vistas = await publica(page);
  await page.goto('/legal/terminos-de-uso/?version=../../perfil');
  await expect(ver(page, 'No existe la versión')).toBeVisible();
  expect(vistas.versiones).toEqual([]);
});

test('publico: texto sin version publicada', async ({ page }) => {
  await publica(page);
  await page.goto('/legal/condiciones-de-contratacion/');
  await expect(ver(page, 'Este texto aún no está publicado.')).toBeVisible();
  await sinViolaciones(page);
});

test('publico: el contenido no ejecuta scripts ni atributos de evento aunque lleguen', async ({ page }) => {
  const sucio = '<h2>Ok</h2><script>window.__xss = 1</script><img src="x" onerror="window.__xss = 2"><a href="javascript:window.__xss=3">mal</a>';
  await publica(page, { version: (r) => r.fulfill(json(200, texto({ contenido_html: sucio }))) });
  await page.goto('/legal/terminos-de-uso/');
  await expect(page.getByRole('heading', { level: 2, name: 'Ok' })).toBeVisible();
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  await expect(page.locator('.prosa script')).toHaveCount(0);
  await expect(page.locator('.prosa [onerror]')).toHaveCount(0);
  await expect(page.locator('.prosa a[href^="javascript"]')).toHaveCount(0);
});

test('publico: el saneado del navegador deja solo atributos permitidos y rutas propias', async ({ page }) => {
  const sucio = [
    '<h2>Ok</h2>',
    '<p id="a" name="b" style="position:fixed" title="t" class="x" data-k="1">párrafo</p>',
    '<button formaction="https://mal.example" form="f">botón</button>',
    '<img src="https://bugalu.studio/a.png" srcset="https://mal.example/a.png 2x" alt="logo" onerror="window.__xss = 1">',
    '<a href="https://bugalu.studio/x" ping="https://mal.example/p" target="_blank" rel="x">fuera</a>',
    '<a href="/\\otro.sitio">barra invertida</a><a href="//otro.sitio">protocolo relativo</a><a href="/&#9;/otro.sitio">tab</a><a href="/&#10;/otro.sitio">salto</a><a href="/legal/">propia</a>',
    '<svg><a href="https://mal.example"><text>svg</text></a></svg>',
    '<table><tr><td colspan="2" rowspan="1" scope="col" style="x:y">celda</td></tr></table>',
  ].join('');
  await publica(page, { version: (r) => r.fulfill(json(200, texto({ contenido_html: sucio }))) });
  await page.goto('/legal/terminos-de-uso/');
  await expect(page.getByRole('heading', { level: 2, name: 'Ok' })).toBeVisible();
  const prosa = page.locator('.prosa');
  for (const mal of ['[style]', '[formaction]', '[form]', '[id]', '[name]', '[class]', '[data-k]', '[srcset]', '[ping]', '[target]', '[rel]', '[onerror]', 'svg', 'a[href^="//"]']) await expect(prosa.locator(mal), mal).toHaveCount(0);
  await expect(prosa.locator('p')).toHaveAttribute('title', 't');
  await expect(prosa.locator('img')).toHaveAttribute('alt', 'logo');
  await expect(prosa.locator('img')).toHaveAttribute('src', 'https://bugalu.studio/a.png');
  await expect(prosa.locator('td')).toHaveAttribute('colspan', '2');
  await expect(prosa.locator('td')).toHaveAttribute('scope', 'col');
  await expect(prosa.locator('a[href="/legal/"]')).toHaveCount(1);
  await expect(prosa.getByText('barra invertida')).not.toHaveAttribute('href', /.+/);
  for (const t of ['tab', 'salto']) await expect(prosa.getByText(t, { exact: true })).not.toHaveAttribute('href', /.+/);
});

for (const f of fallos.filter((x) => !['401', '403'].includes(x.n))) {
  test(`publico: ${f.n} al cargar muestra el error con Reintentar y se recupera`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = true;
    await publica(page, { lista: undefined });
    await simular(page, 'GET', '/textos-legales', (r) => (falla ? f.r(r) : r.fulfill(json(200, LISTA))));
    await page.goto('/legal/terminos-de-uso/');
    await expect(ver(page, 'No pudimos cargar el texto. Inténtalo de nuevo en unos minutos.')).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    if (f.n === '503') await page.screenshot({ path: 'pruebas/capturas/textos-legales-error-1440.png', fullPage: true });
    falla = false;
    await page.getByRole('button', { name: 'Reintentar' }).click();
    await expect(ver(page, 'VERSIÓN 1.0.0')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    expect(consola).toEqual([]);
  });
}

test('publico: una pagina publica ignora un token caducado (401) y repite sin token', async ({ page }) => {
  await publica(page);
  const cabeceras = [];
  await simular(page, 'GET', '/textos-legales', (r) => {
    cabeceras.push(r.request().headers().authorization ?? null);
    return r.request().headers().authorization ? r.fulfill(errorApi(401, 'no_autenticado')) : r.fulfill(json(200, LISTA));
  });
  await page.addInitScript(() => localStorage.setItem('bugalu-sesion', JSON.stringify({ access_token: 'caducado', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, refresh_token: 'x', user: { id: 'u1' } })));
  await page.goto('/legal/terminos-de-uso/');
  await expect(ver(page, 'VERSIÓN 1.0.0')).toBeVisible();
});

test('publico: carga con aria-busy mientras la API tarda', async ({ page }) => {
  await publica(page);
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'GET', '/textos-legales', async (r) => { await llega; await r.fulfill(json(200, LISTA)); });
  await page.goto('/legal/terminos-de-uso/');
  await expect(page.getByText('Cargando…')).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(1);
  soltar();
  await expect(ver(page, 'VERSIÓN 1.0.0')).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('publico: el texto da el contacto del estudio y como pedirlo', async ({ page }) => {
    await page.goto('/legal/terminos-de-uso/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^términos de uso$/i);
    // Playwright no lee el texto de <noscript> con getByText: se usan selectores CSS.
    await expect(page.locator('noscript .aviso-titulo')).toHaveText('Este texto necesita JavaScript para mostrarse.');
    await expect(page.locator('noscript a[href^="mailto:somos.bugalu.studio@gmail.com"]')).toBeVisible();
    await expect(page.locator('noscript a[href="https://wa.me/51925530800"]')).toHaveText('+51 925 530 800');
    await expect(page.getByText('Cargando…')).toBeHidden();
    await expect(page.getByRole('contentinfo').getByRole('link', { name: 'Libro de Reclamaciones' })).toBeVisible();
    expect(await page.locator('noscript .aviso').evaluate((e) => getComputedStyle(e).maxWidth)).not.toBe('none'); // N6
    await page.screenshot({ path: 'pruebas/capturas/textos-legales-sin-js-1440.png', fullPage: true });
  });
});

// --- 2. Directorio ---
for (const t of tamanos) {
  test(`publico: directorio de textos a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await publica(page);
    await page.goto('/legal/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^textos legales$/i);
    await expect(page.getByText('Las reglas con las que trabajamos. Cada texto indica su versión y desde cuándo rige.')).toBeVisible();
    const filas = page.getByRole('table', { name: 'Textos legales' }).getByRole('row');
    await expect(filas).toHaveCount(5);
    await expect(filas.nth(1)).toContainText('Términos de uso');
    await expect(filas.nth(1)).toContainText('1.0.0');
    await expect(filas.nth(1)).toContainText('1 dic 2026');
    await expect(filas.nth(1)).toContainText('1.1.0 desde el 15 dic 2026');
    await expect(filas.nth(2)).toContainText('1.2.3');
    await expect(filas.nth(2)).toContainText('—');
    await expect(filas.nth(3)).toContainText('Condiciones de contratación');
    await expect(page.getByRole('main').getByRole('link', { name: 'Términos de uso' })).toHaveAttribute('href', '/legal/terminos-de-uso/');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/textos-legales-directorio-${t.nombre}.png`, fullPage: true });
  });
}

test('publico: directorio con error de red ofrece Reintentar', async ({ page }) => {
  await publica(page);
  await simular(page, 'GET', '/textos-legales', (r) => r.abort('connectionrefused'));
  await page.goto('/legal/');
  await expect(ver(page, 'No pudimos cargar el texto. Inténtalo de nuevo en unos minutos.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
});

// El libro de reclamaciones ya no es provisional: lo cubre reclamacion-publico.spec.js.

// --- 4. Administrador: lista ---
async function admin(page, { lista = json(200, LISTA) } = {}) {
  await page.clock.setFixedTime(HOY);
  await comoAdministrador(page);
  // Prellenado (RF-17 CA-16) y vista previa (CA-18): la version de partida llega vacia y la vista previa devuelve el texto en un <p>.
  await page.route((u) => /^\/api\/v1\/textos-legales\/[^/]+\/versiones\/[^/]+$/.test(u.pathname), (r) => r.fulfill(json(200, texto({ contenido: '', resumenes: {} }))));
  await simular(page, 'POST', '/textos-legales/previsualizar', (r) => r.fulfill(json(200, { contenido_html: `<p>${r.request().postDataJSON().contenido}</p>` })));
  return { lista: await simular(page, 'GET', '/textos-legales', lista) };
}

for (const t of tamanos) {
  test(`admin: lista de textos con vigente y programada a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await admin(page);
    await page.goto('/app/textos');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^textos legales$/i);
    await expect(page.getByText('Publica nuevas versiones de los términos, la privacidad y las condiciones. Las publicadas no se editan.')).toBeVisible();
    await expect(page.getByText('[A10] CONTROL / TEXTOS')).toBeVisible();
    const filas = page.getByRole('table', { name: 'Textos' }).getByRole('row');
    await expect(filas).toHaveCount(5);
    await expect(filas.nth(1)).toContainText('versión 1.0.0 · desde 1 dic 2026');
    await expect(filas.nth(1)).toContainText('1.1.0 · desde 15 dic 2026');
    await expect(filas.nth(1).getByRole('link', { name: 'Ver versión 1.0.0 de Términos de uso' })).toHaveAttribute('href', '/app/textos/ver?tipo=terminos_uso&version=1.0.0');
    await expect(filas.nth(2)).toContainText('versión 1.2.3');
    await expect(filas.nth(3)).toContainText('SIN PUBLICAR');
    await expect(page.getByRole('button', { name: 'Publicar versión de Términos de uso' })).toHaveAttribute('aria-disabled', 'true'); // hay programada: publicar daria 409
    await expect(page.getByRole('link', { name: 'Publicar versión de Política de privacidad' })).toHaveAttribute('href', '/app/textos/publicar?tipo=politica_privacidad');
    await expect(page.getByRole('link', { name: 'Publicar versión de Declaración de agrupación' })).toHaveAttribute('href', '/app/textos/publicar?tipo=declaracion_agrupacion');
    await expect(page.getByRole('button', { name: 'Retirar versión 1.1.0 de Términos de uso' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Retirar versión/ })).toHaveCount(1);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/textos-admin-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('admin: retirar pide confirmar, Volver devuelve el foco y Retirar borra la programada', async ({ page }) => {
  await admin(page);
  const borrados = await simular(page, 'DELETE', '/textos-legales/terminos_uso/versiones/1.1.0', { status: 204, body: '' });
  await page.goto('/app/textos');
  await page.getByRole('button', { name: 'Retirar versión 1.1.0 de Términos de uso' }).click();
  await expect(page.getByRole('heading', { level: 2, name: /retirar versión 1.1.0 de términos de uso/i })).toBeFocused();
  await expect(page.getByText('Se borra el contenido y no se puede recuperar. La versión vigente sigue rigiendo.')).toBeVisible();
  await sinViolaciones(page);
  // N2: aire entre el parrafo y la barra Decision (espacio-4 = 16 px).
  const aire = await page.evaluate(() => document.querySelector('.textos-retiro-texto').nextElementSibling.getBoundingClientRect().top - document.querySelector('.textos-retiro-texto').getBoundingClientRect().bottom);
  expect(aire).toBeGreaterThanOrEqual(16);
  await page.screenshot({ path: 'pruebas/capturas/textos-admin-retirar-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Volver' }).click();
  await expect(page.getByRole('button', { name: 'Publicar versión de Términos de uso' })).toBeFocused();
  expect(borrados).toHaveLength(0);
  await page.getByRole('button', { name: 'Retirar versión 1.1.0 de Términos de uso' }).click();
  await page.getByRole('button', { name: 'Retirar versión', exact: true }).click();
  await page.waitForURL('**/app/textos?aviso=version-retirada**');
  await expect(page.getByText('Versión retirada.')).toBeVisible();
  expect(borrados).toHaveLength(1);
  await expect(page).not.toHaveURL(/aviso/);
});

test('admin: 409 version_vigente al retirar avisa y recarga la lista', async ({ page }) => {
  const consola = vigilarConsola(page);
  const lista = await admin(page);
  await simular(page, 'DELETE', '/textos-legales/terminos_uso/versiones/1.1.0', json(409, { error: { codigo: 'version_vigente', mensaje: 'x' } }));
  await page.goto('/app/textos');
  await page.getByRole('button', { name: 'Retirar versión 1.1.0 de Términos de uso' }).click();
  await page.getByRole('button', { name: 'Retirar versión', exact: true }).click();
  await expect(page.getByText('Esa versión ya está vigente y no se puede retirar.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByRole('table', { name: 'Textos' })).toBeVisible();
  expect(lista.lista.length).toBeGreaterThanOrEqual(2);
  expect(consola).toEqual([]);
});

test('admin: lista aviso version-publicada solo de la lista cerrada', async ({ page }) => {
  await admin(page);
  await page.goto('/app/textos?aviso=version-publicada');
  await expect(page.getByText('Versión publicada.')).toBeVisible();
  await expect(page.locator('.aviso-exito')).toBeFocused();
  await page.goto('/app/textos?aviso=otra-cosa');
  await expect(page.locator('.aviso-exito')).toHaveCount(0);
});

for (const f of fallos) {
  test(`admin: lista, respuesta ${f.n} al cargar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await admin(page, { lista: f.r });
    await page.goto('/app/textos');
    await expect(page.getByRole('main')).toContainText(f.texto);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('admin: lista sin JS avisa', async ({ browser }) => {
  const pagina = await (await browser.newContext({ javaScriptEnabled: false })).newPage();
  await pagina.goto('/app/textos');
  await expect(pagina.locator('noscript .aviso-informacion').first()).toBeVisible();
  await expect(pagina.getByText('Cargando…')).toBeHidden();
});

// --- 5. Administrador: publicar ---
const publicar = (page, resp = json(201, texto({ version: '2.0.0' }))) => simular(page, 'POST', '/textos-legales', resp);
const ver = (page, t) => page.locator('p:not([data-anuncio])').filter({ hasText: t }).first();
const campo = (page, nombre) => page.getByLabel(nombre, { exact: false });

async function llenar(page, { cambio = 'Mayor', version, fecha = '2026-12-10' } = {}) {
  await page.getByRole('radio', { name: new RegExp(`^${cambio}`) }).check();
  if (version) await page.getByLabel(/^Versión/).fill(version);
  if (cambio !== 'Parche') await page.getByLabel(/^Vigente desde/).fill(fecha);
  await page.locator('[name^="resumen_"]').first().fill('Frases cortas.');
  await page.getByLabel(/^Contenido/).fill('# Título\n\nTexto.');
}

for (const t of tamanos) {
  test(`admin: formulario de publicar a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await admin(page);
    await page.goto('/app/textos/publicar?tipo=terminos_uso');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^publicar versión$/i);
    await expect(page.getByText('Términos de uso: elige el tipo de cambio y desde cuándo rige.')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /P1 versión/i })).toBeVisible();
    await expect(page.getByText('Términos de uso', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('1.1.0', { exact: true })).toBeVisible(); // ultima version: la programada gana a la vigente
    await expect(page.getByRole('radio')).toHaveCount(3);
    for (const r of await page.getByRole('radio').all()) await expect(r).not.toBeChecked();
    await expect(page.getByText('Cambia derechos u obligaciones. Avisa por correo; los términos se vuelven a aceptar.')).toBeVisible();
    await expect(page.getByText('Erratas y formato. Rige al publicarla, sin aviso.')).toBeVisible();
    await expect(page.getByText('Lo que verá la persona antes de aceptar. Frases cortas, en segunda persona.')).toBeVisible();
    await expect(page.getByText('Texto completo en Markdown: # para títulos y - para listas.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Revisar y publicar' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/textos-admin-publicar-${t.nombre}.png`, fullPage: true });
  });
}

test('admin: la version se prellena segun el tipo de cambio y respeta lo que escribas', async ({ page }) => {
  await admin(page, { lista: json(200, [LISTA[0]]) });
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  const version = page.getByLabel(/^Versión/);
  await page.getByRole('radio', { name: /^Mayor/ }).check();
  await expect(version).toHaveValue('2.0.0');
  await page.getByRole('radio', { name: /^Menor/ }).check();
  await expect(version).toHaveValue('1.1.0');
  await page.getByRole('radio', { name: /^Parche/ }).check();
  await expect(version).toHaveValue('1.0.1');
  await version.fill('1.0.7');
  await page.getByRole('radio', { name: /^Menor/ }).check();
  await expect(version).toHaveValue('1.0.7');
});

test('admin: fecha minima a hoy+16 (reloj a media manana de Lima) y el parche rige al publicarse', async ({ page }) => {
  await admin(page, { lista: json(200, [LISTA[0]]) });
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await page.getByRole('radio', { name: /^Mayor/ }).check();
  await expect(page.getByLabel(/^Vigente desde/)).toHaveAttribute('min', '2026-12-01');
  await page.getByRole('radio', { name: /^Parche/ }).check();
  await expect(page.getByLabel(/^Vigente desde/)).toBeHidden();
  await expect(page.getByText('Rige al publicarla.', { exact: true })).toBeVisible();
});

test('admin: hoy+15 se rechaza localmente y hoy+16 pasa a la revision', async ({ page }) => {
  await admin(page, { lista: json(200, [LISTA[0]]) });
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Mayor', version: '2.0.0', fecha: '2026-11-30' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByText('Elige una fecha desde el 1 dic 2026: los clientes necesitan 15 días de aviso.')).toBeVisible();
  await page.getByLabel(/^Vigente desde/).fill('2026-12-01');
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByRole('button', { name: 'Publicar versión', exact: true })).toBeVisible();
});

test('admin: primera version de un texto, sin aviso previo y desde hoy', async ({ page }) => {
  await admin(page, { lista: json(200, []) });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await page.getByRole('radio', { name: /^Mayor/ }).check();
  await expect(page.getByLabel(/^Versión/)).toHaveValue('1.0.0');
  await expect(page.getByLabel(/^Vigente desde/)).toHaveAttribute('min', '2026-11-15');
});

test('admin: validacion con errores bajo cada campo y resumen', async ({ page }) => {
  await admin(page);
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.locator('.aviso-error')).toBeFocused(); // N1: el foco va al resumen, no al enlace de salto
  await expect(page.getByRole('link', { name: 'Saltar al contenido' })).not.toBeFocused();
  await expect(page.getByText('Revisa 5 campos')).toBeVisible();
  await expect(page.locator('.aviso-error').getByRole('link', { name: 'Resumen de registro' })).toBeVisible(); // N8: nombra el campo, no "Resumen"
  await expect(page.getByRole('group', { name: 'Tipo de cambio (obligatorio)' })).toBeVisible();
  await expect(page.getByText('Elige el tipo de cambio.')).toBeVisible();
  await expect(page.getByText('Escribe la versión como 1.2.0.')).toBeVisible();
  await expect(page.getByText('Elige desde cuándo rige.')).toBeVisible();
  await expect(page.getByText('Escribe el resumen.')).toBeVisible();
  await expect(page.getByText('Escribe el contenido.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/textos-admin-publicar-errores-1440.png', fullPage: true });
});

test('admin: revision antes de publicar, volver a editar conserva todo y publicar envia el contrato', async ({ page }) => {
  const consola = vigilarConsola(page);
  await admin(page);
  const envios = await publicar(page);
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Mayor', version: '2.0.0' });
  await page.getByLabel(/^Resumen de cambios/).fill('Cambia el plazo de cancelación.');
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByRole('heading', { level: 2, name: /R1 revisa antes de publicar/i })).toBeFocused();
  await expect(page.getByRole('link', { name: 'Saltar al contenido' })).not.toBeFocused();
  await expect(page.getByText('Al publicarla no podrás editarla. Avisaremos por correo a todos los clientes y regirá desde el 10 dic 2026 para las operaciones nuevas.')).toBeVisible();
  await expect(page.getByText('Cada cliente tendrá que aceptarlos de nuevo para reservar.')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Contenido' })).toContainText('# Título'); // la vista previa que devuelve la API, con su formato
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/textos-admin-revision-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Volver a editar' }).click();
  await expect(page.getByLabel(/^Versión/)).toHaveValue('2.0.0');
  await expect(page.getByLabel(/^Contenido/)).toHaveValue('# Título\n\nTexto.');
  await expect(page.getByRole('button', { name: 'Revisar y publicar' })).toBeFocused();
  expect(envios).toHaveLength(0);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await page.waitForURL('**/app/textos?aviso=version-publicada**');
  await expect(page.getByText('Versión publicada.')).toBeVisible();
  expect(envios).toHaveLength(1);
  expect(envios[0].cuerpo).toEqual({
    tipo: 'terminos_uso', version: '2.0.0', tipo_cambio: 'mayor', contenido: '# Título\n\nTexto.',
    resumenes: { registro: 'Frases cortas.' }, resumen_cambios: 'Cambia el plazo de cancelación.', vigente_desde: '2026-12-10T00:00:00-05:00',
  });
  expect(consola).toEqual([]);
});

test('admin: un parche se publica sin vigente_desde y avisa que no se retira', async ({ page }) => {
  await admin(page);
  const envios = await publicar(page);
  await page.goto('/app/textos/publicar?tipo=politica_privacidad');
  await llenar(page, { cambio: 'Parche' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByText('Al publicarla no podrás editarla ni retirarla, y rige desde ahora.')).toBeVisible();
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await page.waitForURL('**/app/textos?aviso=version-publicada**');
  expect(envios[0].cuerpo).toMatchObject({ tipo: 'politica_privacidad', version: '1.2.4', tipo_cambio: 'parche' });
  expect(envios[0].cuerpo).not.toHaveProperty('vigente_desde');
});

test('admin: 422 version_invalida deja el error bajo la version y la lleva a editar', async ({ page }) => {
  await admin(page, { lista: json(200, [LISTA[0]]) });
  await publicar(page, errorApi(422, 'version_invalida'));
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Mayor', version: '1.5.0' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await expect(page.getByText('Para un cambio mayor la versión debe ser 2.0.0, mayor que la última (1.0.0).')).toBeVisible();
  await expect(page.getByLabel(/^Versión/)).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByLabel(/^Contenido/)).toHaveValue('# Título\n\nTexto.');
  await sinViolaciones(page);
});

test('admin: 422 aviso_insuficiente deja el error bajo la fecha', async ({ page }) => {
  await admin(page);
  await publicar(page, errorApi(422, 'aviso_insuficiente'));
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Menor', version: '1.2.0', fecha: '2026-12-01' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await expect(page.getByText('Elige una fecha desde el 1 dic 2026: los clientes necesitan 15 días de aviso.')).toBeVisible();
  await expect(page.getByLabel(/^Vigente desde/)).toHaveAttribute('aria-invalid', 'true');
});

test('admin: 409 version_programada avisa con la programada y vuelve a textos', async ({ page }) => {
  const consola = vigilarConsola(page);
  await admin(page, { lista: json(200, [LISTA[0]]) }); // al cargar no habia programada
  await publicar(page, errorApi(409, 'version_programada'));
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Mayor', version: '2.0.0' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await simular(page, 'GET', '/textos-legales', json(200, LISTA));
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await expect(page.getByText('Ya hay una versión programada de este texto (1.1.0, desde 15 dic 2026). Retírala antes de publicar otra.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByRole('link', { name: 'Volver a textos' })).toHaveAttribute('href', '/app/textos');
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/textos-admin-programada-1440.png', fullPage: true });
});

test('admin: 409 conflicto avisa y conserva lo escrito', async ({ page }) => {
  await admin(page);
  await publicar(page, errorApi(409, 'conflicto'));
  await page.goto('/app/textos/publicar?tipo=terminos_uso');
  await llenar(page, { cambio: 'Mayor', version: '2.0.0' });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await expect(page.getByText('Alguien publicó una versión de este texto hace un momento. Revisa la lista antes de seguir.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Publicar versión', exact: true })).toBeEnabled();
});

for (const f of [{ n: '503', r: errorApi(503, 'servicio_no_disponible'), t: 'El servicio no responde. Inténtalo de nuevo en unos minutos.' }, { n: 'no-json', r: { status: 200, contentType: 'text/html', body: '<h1>x</h1>' }, t: 'Algo salió mal. Inténtalo de nuevo.' }]) {
  test(`admin: publicar con ${f.n} conserva lo escrito y no ofrece Reintentar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await admin(page);
    await publicar(page, f.r);
    await page.goto('/app/textos/publicar?tipo=terminos_uso');
    await llenar(page, { cambio: 'Mayor', version: '2.0.0' });
    await page.getByRole('button', { name: 'Revisar y publicar' }).click();
    await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
    await expect(page.locator('.aviso-error')).toContainText(f.t);
    await expect(page.locator('.aviso-error')).toBeFocused();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
    await page.getByRole('button', { name: 'Volver a editar' }).click();
    await expect(page.getByLabel(/^Contenido/)).toHaveValue('# Título\n\nTexto.');
    expect(consola).toEqual([]);
  });
}

test('admin: publicar con tipo desconocido es no encontrado', async ({ page }) => {
  await admin(page);
  await page.goto('/app/textos/publicar?tipo=../../x');
  await expect(page.getByRole('main')).toContainText('No encontramos este texto.');
  await expect(page.getByRole('link', { name: 'Volver a textos' })).toHaveAttribute('href', '/app/textos');
});

for (const f of fallos) {
  test(`admin: publicar, respuesta ${f.n} al cargar`, async ({ page }) => {
    await admin(page, { lista: f.r });
    await page.goto('/app/textos/publicar?tipo=terminos_uso');
    await expect(page.getByRole('main')).toContainText(f.texto);
    await sinViolaciones(page);
  });
}

// --- 6. Navegacion ---
test('navegacion: TEXTOS con icono file-text, actual en su pantalla (escritorio)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await admin(page);
  await page.goto('/app/textos');
  const enlace = page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Textos', exact: true });
  await expect(enlace).toHaveAttribute('href', '/app/textos/');
  await expect(enlace).toHaveAttribute('aria-current', 'page');
  await expect(enlace.locator('svg path')).toHaveCount(5);
});

test('navegacion: TEXTOS en el menu del movil y un cliente no la ve', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await admin(page);
  await page.goto('/app/textos');
  await page.getByText('Menú', { exact: true }).click();
  await expect(page.locator('.cabecera-menu-panel').getByRole('link', { name: 'Textos', exact: true })).toHaveAttribute('aria-current', 'page');
  const otra = await page.context().newPage();
  await otra.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
  await otra.setViewportSize({ width: 1440, height: 900 });
  await otra.goto('/app/');
  await expect(otra.getByRole('link', { name: 'Textos', exact: true })).toBeHidden();
});

// --- 7. Usuarios con documento repetido ---
const USUARIOS = [
  { id: 'u1', nombre: 'Ana Pérez', correo: 'ana@correo.com', rol: 'cliente', especialidad: null, documento: { tipo: 'dni', numero: '12345678' }, documento_repetido: true },
  { id: 'u2', nombre: 'Luis Mora', correo: 'luis@correo.com', rol: 'cliente', especialidad: null, documento: { tipo: 'dni', numero: '12345678' }, documento_repetido: true },
  { id: 'u3', nombre: 'Rosa Gil', correo: 'rosa@correo.com', rol: 'personal', especialidad: 'Mezcla', documento: { tipo: 'ce', numero: 'AB12345' }, documento_repetido: false },
  { id: 'u4', nombre: 'Sin Documento', correo: 'sd@correo.com', rol: 'cliente', especialidad: null, documento: null, documento_repetido: false },
];

test('usuarios: columna documento con etiqueta REPETIDO y filtro que llega a la API', async ({ page }) => {
  const consola = vigilarConsola(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await comoAdministrador(page);
  const api = await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
  await page.goto('/app/usuarios');
  const filas = page.getByRole('table', { name: 'Cuentas del estudio' }).getByRole('row');
  await expect(filas.nth(1)).toContainText('DNI 12345678');
  await expect(filas.nth(1)).toContainText('REPETIDO');
  await expect(filas.nth(3)).toContainText('CE AB12345');
  await expect(filas.nth(3)).not.toContainText('REPETIDO');
  await expect(filas.nth(4)).toContainText('—');
  await expect(page.getByRole('link', { name: 'Documento repetido' })).toHaveAttribute('href', '/app/usuarios?documento=repetido');
  expect(api[0].url.search).toBe('');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/usuarios-documento-1440.png', fullPage: true });
  expect(consola).toEqual([]);
});

for (const t of tamanos) {
  test(`usuarios: filtro documento=repetido, ordenado por documento a ${t.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoAdministrador(page);
    const api = await simular(page, 'GET', '/usuarios', json(200, [USUARIOS[1], USUARIOS[0]]));
    await page.goto('/app/usuarios?documento=repetido');
    expect(api[0].url.searchParams.get('documento_repetido')).toBe('true');
    const marcado = page.getByRole('link', { name: 'Documento repetido' });
    await expect(marcado).toHaveAttribute('aria-current', 'true');
    const filas = page.getByRole('table', { name: 'Cuentas del estudio' }).getByRole('row');
    await expect(filas).toHaveCount(3);
    await expect(filas.nth(1)).toContainText('Ana Pérez'); // mismo documento: orden estable por nombre
    await expect(filas.nth(2)).toContainText('Luis Mora');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/usuarios-documento-repetido-${t.nombre}.png`, fullPage: true });
  });
}

test('usuarios: sin documentos repetidos', async ({ page }) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/usuarios', json(200, []));
  await page.goto('/app/usuarios?documento=repetido');
  await expect(page.getByText('No hay documentos repetidos.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Quitar filtros' })).toHaveAttribute('href', '/app/usuarios');
});

test('usuarios: valor desconocido de documento se ignora', async ({ page }) => {
  await comoAdministrador(page);
  const api = await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
  await page.goto('/app/usuarios?documento=x');
  expect(api[0].url.search).toBe('');
});

// --- 8. Ficha de persona del Administrador (U1 ampliado y U3 textos aceptados) ---
const UID = '11111111-1111-4111-8111-111111111111';
const FICHA = {
  id: UID, nombre: 'Ana Pérez', correo: 'ana@correo.com', rol: 'cliente', especialidad: null, telefono: '987654321', nombre_artistico: 'Ana y los Ecos',
  modalidad: 'agrupacion', documento: { tipo: 'dni', numero: '12345678' }, documento_repetido: true, domicilio: 'Av. Lima 123',
  redes: [{ red: 'instagram', valor: '@ana' }], integrantes: [{ nombre: 'Luis', rol: 'Voz' }],
};
const ACEPTADOS = [
  { id: 'a1', tipo: 'terminos_uso', version: '1.0.0', contexto: 'registro', id_operacion: 'o1', aceptada_en: '2026-11-10T15:00:00Z', retirada_en: null },
  { id: 'a2', tipo: 'politica_privacidad', version: '1.2.3', contexto: 'promociones', id_operacion: 'o2', aceptada_en: '2026-11-12T15:00:00Z', retirada_en: '2026-12-03T15:00:00Z' },
];
const fichaApi = async (page, aceptaciones) => {
  await comoAdministrador(page);
  await simular(page, 'GET', '/usuarios', json(200, [FICHA]));
  return simular(page, 'GET', `/usuarios/${UID}/aceptaciones`, aceptaciones);
};

for (const t of tamanos) {
  test(`ficha: identidad y textos aceptados de la persona a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const api = await fichaApi(page, json(200, ACEPTADOS));
    await page.goto(`/app/usuarios/editar?id=${UID}`);
    const persona = page.getByRole('region', { name: /Persona/ });
    await expect(persona).toContainText('Agrupación');
    await expect(persona).toContainText('DNI 12345678');
    await expect(persona).toContainText('REPETIDO');
    await expect(persona).toContainText('Av. Lima 123');
    await expect(persona).toContainText('Instagram: @ana');
    await expect(persona).toContainText('Luis, Voz');
    const filas = page.getByRole('table', { name: 'Textos que aceptó esta persona' }).locator('tbody tr');
    await expect(filas).toHaveCount(2);
    await expect(filas.first()).toContainText('Política de privacidad');
    await expect(filas.first()).toContainText('Retirado el 3 dic 2026');
    await expect(filas.nth(1)).toContainText('—');
    expect(api).toHaveLength(1);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/usuarios-ficha-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('ficha: sin aceptaciones y con error en U3 (el resto sigue usable)', async ({ page }) => {
  await fichaApi(page, json(200, []));
  await page.goto(`/app/usuarios/editar?id=${UID}`);
  await expect(page.getByText('Esta persona aún no ha aceptado ningún texto.')).toBeVisible();
  const otra = await page.context().newPage();
  await comoAdministrador(otra);
  await simular(otra, 'GET', '/usuarios', json(200, [FICHA]));
  await simular(otra, 'GET', `/usuarios/${UID}/aceptaciones`, (r) => r.fulfill(errorApi(503, 'x')));
  await otra.goto(`/app/usuarios/editar?id=${UID}`);
  await expect(otra.getByText('No pudimos cargar los textos aceptados.')).toBeVisible();
  await expect(otra.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  await expect(otra.getByRole('button', { name: 'Guardar rol y especialidad' })).toBeEnabled();
});

// --- Cobertura permanente (auditoria B, ronda 1) ---
test('publico: la región viva anuncia una sola vez el error y tras Reintentar, y el aviso no es vivo', async ({ page }) => {
  let falla = true;
  await publica(page, { version: (r) => (falla ? r.fulfill(errorApi(503, 'x')) : r.fulfill(json(200, texto()))) });
  await page.addInitScript(() => {
    window.__anuncios = [];
    document.addEventListener('DOMContentLoaded', () => {
      const vivo = document.querySelector('[data-anuncio]');
      new MutationObserver(() => vivo.textContent && window.__anuncios.push(vivo.textContent)).observe(vivo, { childList: true, characterData: true, subtree: true });
    });
  });
  await page.goto('/legal/terminos-de-uso/');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  await expect(page.locator('[data-salida] [role]')).toHaveCount(0);
  expect(await page.evaluate(() => window.__anuncios)).toEqual(['No pudimos cargar el texto. Inténtalo de nuevo en unos minutos.']);
  falla = false;
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'Quiénes somos' })).toBeVisible();
  await expect(page.locator('[data-salida] [role]')).toHaveCount(0);
  expect((await page.evaluate(() => window.__anuncios)).length).toBe(2);
});

test.describe('directorio sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('explica qué falta y da el contacto', async ({ page }) => {
    await page.goto('/legal/');
    await expect(page.locator('noscript .aviso-titulo')).toHaveText('Esta lista necesita JavaScript para mostrarse.');
    await expect(page.locator('noscript a[href^="mailto:somos.bugalu.studio@gmail.com"]')).toBeVisible();
    await expect(page.getByText('Cargando…')).toBeHidden();
  });
});

test('admin: motivos y resúmenes con HTML hostil se pintan como texto', async ({ page }) => {
  const mal = '<img src=x onerror="window.__xss = 1"><b>negrita</b>';
  await admin(page, { lista: json(200, LISTA.map((x) => ({ ...x, resumenes: { registro: mal, pago: mal }, resumen_cambios: mal }))) });
  await page.goto('/app/textos');
  await expect(page.getByRole('table', { name: 'Textos' })).toBeVisible();
  await expect(page.locator('main').locator('img, b')).toHaveCount(0);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

test('ficha: nombre, domicilio, redes e integrantes con HTML hostil se pintan como texto', async ({ page }) => {
  const mal = '<img src=x onerror="window.__xss = 1"><b>negrita</b>';
  await comoAdministrador(page);
  await simular(page, 'GET', '/usuarios', json(200, [{ ...FICHA, nombre: mal, nombre_artistico: mal, domicilio: mal, redes: [{ red: 'instagram', valor: mal }], integrantes: [{ nombre: mal, rol: mal }] }]));
  await simular(page, 'GET', `/usuarios/${UID}/aceptaciones`, json(200, ACEPTADOS));
  await page.goto(`/app/usuarios/editar?id=${UID}`);
  const persona = page.getByRole('region', { name: /Persona/ });
  await expect(persona).toContainText('<img src=x');
  await expect(page.locator('main').locator('img, b')).toHaveCount(0);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

for (const f of fallos) {
  test(`ficha: los textos aceptados fallan (${f.n}) con mensaje y el resto sigue usable`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await fichaApi(page, f.r);
    await page.goto(`/app/usuarios/editar?id=${UID}`);
    await expect(page.getByRole('region', { name: /Persona/ })).toContainText('DNI 12345678');
    await expect(page.getByText(/No pudimos cargar los textos aceptados|Tu sesión no es válida|solo para el Administrador/).first()).toBeVisible();
    if (f.reintentar) await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}
