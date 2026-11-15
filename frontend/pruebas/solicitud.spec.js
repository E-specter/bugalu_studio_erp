import { test, expect } from '@playwright/test';
import { API, SB, json, errorApi, sesion, simularAuth, conSesion, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const MIA = `${API}/solicitudes-acceso/mia`;
const RUTA = '/acceso/interno/solicitud';
const datos = (extra = {}) => ({ id: 's1', id_usuario: 'u1', nombre: 'Luis Mora', correo: 'luis@correo.com', especialidad: 'Ingeniería de mezcla', mensaje: 'Me invitó Ana.', estado: 'pendiente', motivo: null, creada_en: '2026-11-10T10:00:00Z', revisada_en: null, ...extra });

test.beforeEach(async ({ page }) => conSesion(page));

const estados = [
  { n: 'pendiente', r: (r) => r.fulfill(json(200, datos())), texto: ['Pendiente', 'El Administrador aún no revisa tu solicitud. Cuando la apruebe, entrarás al panel con tu correo y contraseña.', 'Ingeniería de mezcla', 'Me invitó Ana.', '10 nov 2026'], boton: 'Comprobar estado' },
  { n: 'rechazada', r: (r) => r.fulfill(json(200, datos({ estado: 'rechazada', motivo: 'Aún no abrimos plazas.', revisada_en: '2026-11-12T10:00:00Z' }))), texto: ['Rechazada', 'Motivo', 'Aún no abrimos plazas.', '12 nov 2026', 'Si algo cambió, puedes enviar otra solicitud.'], boton: 'Enviar otra solicitud', rol: 'link' },
  { n: 'sin-solicitud', r: (r) => r.fulfill(errorApi(404, 'no_encontrado')), texto: ['Tu cuenta aún no tiene una solicitud de acceso al panel.'], boton: 'Enviar solicitud', formulario: true },
  { n: 'no-autenticado', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: ['Tu sesión no es válida. Inicia sesión para ver tu solicitud.'], enlace: 'Ir al acceso interno' },
  { n: 'sin-permiso', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: ['Sin permiso. No tienes permiso para ver esta solicitud.'], reintentar: true },
  { n: 'servicio-no-disponible', r: (r) => r.fulfill(errorApi(503, 'autenticacion_no_disponible')), texto: ['El servicio de acceso no responde. Inténtalo de nuevo en unos minutos.'], reintentar: true },
  { n: 'sin-conexion', r: (r) => r.abort('connectionrefused'), texto: ['No hay conexión con el servidor. Revisa tu red e inténtalo de nuevo.'], reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: ['No pudimos cargar tu solicitud'], reintentar: true },
];

for (const e of estados) {
  for (const t of tamanos) {
    test(`estado ${e.n} a ${t.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await page.route(MIA, e.r);
      await page.goto(RUTA);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Tu solicitud');
      for (const x of e.texto) await expect(page.getByRole('main')).toContainText(x);
      await expect(page.locator('[aria-busy]')).toHaveCount(0);
      if (e.boton) await expect(page.getByRole(e.rol ?? 'button', { name: e.boton })).toBeVisible();
      if (e.enlace) await expect(page.getByRole('link', { name: e.enlace })).toHaveAttribute('href', '/acceso/interno');
      if (e.reintentar) await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
      if (e.formulario) await expect(page.getByLabel('Especialidad', { exact: true })).toBeVisible();
      else await expect(page.getByLabel('Especialidad', { exact: true })).toHaveCount(0);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/solicitud-${e.n}-${t.nombre}.png`, fullPage: true });
    });
  }
}

test('estado fuera de la lista cerrada: respuesta inesperada con Reintentar, sin TypeError', async ({ page }) => {
  const consola = vigilarConsola(page);
  await page.route(MIA, (r) => r.fulfill(json(200, datos({ estado: 'archivada' }))));
  await page.goto(RUTA);
  await expect(page.getByRole('main')).toContainText('Respuesta inesperada del servidor');
  await expect(page.getByRole('main')).not.toContainText('Algo salió mal');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  expect(consola).toEqual([]);
});

