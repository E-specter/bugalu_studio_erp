// RF-17 (CA-15 a CA-18): ver una version, prellenar, cargar un .md y vista previa del editor de textos legales. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const LISTA = [
  { tipo: 'terminos_uso', version: '1.0.0', tipo_cambio: 'mayor', vigente_desde: '2026-12-01T00:00:00-05:00', resumenes: { registro: 'Reglas de uso.' }, programada: false },
  { tipo: 'politica_privacidad', version: '1.2.3', tipo_cambio: 'parche', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes: { registro: 'Cómo tratamos tus datos.' }, programada: false },
];
const PROGRAMADA = { tipo: 'terminos_uso', version: '1.1.0', tipo_cambio: 'menor', vigente_desde: '2026-12-15T00:00:00-05:00', resumenes: { registro: 'Reglas de uso, con aclaraciones.' }, programada: true };
const HTML = '<h1>Términos</h1><p>Texto base con <a href="https://bugalu.studio/x">enlace</a>.</p><h2>Daños</h2><h6>Detalle</h6>';
const texto = (extra = {}) => ({
  ...LISTA[0], contenido: '# Términos\n\nTexto base.', contenido_html: HTML, publicado_en: '2026-11-10T10:00:00-05:00', resumen_cambios: 'Primera versión.',
  resumenes: { registro: 'Reglas de uso.' }, ...extra,
});
const HOY = new Date('2026-11-15T15:00:00Z');
const previaPorDefecto = (r) => r.fulfill(json(200, { contenido_html: `<h1>Previa</h1><p>${r.request().postDataJSON().contenido.slice(0, 60)}</p>` }));

async function admin(page, { lista = LISTA, version = (r) => r.fulfill(json(200, texto())), previa = previaPorDefecto } = {}) {
  await page.clock.setFixedTime(HOY);
  await comoAdministrador(page);
  const v = { versiones: [] };
  await simular(page, 'GET', '/textos-legales', json(200, lista));
  await page.route((u) => /^\/api\/v1\/textos-legales\/[^/]+\/versiones\/[^/]+$/.test(u.pathname), (r) => {
    if (r.request().method() !== 'GET') return r.fallback();
    v.versiones.push(new URL(r.request().url()).pathname.split('/').slice(-3).join('/'));
    return version(r);
  });
  v.previas = await simular(page, 'POST', '/textos-legales/previsualizar', previa);
  v.publicaciones = await simular(page, 'POST', '/textos-legales', json(201, texto({ version: '2.0.0' })));
  return v;
}
const sinDesborde = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const contenido = (page) => page.getByLabel(/^Contenido/);
const previa = (page) => page.getByRole('region', { name: 'Vista previa' });
const carga = (page) => page.getByLabel('Cargar archivo .md');
const actualizar = (page) => page.getByRole('button', { name: 'Actualizar vista previa' });
const archivo = (name, contenidoDelArchivo, mimeType = 'text/markdown') => ({ name, mimeType, buffer: Buffer.isBuffer(contenidoDelArchivo) ? contenidoDelArchivo : Buffer.from(contenidoDelArchivo, 'utf-8') });
const visible = (page, t) => page.locator('p:not([data-anuncio])').filter({ hasText: t }).first();
const aviso = (page, t) => page.locator('.aviso').filter({ hasText: t }).first();
const EDITAR = '/app/textos/publicar?tipo=terminos_uso';