test('estado pendiente: etiqueta de estado con texto propio y una sola region viva estable', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(RUTA);
  await expect(page.locator('.etiqueta-aviso', { hasText: 'Pendiente' })).toBeVisible();
  await expect(page.locator('[data-anuncio]')).toHaveAttribute('role', 'status');
  await expect(page.locator('[data-anuncio]')).toHaveText('Solicitud pendiente');
});

test('estado rechazada: etiqueta Alerta y motivo como dd tras su dt', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos({ estado: 'rechazada', motivo: 'Sin plazas.', revisada_en: '2026-11-12T10:00:00Z' }))));
  await page.goto(RUTA);
  await expect(page.locator('.etiqueta-alerta', { hasText: 'Rechazada' })).toBeVisible();
  await expect(page.locator('dt', { hasText: 'Motivo' })).toBeVisible();
  await expect(page.locator('dt:has-text("Motivo") + dd')).toHaveText('Sin plazas.');
  await expect(page.locator('[data-anuncio]')).toHaveText('Solicitud rechazada');
});

test('el motivo y el mensaje se muestran como texto, nunca como HTML', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos({ mensaje: '<img src=x onerror=window.__xss=1>', estado: 'rechazada', motivo: '<b>negrita</b>' }))));
  await page.goto(RUTA);
  await expect(page.getByText('<b>negrita</b>')).toBeVisible();
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

test('estado aprobada: va a /app/ sin pantalla intermedia', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos({ estado: 'aprobada' }))));
  await page.route(`${API}/**`, (r) => (r.request().url() === MIA ? r.fallback() : r.fulfill(errorApi(401, 'no_autenticado'))));
  await page.goto(RUTA);
  await page.waitForURL('**/app/');
});

test('cargando: bloque con aria-busy mientras la API tarda', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await page.route(MIA, async (r) => { await llega; await r.fulfill(json(200, datos())); });
  await page.goto(RUTA);
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
  await expect(page.getByText('Cargando…')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitud-cargando-1440.png', fullPage: true });
  soltar();
  await expect(page.getByText('Ingeniería de mezcla')).toBeVisible();
});

test('Comprobar estado vuelve a pedir y enfoca el h1; el anuncio es una sola vez', async ({ page }) => {
  let n = 0;
  await page.route(MIA, (r) => r.fulfill(++n === 1 ? json(200, datos()) : json(200, datos({ estado: 'rechazada', motivo: 'No.', revisada_en: '2026-11-12T10:00:00Z' }))));
  await page.goto(RUTA);
  await expect(page.getByText('Ingeniería de mezcla')).toBeVisible();
  await page.evaluate(() => {
    window.__anuncios = 0;
    const v = document.querySelector('[data-anuncio]');
    new MutationObserver(() => v.textContent && window.__anuncios++).observe(v, { childList: true, characterData: true, subtree: true });
  });
  await page.getByRole('button', { name: 'Comprobar estado' }).click();
  await expect(page.getByText('No.', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
  expect(await page.evaluate(() => window.__anuncios)).toBe(1);
});

test('Reintentar tras 503 vuelve a pedir y muestra el estado', async ({ page }) => {
  let n = 0;
  await page.route(MIA, (r) => r.fulfill(++n === 1 ? errorApi(503, 'autenticacion_no_disponible') : json(200, datos())));
  await page.goto(RUTA);
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByText('Ingeniería de mezcla')).toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
});

test('?aviso=solicitud-enviada muestra el exito y se quita de la URL', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(`${RUTA}?aviso=solicitud-enviada`);
  await expect(page.locator('.aviso-exito')).toContainText('Solicitud enviada. El Administrador la revisará; vuelve aquí para ver su estado.');
  await expect(page).toHaveURL(/solicitud$/);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitud-enviada-1440.png', fullPage: true });
});

test('aviso desconocido no se muestra', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(`${RUTA}?aviso=otra-cosa`);
  await expect(page.getByText('Ingeniería de mezcla')).toBeVisible();
  await expect(page.locator('.aviso-exito')).toHaveCount(0);
});

test('Enviar otra solicitud abre el formulario corto sin pedir /mia y lo envia', async ({ page }) => {
  let mias = 0;
  let cuerpo;
  await page.route(MIA, (r) => (mias++, r.fulfill(json(200, datos()))));
  await page.route(`${API}/solicitudes-acceso`, (r) => ((cuerpo = r.request().postDataJSON()), r.fulfill(json(201, datos()))));
  await page.goto(`${RUTA}?nueva=1`);
  await expect(page.getByLabel('Especialidad', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.locator('#campo-especialidad-error')).toContainText('Escribe tu especialidad, por ejemplo Ingeniería de mezcla.');
  await expect(page.getByLabel('Especialidad', { exact: true })).toBeFocused();
  await page.getByLabel('Especialidad', { exact: true }).fill('Producción');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await page.waitForURL(`**${RUTA}`);
  expect(cuerpo).toEqual({ especialidad: 'Producción' });
  await expect.poll(() => mias).toBe(1); // solo despues de enviar
});

test('formulario corto: 409 va al estado, 422 muestra el error y 503 un aviso con datos conservados', async ({ page }) => {
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  const respuestas = [errorApi(503, 'autenticacion_no_disponible'), errorApi(422, 'datos_invalidos'), errorApi(409, 'conflicto')];
  await page.route(`${API}/solicitudes-acceso`, (r) => r.fulfill(respuestas.shift()));
  await page.goto(`${RUTA}?nueva=1`);
  await page.getByLabel('Especialidad', { exact: true }).fill('Producción');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.locator('[data-avisos] .aviso-error, .aviso-error').first()).toContainText('El servicio de acceso no responde');
  await expect(page.getByLabel('Especialidad', { exact: true })).toHaveValue('Producción');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.locator('#campo-especialidad-error')).toBeVisible();
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await page.waitForURL(`**${RUTA}`);
});

test('cerrar sesion: borra la sesion local y va al acceso interno con aviso (CA-12)', async ({ page }) => {
  const llamadas = await simularAuth(page, { '/logout': { status: 204, body: '' } });
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(RUTA);
  expect(await page.evaluate(() => localStorage.getItem('bugalu-sesion'))).not.toBeNull();
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.waitForURL('**/acceso/interno');
  expect(await page.evaluate(() => localStorage.getItem('bugalu-sesion'))).toBeNull();
  await expect(page.getByText('Cerraste sesión.')).toBeVisible();
  expect(llamadas.some((l) => l.ruta.includes('logout'))).toBe(true);
});

test('cerrar sesion con la red caida igual borra la sesion del navegador (CA-12)', async ({ page }) => {
  await page.route(`${SB}/logout*`, (r) => r.abort('connectionrefused'));
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(RUTA);
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.waitForURL('**/acceso/interno');
  expect(await page.evaluate(() => localStorage.getItem('bugalu-sesion'))).toBeNull();
});

test('el token no aparece en la URL ni en la consola', async ({ page }) => {
  const mensajes = [];
  page.on('console', (m) => mensajes.push(m.text()));
  await page.route(MIA, (r) => r.fulfill(json(200, datos())));
  await page.goto(RUTA);
  await expect(page.getByText('Ingeniería de mezcla')).toBeVisible();
  expect(page.url()).not.toContain(sesion().access_token);
  expect(mensajes.join('\n')).not.toContain(sesion().access_token);
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('explica que hace falta JS', async ({ page }) => {
    await page.goto(RUTA);
    const html = await page.content();
    expect(html).toContain('El acceso necesita JavaScript');
    expect(html).toContain('Actívalo en tu navegador y recarga la página.');
    await expect(page.locator('bugalu-solicitud [data-salida]')).toBeHidden();
    await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
    await page.screenshot({ path: 'pruebas/capturas/solicitud-sin-js-1440.png', fullPage: true });
  });
});