// --- Lista: Ver y Publicar bloqueado ---
test('lista: "Ver" con el objeto en el nombre, a la vista del panel, y Publicar deshabilitado con programada', async ({ page }) => {
  const consola = vigilarConsola(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await admin(page, { lista: [...LISTA, PROGRAMADA] });
  await page.goto('/app/textos');
  await expect(page.getByRole('link', { name: 'Ver versión 1.0.0 de Términos de uso' })).toHaveAttribute('href', '/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByRole('link', { name: 'Ver versión 1.1.0 de Términos de uso' })).toHaveAttribute('href', '/app/textos/ver?tipo=terminos_uso&version=1.1.0');
  await expect(page.getByRole('link', { name: 'Ver versión 1.2.3 de Política de privacidad' })).toBeVisible();
  const fila = page.getByRole('row').filter({ hasText: 'Términos de uso' });
  await expect(fila).toContainText('versión 1.0.0 · desde 1 dic 2026');
  await expect(fila).toContainText('1.1.0 · desde 15 dic 2026');
  // Con programada: sin enlace de publicar, boton deshabilitado con su motivo.
  await expect(page.getByRole('link', { name: 'Publicar versión de Términos de uso' })).toHaveCount(0);
  const bloqueado = page.getByRole('button', { name: 'Publicar versión de Términos de uso' });
  await expect(bloqueado).toHaveAttribute('aria-disabled', 'true');
  await expect(bloqueado).toHaveAccessibleDescription('Retira la versión programada para publicar otra.');
  await expect(fila.getByText('Retira la versión programada para publicar otra.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Publicar versión de Política de privacidad' })).toHaveAttribute('href', '/app/textos/publicar?tipo=politica_privacidad');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-lista-ver-1440.png', fullPage: true });
  expect(consola).toEqual([]);
});

test('lista: a 390 y 320 px la tabla con Ver no desborda', async ({ page }) => {
  await admin(page, { lista: [...LISTA, PROGRAMADA] });
  for (const ancho of [390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    await page.goto('/app/textos');
    await expect(page.getByRole('link', { name: 'Ver versión 1.0.0 de Términos de uso' })).toBeVisible();
    expect(await sinDesborde(page)).toBe(true);
    await page.screenshot({ path: `pruebas/capturas/rf17-lista-ver-${ancho}.png`, fullPage: true });
  }
});

// --- Ver ---
for (const t of tamanos) {
  test(`ver: datos, resumenes y texto con su formato final a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await admin(page, { version: (r) => r.fulfill(json(200, texto({ programada: true, resumenes: { registro: 'Reglas de uso.' } }))) });
    await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^términos de uso · versión 1\.0\.0$/i);
    await expect(page.getByText('[A10] CONTROL / TEXTOS')).toBeVisible();
    await expect(page.getByText('Así la leen los clientes en la página pública.')).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Ruta' })).toContainText('Términos de uso');
    await expect(page.getByRole('link', { name: 'Volver a textos' })).toHaveAttribute('href', '/app/textos');
    for (const h of [/V1 Versión/i, /V2 Resúmenes/i, /V3 Texto/i]) await expect(page.getByRole('heading', { level: 2, name: h })).toBeVisible();
    const v1 = page.getByRole('region', { name: /V1 Versión/i });
    await expect(v1).toContainText('Mayor');
    await expect(v1).toContainText('1 dic 2026');
    await expect(v1.getByText('PROGRAMADA', { exact: true })).toBeVisible();
    await expect(v1).toContainText('10 nov 2026');
    await expect(v1).toContainText('Primera versión.');
    await expect(page.getByRole('region', { name: /V2 Resúmenes/i })).toContainText('Reglas de uso.');
    // El <h1> del texto baja a <h3> (bajo el <h2> del panel); el resto, uno mas, hasta <h6>.
    const v3 = page.getByRole('region', { name: /V3 Texto/i });
    await expect(v3.getByRole('heading', { level: 3, name: 'Términos' })).toBeVisible();
    await expect(v3.getByRole('heading', { level: 4, name: 'Daños' })).toBeVisible();
    await expect(v3.getByRole('heading', { level: 6, name: 'Detalle' })).toBeVisible();
    const enlace = v3.getByRole('link', { name: /enlace/ });
    await expect(enlace).toHaveAttribute('target', '_blank');
    await expect(enlace).toHaveAttribute('rel', 'noopener');
    await expect(enlace).toHaveAccessibleName('enlace (se abre en otra pestaña)');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    expect(await sinDesborde(page)).toBe(true);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf17-ver-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('ver: una version vigente no lleva etiqueta PROGRAMADA y sin resumen de cambios dice "—"', async ({ page }) => {
  await admin(page, { version: (r) => r.fulfill(json(200, texto({ resumen_cambios: null }))) });
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByRole('region', { name: /V1 Versión/i })).toContainText('Resumen de cambios—');
  await expect(page.getByText('PROGRAMADA', { exact: true })).toBeHidden();
});

test('ver: 320 px no desborda', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await admin(page);
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByRole('heading', { level: 3, name: 'Términos' })).toBeVisible();
  expect(await sinDesborde(page)).toBe(true);
  await page.screenshot({ path: 'pruebas/capturas/rf17-ver-320.png', fullPage: true });
});

test('ver: 404 dice que la version ya no existe y vuelve a textos', async ({ page }) => {
  const consola = vigilarConsola(page);
  await admin(page, { version: (r) => r.fulfill(errorApi(404, 'no_encontrado')) });
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=9.9.9');
  await expect(visible(page, 'Esa versión ya no existe: se retiró o el enlace está mal.')).toBeVisible();
  await expect(page.locator('.aviso-accion', { hasText: 'Volver a textos' })).toHaveAttribute('href', '/app/textos');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-ver-404-1440.png', fullPage: true });
  expect(consola).toEqual([]);
});

for (const url of ['/app/textos/ver?tipo=../../x&version=1.0.0', '/app/textos/ver?tipo=terminos_uso&version=../../perfil', '/app/textos/ver']) {
  test(`ver: ${url} no llega a la API y es "ya no existe"`, async ({ page }) => {
    const v = await admin(page);
    await page.goto(url);
    await expect(visible(page, 'Esa versión ya no existe: se retiró o el enlace está mal.')).toBeVisible();
    expect(v.versiones).toEqual([]);
  });
}

for (const f of fallos) {
  test(`ver: respuesta ${f.n} al cargar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await admin(page, { version: f.r });
    await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
    await expect(page.getByRole('main')).toContainText(f.texto);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('ver: Reintentar recupera el texto y lleva el foco al titulo del panel', async ({ page }) => {
  let falla = true;
  await admin(page, { version: (r) => (falla ? r.fulfill(errorApi(503, 'servicio_no_disponible')) : r.fulfill(json(200, texto()))) });
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  falla = false;
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('heading', { level: 3, name: 'Términos' })).toBeVisible();
});

test('ver: carga con aria-busy mientras la API tarda', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await admin(page, { version: async (r) => { await llega; await r.fulfill(json(200, texto())); } });
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByText('Cargando…')).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(1);
  soltar();
  await expect(page.getByRole('heading', { level: 3, name: 'Términos' })).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('ver: avisa que necesita JavaScript', async ({ page }) => {
    await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
    await expect(page.locator('noscript .aviso-titulo')).toHaveText('Esta sección necesita JavaScript');
    await expect(page.getByText('Cargando…')).toBeHidden();
  });
});

// --- Prellenado ---
for (const t of tamanos) {
  test(`editor: prellenado con la vigente, resumenes y vista previa a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const v = await admin(page);
    await page.goto(EDITAR);
    await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
    await expect(page.locator('[name="resumen_registro"]')).toHaveValue('Reglas de uso.');
    await expect(page.getByLabel(/^Resumen de cambios/)).toHaveValue(''); // llega vacio: describe el cambio nuevo
    await expect(page.getByText('Parte de la versión 1.0.0. Cambia solo lo necesario.')).toBeVisible();
    await expect(page.getByText('Texto completo en Markdown: # para títulos y - para listas. Puedes cargar un archivo .md en UTF-8 de hasta 200 KB; reemplaza el contenido.')).toBeVisible();
    // La vista previa se genera sola con ese contenido.
    await expect(previa(page).getByRole('heading', { level: 4, name: 'Previa' })).toBeVisible();
    await expect(previa(page)).toContainText('# Términos');
    expect(v.previas).toHaveLength(1);
    expect(v.previas[0].cuerpo).toEqual({ contenido: '# Términos\n\nTexto base.' });
    expect(v.versiones).toEqual(['terminos_uso/versiones/1.0.0']);
    await expect(previa(page).getByText('DESACTUALIZADA')).toBeHidden();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    expect(await sinDesborde(page)).toBe(true);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf17-editor-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('editor: 1440 deja CONTENIDO y VISTA PREVIA en dos columnas del mismo alto; 390 la pone bajo CONTENIDO y antes de los resumenes', async ({ page }) => {
  await admin(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(EDITAR);
  await expect(previa(page)).toBeVisible();
  const caja = async (loc) => loc.evaluate((e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, b: r.bottom }; });
  const area = await caja(page.locator('.textos-columna').first());
  const vista = await caja(page.locator('.textos-columna-previa'));
  expect(vista.x).toBeGreaterThan(area.x + area.w - 2);
  expect(Math.abs(vista.h - area.h)).toBeLessThan(2);
  expect(Math.abs(vista.w - area.w)).toBeLessThan(2);
  await page.setViewportSize({ width: 390, height: 844 });
  const lineal = await page.evaluate(() => {
    const y = (s) => document.querySelector(s).getBoundingClientRect().top;
    return [y('textarea[name="contenido"]'), y('[data-previa]'), y('[data-contextos]')];
  });
  expect(lineal[0]).toBeLessThan(lineal[1]);
  expect(lineal[1]).toBeLessThan(lineal[2]);
});

test('editor: 320 px no desborda', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  expect(await sinDesborde(page)).toBe(true);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-320.png', fullPage: true });
});

test('editor: con programada el prellenado sale de la vigente, no de la programada', async ({ page }) => {
  const v = await admin(page, { lista: [...LISTA, PROGRAMADA] });
  await page.goto(EDITAR);
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
  expect(v.versiones).toEqual(['terminos_uso/versiones/1.0.0']);
  await expect(page.getByText('1.1.0', { exact: true })).toBeVisible(); // la ULTIMA VERSION sigue siendo la programada
});

test('editor: un texto sin versiones llega vacio, sin ayuda de partida y sin llamadas', async ({ page }) => {
  const v = await admin(page, { lista: [] });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await expect(contenido(page)).toHaveValue('');
  await expect(page.getByText(/^Parte de la versión/)).toBeHidden();
  await expect(previa(page)).toContainText('Escribe el contenido para ver la vista previa.');
  expect(v.versiones).toEqual([]);
  expect(v.previas).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-vacio-1440.png', fullPage: true });
});

test('editor: mientras carga el prellenado los campos de P2 estan deshabilitados y avisa', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await admin(page, { version: async (r) => { await llega; await r.fulfill(json(200, texto())); } });
  await page.goto(EDITAR);
  await expect(page.getByText('Cargando la versión 1.0.0…')).toBeVisible();
  await expect(page.getByText('Cargando la versión 1.0.0…')).toHaveAttribute('aria-busy', 'true');
  await expect(contenido(page)).toBeDisabled();
  await expect(page.locator('[name="resumen_registro"]')).toBeDisabled();
  await expect(actualizar(page)).toBeDisabled();
  await expect(carga(page)).toBeDisabled();
  await sinViolaciones(page);
  soltar();
  await expect(contenido(page)).toBeEnabled();
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
  await expect(page.getByText('Cargando la versión 1.0.0…')).toBeHidden();
});

test('editor: si falla el prellenado avisa y Reintentar lo recupera', async ({ page }) => {
  const consola = vigilarConsola(page);
  let falla = true;
  await admin(page, { version: (r) => (falla ? r.fulfill(errorApi(503, 'servicio_no_disponible')) : r.fulfill(json(200, texto()))) });
  await page.goto(EDITAR);
  await expect(aviso(page, 'No pudimos cargar la versión 1.0.0 para partir de ella')).toBeVisible();
  await expect(contenido(page)).toBeEnabled(); // se puede escribir igual
  await expect(contenido(page)).toHaveValue('');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-prellenado-error-1440.png', fullPage: true });
  falla = false;
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
  await expect(aviso(page, 'No pudimos cargar')).toHaveCount(0);
  expect(consola).toEqual([]);
});

// --- Cargar archivo .md ---
test('archivo: el control es un label visible de un input sin name que no viaja con el formulario', async ({ page }) => {
  await admin(page);
  await page.goto(EDITAR);
  const entrada = carga(page);
  await expect(entrada).toHaveAttribute('accept', '.md,text/markdown');
  expect(await entrada.getAttribute('name')).toBeNull();
  await expect(page.locator('label[for="carga-md"]')).toBeVisible();
  await expect(entrada).toHaveAccessibleDescription(/Puedes cargar un archivo \.md en UTF-8 de hasta 200 KB/);
  // El foco del teclado se ve en el label.
  await entrada.focus();
  const anillo = await page.locator('label[for="carga-md"]').evaluate((e) => getComputedStyle(e).outlineStyle);
  expect(anillo).not.toBe('none');
});

const ERRORES_ARCHIVO = [
  ['de otro tipo', archivo('notas.txt', 'hola', 'text/plain'), 'notas.txt no es un archivo .md. Elige un archivo Markdown.'],
  ['con extension en mayusculas pero de otro tipo', archivo('NOTAS.MD.pdf', 'hola', 'application/pdf'), 'NOTAS.MD.pdf no es un archivo .md. Elige un archivo Markdown.'],
  ['mayor de 200 KB', archivo('grande.md', 'a'.repeat(350000)), 'grande.md pesa 350 KB; el máximo es 200 KB.'],
  ['de 200 001 bytes', archivo('limite.md', 'a'.repeat(200001)), 'limite.md pesa 201 KB; el máximo es 200 KB.'],
  ['vacio', archivo('vacio.md', ''), 'vacio.md está vacío.'],
  ['solo con espacios', archivo('blanco.md', '  \n \n'), 'blanco.md está vacío.'],
  ['que no es UTF-8', archivo('latin.md', Buffer.from([0x48, 0xe9, 0x6c, 0x6c, 0xff, 0x28])), 'latin.md no está en UTF-8. Guárdalo con codificación UTF-8 y vuelve a cargarlo.'],
];
for (const [nombre, f, mensaje] of ERRORES_ARCHIVO) {
  test(`archivo: ${nombre} da su error y no cambia CONTENIDO`, async ({ page }) => {
    const consola = vigilarConsola(page);
    const v = await admin(page);
    await page.goto(EDITAR);
    await expect(previa(page)).toContainText('# Términos');
    await carga(page).setInputFiles(f);
    const error = page.getByRole('alert').filter({ hasText: mensaje });
    await expect(error).toBeVisible();
    await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
    await expect(page.locator('[data-confirmar-reemplazo]')).toBeHidden();
    await expect(carga(page)).toHaveAttribute('aria-invalid', 'true');
    await expect(carga(page)).toHaveAccessibleDescription(new RegExp(mensaje.slice(0, 20).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    expect(v.previas).toHaveLength(1); // solo la del prellenado
    expect(consola).toEqual([]);
  });
}

test('archivo: un error se limpia al elegir un archivo valido y se ve bien (axe y captura)', async ({ page }) => {
  await admin(page, { lista: [] });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await carga(page).setInputFiles(archivo('notas.txt', 'hola', 'text/plain'));
  await expect(page.getByRole('alert').filter({ hasText: 'notas.txt no es un archivo .md.' })).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-archivo-error-1440.png', fullPage: true });
  await carga(page).setInputFiles(archivo('bueno.md', '# Bueno'));
  await expect(page.getByRole('alert').filter({ hasText: 'notas.txt' })).toBeHidden();
  await expect(carga(page)).not.toHaveAttribute('aria-invalid', 'true');
});

test('archivo: con CONTENIDO vacio reemplaza sin preguntar, sin BOM, con foco en CONTENIDO y vista previa sola', async ({ page }) => {
  const v = await admin(page, { lista: [] });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await carga(page).setInputFiles(archivo('nuevo.md', Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from('# Ñandú\n\nTexto con tilde: áéí.', 'utf-8')])));
  await expect(contenido(page)).toHaveValue('# Ñandú\n\nTexto con tilde: áéí.');
  await expect(contenido(page)).toBeFocused();
  await expect(page.locator('[data-confirmar-reemplazo]')).toBeHidden();
  await expect(previa(page)).toContainText('# Ñandú');
  expect(v.previas).toHaveLength(1);
  await expect(page.getByRole('status').filter({ hasText: 'Contenido reemplazado por nuevo.md. Vista previa actualizada.' })).toHaveCount(1);
  // El input se vacia: se puede volver a elegir el mismo archivo.
  expect(await carga(page).inputValue()).toBe('');
  await carga(page).setInputFiles(archivo('nuevo.md', '# Otra vez'));
  await expect(page.locator('[data-confirmar-reemplazo]')).toBeVisible();
});

test('archivo: el archivo se lee en el navegador y no se envia a ninguna parte', async ({ page }) => {
  const v = await admin(page, { lista: [] });
  const peticiones = [];
  page.on('request', (r) => r.method() !== 'GET' && peticiones.push(r.postData() ?? ''));
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await carga(page).setInputFiles(archivo('nuevo.md', '# Secreto'));
  await expect(contenido(page)).toHaveValue('# Secreto');
  expect(peticiones.every((p) => !p.includes('filename') && !p.includes('multipart'))).toBe(true);
  expect(v.publicaciones).toHaveLength(0);
});

test('archivo: con texto escrito pide confirmar; el foco va al titulo del aviso', async ({ page }) => {
  const v = await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await carga(page).setInputFiles(archivo('nuevo.md', '# Nuevo texto'));
  const titulo = page.getByText('¿Reemplazar el contenido por nuevo.md?');
  await expect(titulo).toBeVisible();
  await expect(titulo).toBeFocused();
  await expect(page.getByText('Se pierde lo que hay escrito en CONTENIDO.')).toBeVisible();
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.'); // todavia no cambia
  await expect(page.getByRole('button', { name: 'Reemplazar contenido' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mantener lo escrito' })).toBeVisible();
  expect(v.previas).toHaveLength(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-confirmar-1440.png', fullPage: true });
});

test('archivo: "Mantener lo escrito" no cambia nada y devuelve el foco a "Cargar archivo .md"', async ({ page }) => {
  const v = await admin(page);
  await page.goto(EDITAR);
  await carga(page).setInputFiles(archivo('nuevo.md', '# Nuevo texto'));
  await page.getByRole('button', { name: 'Mantener lo escrito' }).click();
  await expect(page.locator('[data-confirmar-reemplazo]')).toBeHidden();
  await expect(carga(page)).toBeFocused();
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
  expect(v.previas).toHaveLength(1);
});

test('archivo: "Reemplazar contenido" reemplaza, enfoca CONTENIDO, actualiza la vista previa y deja los resumenes', async ({ page }) => {
  const v = await admin(page);
  await page.goto(EDITAR);
  await page.locator('[name="resumen_registro"]').fill('Mi resumen.');
  await carga(page).setInputFiles(archivo('nuevo.md', '# Nuevo texto'));
  await page.getByRole('button', { name: 'Reemplazar contenido' }).click();
  await expect(contenido(page)).toHaveValue('# Nuevo texto');
  await expect(contenido(page)).toBeFocused();
  await expect(page.locator('[data-confirmar-reemplazo]')).toBeHidden();
  await expect(previa(page)).toContainText('# Nuevo texto');
  await expect(page.locator('[name="resumen_registro"]')).toHaveValue('Mi resumen.');
  expect(v.previas.map((p) => p.cuerpo.contenido)).toEqual(['# Términos\n\nTexto base.', '# Nuevo texto']);
});

test('archivo: el teclado llega al control, lo abre con Enter y recorre la confirmacion', async ({ page }) => {
  await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await carga(page).focus();
  await page.keyboard.press('Tab');
  await expect(actualizar(page)).toBeFocused();
  await carga(page).setInputFiles(archivo('nuevo.md', '# Nuevo texto'));
  await expect(page.getByText('¿Reemplazar el contenido por nuevo.md?')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Mantener lo escrito' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Reemplazar contenido' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(contenido(page)).toHaveValue('# Nuevo texto');
});

// --- Vista previa ---
test('previa: actualizando mantiene la anterior con aria-busy, el boton en Carga y anuncia al terminar', async ({ page }) => {
  let soltar;
  let n = 0;
  await admin(page, {
    previa: async (r) => {
      if (++n > 1) await new Promise((ok) => (soltar = ok));
      await previaPorDefecto(r);
    },
  });
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await contenido(page).fill('# Escrito de nuevo');
  await expect(previa(page).getByText('DESACTUALIZADA')).toBeVisible(); // texto, no solo color
  await actualizar(page).click();
  await expect(page.getByRole('button', { name: 'Actualizando…' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Actualizando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(previa(page)).toHaveAttribute('aria-busy', 'true');
  await expect(previa(page)).toContainText('# Términos'); // la vista anterior sigue
  await expect(page.getByRole('button', { name: 'Revisar y publicar' })).toBeDisabled();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-actualizando-1440.png', fullPage: true });
  soltar();
  await expect(previa(page)).toContainText('# Escrito de nuevo');
  await expect(previa(page)).not.toHaveAttribute('aria-busy', 'true');
  await expect(previa(page).getByText('DESACTUALIZADA')).toBeHidden();
  await expect(page.getByRole('status').filter({ hasText: 'Vista previa actualizada.' })).toHaveCount(1);
  await expect(actualizar(page)).toBeEnabled();
});

test('previa: escribir no llama a la API ni anuncia, solo marca DESACTUALIZADA', async ({ page }) => {
  const v = await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  const antes = await page.locator('[data-anuncio]').textContent();
  await contenido(page).pressSequentially(' mas', { delay: 5 });
  await expect(previa(page).getByText('DESACTUALIZADA')).toBeVisible();
  expect(v.previas).toHaveLength(1);
  expect(await page.locator('[data-anuncio]').textContent()).toBe(antes);
  await contenido(page).fill('# Términos\n\nTexto base.'); // vuelve al mismo texto
  await expect(previa(page).getByText('DESACTUALIZADA')).toBeHidden();
});

test('previa: sin generar pide pulsar el boton; vacio y de mas de 300 000 caracteres no llaman a la API', async ({ page }) => {
  const v = await admin(page, { lista: [] });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await expect(previa(page)).toContainText('Escribe el contenido para ver la vista previa.');
  await contenido(page).fill('# Algo');
  await expect(previa(page)).toContainText('Pulsa «Actualizar vista previa» para ver el texto con su formato final.');
  await contenido(page).fill('   ');
  await actualizar(page).click();
  await expect(previa(page)).toContainText('Escribe el contenido para ver la vista previa.');
  await contenido(page).evaluate((e) => { e.value = 'a'.repeat(300001); e.dispatchEvent(new Event('input', { bubbles: true })); });
  await actualizar(page).click();
  await expect(previa(page)).toContainText('El contenido supera los 300 000 caracteres. Acórtalo para verlo y publicarlo.');
  expect(v.previas).toHaveLength(0);
  await contenido(page).evaluate((e) => { e.value = 'a'.repeat(300000); e.dispatchEvent(new Event('input', { bubbles: true })); });
  await actualizar(page).click(); // exactamente 300 000: si va
  await expect(previa(page).getByRole('heading', { level: 4, name: 'Previa' })).toBeVisible();
  expect(v.previas).toHaveLength(1);
  await sinViolaciones(page);
});

const ERRORES_PREVIA = [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), t: 'Tu sesión no es válida. Inicia sesión y vuelve a intentarlo.', enlace: true, reintentar: true },
  { n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), t: 'Tu cuenta ya no puede publicar textos.', reintentar: false },
  { n: '422', r: (r) => r.fulfill(errorApi(422, 'datos_invalidos')), t: 'El contenido supera los 300 000 caracteres. Acórtalo para verlo y publicarlo.', reintentar: false },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), t: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), t: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), t: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
  { n: 'sin contenido_html', r: (r) => r.fulfill(json(200, {})), t: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];
for (const e of ERRORES_PREVIA) {
  test(`previa: ${e.n} muestra su error en el bloque y conserva la anterior con DESACTUALIZADA`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = false;
    await admin(page, { previa: (r) => (falla ? e.r(r) : previaPorDefecto(r)) });
    await page.goto(EDITAR);
    await expect(previa(page)).toContainText('# Términos');
    await contenido(page).fill('# Cambiado');
    falla = true;
    await actualizar(page).click();
    const bloque = previa(page).locator('.aviso-error');
    await expect(bloque).toContainText(e.t);
    await expect(previa(page)).toContainText('# Términos'); // la ultima vista se conserva
    await expect(previa(page).getByText('DESACTUALIZADA')).toBeVisible();
    await expect(contenido(page)).toHaveValue('# Cambiado'); // lo escrito no se toca
    await expect(bloque.getByRole('button', { name: 'Reintentar' })).toHaveCount(e.reintentar ? 1 : 0);
    if (e.enlace) {
      const acceso = bloque.getByRole('link', { name: 'Ir al acceso interno' });
      await expect(acceso).toHaveAttribute('target', '_blank');
      await expect(acceso).toHaveAttribute('rel', 'noopener');
      await expect(acceso).toHaveAttribute('href', /^\/acceso\/interno\?volver=/);
    }
    await expect(actualizar(page)).toBeEnabled();
    await expect(page.locator('[data-anuncio]')).toContainText(e.t.slice(0, 20));
    await sinViolaciones(page);
    if (['401', '503'].includes(e.n)) await page.screenshot({ path: `pruebas/capturas/rf17-editor-previa-${e.n}-1440.png`, fullPage: true });
    if (e.reintentar) {
      falla = false;
      await bloque.getByRole('button', { name: 'Reintentar' }).click();
      await expect(previa(page)).toContainText('# Cambiado');
      await expect(previa(page).locator('.aviso-error')).toHaveCount(0);
      await expect(previa(page).getByText('DESACTUALIZADA')).toBeHidden();
    }
    expect(consola).toEqual([]);
  });
}

test('previa: un error en el bloque a 320 px no desborda', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  let falla = false;
  await admin(page, { previa: (r) => (falla ? r.fulfill(errorApi(401, 'no_autenticado')) : previaPorDefecto(r)) });
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await contenido(page).fill('# Cambiado');
  falla = true;
  await actualizar(page).click();
  await expect(previa(page).locator('.aviso-error')).toBeVisible();
  expect(await sinDesborde(page)).toBe(true);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-previa-error-320.png', fullPage: true });
});

// --- R1 con formato final ---
const llenar = async (page) => {
  await page.getByRole('radio', { name: /^Menor/ }).check();
  await page.getByLabel(/^Vigente desde/).fill('2026-12-10');
};

test('R1: muestra el texto con formato final (no como texto plano) y no pide otra vista previa si corresponde', async ({ page }) => {
  const consola = vigilarConsola(page);
  const v = await admin(page, { previa: (r) => r.fulfill(json(200, { contenido_html: '<h1>Título final</h1><p>Texto <a href="https://bugalu.studio/y">enlace</a></p><h2>Sub</h2>' })) });
  await page.goto(EDITAR);
  await expect(previa(page).getByRole('heading', { level: 4, name: 'Título final' })).toBeVisible();
  await llenar(page);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByRole('heading', { level: 2, name: /R1 revisa antes de publicar/i })).toBeFocused();
  const region = page.getByRole('region', { name: 'Contenido' });
  await expect(region).toHaveAttribute('tabindex', '0');
  await expect(region.getByRole('heading', { level: 3, name: 'Título final' })).toBeVisible();
  await expect(region.getByRole('heading', { level: 4, name: 'Sub' })).toBeVisible();
  await expect(region).not.toContainText('# ');
  const enlace = region.getByRole('link', { name: /enlace/ });
  await expect(enlace).toHaveAttribute('target', '_blank');
  await expect(enlace).toHaveAccessibleName('enlace (se abre en otra pestaña)');
  expect(v.previas).toHaveLength(1); // la del prellenado: corresponde, no se repite
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-revision-1440.png', fullPage: true });
  // Se publica el Markdown, no el HTML.
  await page.getByRole('button', { name: 'Publicar versión', exact: true }).click();
  await page.waitForURL('**/app/textos?aviso=version-publicada**');
  expect(v.publicaciones[0].cuerpo.contenido).toBe('# Términos\n\nTexto base.');
  expect(JSON.stringify(v.publicaciones[0].cuerpo)).not.toContain('contenido_html');
  expect(consola).toEqual([]);
});

test('R1: "Volver a editar" conserva contenido y vista previa', async ({ page }) => {
  await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await llenar(page);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await page.getByRole('button', { name: 'Volver a editar' }).click();
  await expect(contenido(page)).toHaveValue('# Términos\n\nTexto base.');
  await expect(previa(page)).toContainText('# Términos');
  await expect(page.getByRole('button', { name: 'Revisar y publicar' })).toBeFocused();
});

test('R1: si la vista previa no corresponde al contenido la pide antes (Preparando revisión…) y muestra lo que se vio', async ({ page }) => {
  let soltar;
  let n = 0;
  const v = await admin(page, { previa: async (r) => { if (++n > 1) await new Promise((ok) => (soltar = ok)); await previaPorDefecto(r); } });
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await contenido(page).fill('# Editado a mano');
  await llenar(page);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByRole('button', { name: 'Preparando revisión…' })).toBeDisabled();
  await expect(page.getByRole('heading', { level: 2, name: /R1/ })).toHaveCount(0);
  soltar();
  await expect(page.getByRole('heading', { level: 2, name: /R1 revisa antes de publicar/i })).toBeFocused();
  await expect(page.getByRole('region', { name: 'Contenido' })).toContainText('# Editado a mano');
  expect(v.previas.map((p) => p.cuerpo.contenido)).toEqual(['# Términos\n\nTexto base.', '# Editado a mano']);
  await page.getByRole('button', { name: 'Volver a editar' }).click();
  await expect(previa(page)).toContainText('# Editado a mano'); // la vista previa del bloque tambien se actualizo
  await expect(previa(page).getByText('DESACTUALIZADA')).toBeHidden();
});

for (const e of ERRORES_PREVIA.filter((x) => x.n !== 'sin contenido_html')) {
  test(`R1: ${e.n} al pedir la vista previa no abre la revision y avisa sobre el formulario`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = false;
    const v = await admin(page, { previa: (r) => (falla ? e.r(r) : previaPorDefecto(r)) });
    await page.goto(EDITAR);
    await expect(previa(page)).toContainText('# Términos');
    await contenido(page).fill('# Editado a mano');
    await llenar(page);
    falla = true;
    await page.getByRole('button', { name: 'Revisar y publicar' }).click();
    const error = page.locator('[data-avisos] .aviso-error');
    await expect(error).toContainText(e.t.replace('verlo y publicarlo', 'publicarlo'));
    await expect(error).toBeFocused();
    await expect(page.getByRole('heading', { level: 2, name: /R1/ })).toHaveCount(0);
    await expect(contenido(page)).toHaveValue('# Editado a mano');
    await expect(page.getByRole('button', { name: 'Revisar y publicar' })).toBeEnabled();
    expect(v.publicaciones).toHaveLength(0);
    await sinViolaciones(page);
    if (e.n === '503') await page.screenshot({ path: 'pruebas/capturas/rf17-editor-revision-503-1440.png', fullPage: true });
    if (e.n === '401') await expect(error.getByRole('link', { name: 'Ir al acceso interno' })).toHaveAttribute('target', '_blank');
    expect(consola).toEqual([]);
  });
}

test('R1: Reintentar de la revision vuelve a pedirla y la abre', async ({ page }) => {
  let falla = false;
  await admin(page, { previa: (r) => (falla ? r.fulfill(errorApi(503, 'servicio_no_disponible')) : previaPorDefecto(r)) });
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await contenido(page).fill('# Editado a mano');
  await llenar(page);
  falla = true;
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.locator('[data-avisos] .aviso-error')).toBeVisible();
  falla = false;
  await page.locator('[data-avisos]').getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('heading', { level: 2, name: /R1 revisa antes de publicar/i })).toBeFocused();
});

test('R1: contenido de mas de 300 000 caracteres da su error de validacion y no llama a la API', async ({ page }) => {
  const v = await admin(page, { lista: [] });
  await page.goto('/app/textos/publicar?tipo=declaracion_agrupacion');
  await page.getByRole('radio', { name: /^Mayor/ }).check();
  await page.getByLabel(/^Vigente desde/).fill('2026-11-20');
  await page.locator('[name="resumen_registro"]').fill('Resumen.');
  await contenido(page).evaluate((e) => { e.value = 'a'.repeat(300001); e.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByText('El contenido supera los 300 000 caracteres. Acórtalo para publicarlo.')).toBeVisible();
  await expect(contenido(page)).toHaveAttribute('aria-invalid', 'true');
  expect(v.previas).toHaveLength(0);
});

test('R1: a 320 px no desborda', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await admin(page);
  await page.goto(EDITAR);
  await expect(previa(page)).toContainText('# Términos');
  await llenar(page);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  await expect(page.getByRole('region', { name: 'Contenido' })).toBeVisible();
  expect(await sinDesborde(page)).toBe(true);
  await page.screenshot({ path: 'pruebas/capturas/rf17-editor-revision-320.png', fullPage: true });
});

// --- Retoques de auditoria ---
test('prellenado: si fallo y el Administrador escribio, Reintentar no pisa lo escrito', async ({ page }) => {
  let falla = true;
  await admin(page, { version: (r) => (falla ? r.fulfill(errorApi(503, 'servicio_no_disponible')) : r.fulfill(json(200, texto()))) });
  await page.goto(EDITAR);
  await expect(aviso(page, 'No pudimos cargar la versión 1.0.0')).toBeVisible();
  await contenido(page).fill('# Lo mío');
  await page.locator('[name="resumen_registro"]').fill('Mi resumen.');
  falla = false;
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(aviso(page, 'No pudimos cargar')).toHaveCount(0);
  await expect(page.getByText('Parte de la versión 1.0.0.')).toBeVisible();
  await expect(contenido(page)).toHaveValue('# Lo mío');
  await expect(page.locator('[name="resumen_registro"]')).toHaveValue('Mi resumen.');
});

const HOSTIL = '<h2>Ok</h2><script>window.__xss = 1</script><img src="x" onerror="window.__xss = 2"><a href="javascript:window.__xss=3" onclick="window.__xss=4">mal</a>';
const limpio = async (page, zona) => {
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  await expect(zona.locator('script')).toHaveCount(0);
  await expect(zona.locator('[onerror], [onclick]')).toHaveCount(0);
  await expect(zona.locator('a[href^="javascript"]')).toHaveCount(0);
};
test('xss: Ver no ejecuta ni conserva HTML hostil', async ({ page }) => {
  await admin(page, { version: (r) => r.fulfill(json(200, texto({ contenido_html: HOSTIL }))) });
  await page.goto('/app/textos/ver?tipo=terminos_uso&version=1.0.0');
  await expect(page.getByRole('region', { name: /V3 Texto/i }).getByRole('heading', { name: 'Ok' })).toBeVisible();
  await limpio(page, page.getByRole('region', { name: /V3 Texto/i }));
});
test('xss: vista previa y R1 no ejecutan ni conservan HTML hostil', async ({ page }) => {
  await admin(page, { version: (r) => r.fulfill(json(200, texto())), previa: (r) => r.fulfill(json(200, { contenido_html: HOSTIL })) });
  await page.goto(EDITAR);
  await expect(previa(page).getByRole('heading', { name: 'Ok' })).toBeVisible();
  await limpio(page, previa(page));
  await llenar(page);
  await page.getByRole('button', { name: 'Revisar y publicar' }).click();
  const region = page.getByRole('region', { name: 'Contenido' });
  await expect(region.getByRole('heading', { name: 'Ok' })).toBeVisible();
  await limpio(page, region);
});
