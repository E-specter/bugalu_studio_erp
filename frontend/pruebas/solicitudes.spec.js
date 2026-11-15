// RF-01 (CA-08, CA-10, CA-13): bandeja de solicitudes y usuarios del Administrador. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const U1 = '11111111-1111-4111-8111-111111111111';
const U2 = '22222222-2222-4222-8222-222222222222';
const U3 = '33333333-3333-4333-8333-333333333333';
const sol = (id, nombre, extra = {}) => ({ id, id_usuario: `u-${id}`, nombre, correo: `${nombre.split(' ')[0].toLowerCase()}@correo.com`, especialidad: 'Ingeniería de mezcla', mensaje: 'Me invitó Luis.', estado: 'pendiente', motivo: null, creada_en: '2026-01-10T10:00:00Z', revisada_en: null, ...extra });
const usr = (id, nombre, rol, extra = {}) => ({ id, correo: `${nombre.split(' ')[0].toLowerCase()}@correo.com`, correo_confirmado: true, nombre, telefono: null, nombre_artistico: null, rol, especialidad: null, ...extra });
const PENDIENTES = [sol(U2, 'Marta Ríos', { creada_en: '2026-02-01T10:00:00Z' }), sol(U1, 'Ana Pérez')];
const USUARIOS = [usr(U1, 'Ana Pérez', 'administrador', { especialidad: 'Producción' }), usr(U2, 'Luis Mora', 'personal', { especialidad: 'asesoria' }), usr(U3, 'Eva Soto', 'cliente', { telefono: '+51999111222', nombre_artistico: 'Eva S.' })];

// Responde `metodo` + `camino` (sin query); el resto de llamadas cae en silenciarApi (401). Devuelve las peticiones vistas.
async function simular(page, metodo, camino, resp) {
  const vistas = [];
  await page.route((u) => u.pathname === `/api/v1${camino}`, (r) => {
    if (r.request().method() !== metodo) return r.fallback();
    let cuerpo = null;
    try { cuerpo = r.request().postDataJSON(); } catch {}
    vistas.push({ url: new URL(r.request().url()), cuerpo });
    return typeof resp === 'function' ? resp(r) : r.fulfill(resp);
  });
  return vistas;
}

test.beforeEach(async ({ page }) => {
  await conSesion(page);
  await silenciarApi(page);
  // El Administrador: la navegacion de las capturas es la real (Accesos, Usuarios).
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'administrador' })));
});

const vistas = {
  bandeja: { ruta: '/app/solicitudes', camino: '/solicitudes-acceso', h1: /solicitudes de acceso/i, ok: json(200, PENDIENTES) },
  usuarios: { ruta: '/app/usuarios', camino: '/usuarios', h1: /^usuarios$/i, ok: json(200, USUARIOS) },
};

// --- 1. Bandeja ---
for (const t of tamanos) {
  test(`bandeja: pendientes, la mas antigua arriba, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistasApi = await simular(page, 'GET', '/solicitudes-acceso', vistas.bandeja.ok);
    await page.goto('/app/solicitudes');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/solicitudes de acceso/i);
    await expect(page.getByText('2 pendientes')).toBeVisible();
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Accesos']);
    await expect(page.locator('.encabezado')).toContainText('[A1] EQUIPO / ACCESOS');
    await expect(page.getByRole('navigation', { name: 'Principal' }).locator('a:visible', { hasText: 'Accesos' })).toHaveAttribute('href', '/app/solicitudes/');
    const filas = page.getByRole('row');
    await expect(filas).toHaveCount(3);
    await expect(filas.nth(1)).toContainText('Ana Pérez');
    await expect(filas.nth(1)).toContainText('ana@correo.com');
    await expect(filas.nth(1)).toContainText('Ingeniería de mezcla');
    await expect(filas.nth(1)).toContainText('10 ene 2026');
    await expect(filas.nth(2)).toContainText('Marta Ríos');
    await expect(page.getByRole('link', { name: 'Revisar solicitud de Ana Pérez' })).toHaveAttribute('href', `/app/solicitudes/revisar?id=${U1}`);
    expect(vistasApi[0].url.searchParams.get('estado')).toBe('pendiente');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/solicitudes-bandeja-${t.nombre}.png`, fullPage: true });
  });
}

test('bandeja: la fecha reciente es relativa y la absoluta va en title', async ({ page }) => {
  const hace2h = new Date(Date.now() - 2 * 3600e3).toISOString();
  await simular(page, 'GET', '/solicitudes-acceso', json(200, [sol(U1, 'Ana Pérez', { creada_en: hace2h })]));
  await page.goto('/app/solicitudes');
  const hora = page.locator('time');
  await expect(hora).toHaveText('hace 2 h');
  await expect(hora).toHaveAttribute('title', /\d{4}/);
});

test('bandeja: sin pendientes explica y no ofrece accion', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, []));
  await page.goto('/app/solicitudes');
  await expect(page.locator('.vacio-titulo')).toHaveText('No hay solicitudes pendientes');
  await expect(page.getByText('Cuando alguien del equipo pida acceso desde el registro interno, aparecerá aquí.')).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-bandeja-vacia-1440.png', fullPage: true });
});

test('bandeja: nombre y mensaje del usuario se muestran como texto', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, [sol(U1, '<img src=x onerror=window.__xss=1>')]));
  await page.goto('/app/solicitudes');
  await expect(page.getByText('<img src=x onerror=window.__xss=1>').first()).toBeVisible();
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

test('bandeja: carga con aria-busy mientras la API tarda', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'GET', '/solicitudes-acceso', async (r) => { await llega; await r.fulfill(json(200, PENDIENTES)); });
  await page.goto('/app/solicitudes');
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
  await expect(page.getByText('Cargando…')).toBeVisible();
  soltar();
  await expect(page.getByRole('table')).toBeVisible();
});

const fallos = [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: 'Tu sesión no es válida. Inicia sesión para continuar.', enlace: ['Ir al acceso interno', (ruta) => `/acceso/interno?volver=${encodeURIComponent(ruta)}`] },
  { n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: 'Esta sección es solo para el Administrador.', extra: '[403]', enlace: ['Volver al inicio', () => '/app/'] },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red e inténtalo de nuevo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];
for (const [nombre, v] of Object.entries(vistas)) {
  for (const f of fallos) {
    test(`${nombre}: respuesta ${f.n} al cargar`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await simular(page, 'GET', v.camino, f.r);
      await page.goto(v.ruta);
      await expect(page.getByRole('main')).toContainText(f.texto);
      if (f.extra) await expect(page.getByRole('main')).toContainText(f.extra);
      if (f.enlace) await expect(page.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1](v.ruta));
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
      await expect(page.locator('[aria-busy]')).toHaveCount(0);
      await expect(page.getByRole('table')).toHaveCount(0);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      if (nombre === 'bandeja') await page.screenshot({ path: `pruebas/capturas/solicitudes-error-${f.n}-1440.png`, fullPage: true });
    });
  }
}

test('bandeja: Reintentar vuelve a pedir y lleva el foco al titulo del panel', async ({ page }) => {
  let n = 0;
  await simular(page, 'GET', '/solicitudes-acceso', (r) => (n++ ? r.fulfill(json(200, PENDIENTES)) : r.fulfill(errorApi(503, 'x'))));
  await page.goto('/app/solicitudes');
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('table')).toBeVisible();
  await expect(page.locator('[data-salida] .panel-titulo')).toBeFocused();
});

test('bandeja: ?aviso= de la lista cerrada se anuncia, recibe foco y se quita de la URL', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, []));
  await page.goto('/app/solicitudes?aviso=solicitud-aprobada');
  const aviso = page.locator('[data-avisos] .aviso');
  await expect(aviso).toContainText('Solicitud aprobada. La persona ya puede entrar al panel.');
  await expect(aviso).toBeFocused();
  expect(page.url()).not.toContain('aviso');
  await sinViolaciones(page);
  await page.goto('/app/solicitudes?aviso=<script>');
  await expect(page.locator('[data-avisos] .aviso')).toHaveCount(0);
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/app/solicitudes', '/app/solicitudes/revisar', '/app/usuarios', '/app/usuarios/editar']) {
    test(`${ruta} explica que hace falta JS`, async ({ page }) => {
      await page.goto(ruta);
      const html = await page.content();
      expect(html).toContain('Esta sección necesita JavaScript');
      expect(html).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-solicitudes [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      if (ruta === '/app/solicitudes') await page.screenshot({ path: 'pruebas/capturas/solicitudes-sin-js-1440.png', fullPage: true });
    });
  }
});

// --- 2. Revisar ---
const REVISAR = `/app/solicitudes/revisar?id=${U1}`;
const yaNoPendiente = 'Esta solicitud ya no está pendiente. Puede que otra persona la haya revisado.';

test('revisar: id que no es UUID no llama a la API y explica', async ({ page }) => {
  const vistasApi = await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  await page.goto('/app/solicitudes/revisar?id=../../usuarios');
  await expect(page.getByRole('main')).toContainText(yaNoPendiente);
  await expect(page.getByRole('link', { name: 'Volver a solicitudes' })).toHaveAttribute('href', '/app/solicitudes');
  expect(vistasApi).toHaveLength(0);
  await sinViolaciones(page);
});

test('revisar: id que ya no esta en la lista', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, [PENDIENTES[0]]));
  await page.goto(REVISAR);
  await expect(page.getByRole('main')).toContainText(yaNoPendiente);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-revisar-no-pendiente-1440.png', fullPage: true });
});

for (const t of tamanos) {
  test(`revisar: solicitud, aprobar y rechazar a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
    await page.goto(REVISAR);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/revisar solicitud/i);
    await expect(page.getByText('Decide si Ana Pérez entra al panel y con qué rol.')).toBeVisible();
    await expect(page.getByRole('main').locator('[aria-current="page"]')).toHaveText('Ana Pérez');
    const s1 = page.getByRole('region', { name: /solicitud/i }).first();
    await expect(s1).toContainText('Me invitó Luis.');
    await expect(s1).toContainText('ana@correo.com');
    await expect(page.getByRole('radio', { name: /Personal del estudio/ })).toBeChecked();
    await expect(page.getByRole('radio', { name: /Administrador/ })).not.toBeChecked();
    await expect(page.getByLabel('Especialidad')).toHaveValue('Ingeniería de mezcla');
    await expect(page.getByText('Para quien da asesorías, escribe asesoria.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Aprobar acceso' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Rechazar solicitud' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/solicitudes-revisar-${t.nombre}.png`, fullPage: true });
  });
}

test('revisar: orden de foco rol, especialidad, aprobar, motivo, rechazar', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  await page.goto(REVISAR);
  await page.getByRole('radio', { name: /Personal del estudio/ }).focus();
  for (const nombre of [/Especialidad/, 'Aprobar acceso', /Motivo del rechazo/, 'Rechazar solicitud']) {
    await page.keyboard.press('Tab');
    await expect(page.getByRole(nombre === 'Aprobar acceso' || nombre === 'Rechazar solicitud' ? 'button' : 'textbox', { name: nombre })).toBeFocused();
  }
});

test('revisar: aprobar envia rol y especialidad y vuelve a la bandeja con el aviso', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  const aprobar = await simular(page, 'POST', `/solicitudes-acceso/${U1}/aprobar`, json(200, sol(U1, 'Ana Pérez', { estado: 'aprobada' })));
  await page.goto(REVISAR);
  await page.getByRole('radio', { name: /Administrador/ }).check();
  await page.getByLabel('Especialidad').fill('  asesoria ');
  await page.getByRole('button', { name: 'Aprobar acceso' }).click();
  await page.waitForURL('**/app/solicitudes?aviso=solicitud-aprobada');
  expect(aprobar[0].cuerpo).toEqual({ rol: 'administrador', especialidad: 'asesoria' });
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Solicitud aprobada. La persona ya puede entrar al panel.');
});

test('revisar: aprobar sin especialidad marca el campo y no envia', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  const aprobar = await simular(page, 'POST', `/solicitudes-acceso/${U1}/aprobar`, json(200, {}));
  await page.goto(REVISAR);
  await page.getByLabel('Especialidad').fill('');
  await page.getByRole('button', { name: 'Aprobar acceso' }).click();
  const campo = page.getByLabel('Especialidad');
  await expect(campo).toBeFocused();
  await expect(campo).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText('Escribe la especialidad.')).toBeVisible();
  expect(aprobar).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-revisar-error-campo-1440.png', fullPage: true });
});

test('revisar: rechazar exige motivo y lo envia', async ({ page }) => {
  await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  const rechazar = await simular(page, 'POST', `/solicitudes-acceso/${U1}/rechazar`, json(200, sol(U1, 'Ana Pérez', { estado: 'rechazada' })));
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Rechazar solicitud' }).click();
  await expect(page.getByLabel(/Motivo del rechazo/)).toBeFocused();
  await expect(page.getByText('Escribe el motivo del rechazo.')).toBeVisible();
  expect(rechazar).toHaveLength(0);
  await page.getByLabel(/Motivo del rechazo/).fill('Aún no abrimos plazas.');
  await page.getByRole('button', { name: 'Rechazar solicitud' }).click();
  await page.waitForURL('**/app/solicitudes?aviso=solicitud-rechazada');
  expect(rechazar[0].cuerpo).toEqual({ motivo: 'Aún no abrimos plazas.' });
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Solicitud rechazada. La persona verá el motivo al entrar.');
});

test('revisar: mientras envia, el boton esta en carga y el otro formulario deshabilitado', async ({ page }) => {
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
  await simular(page, 'POST', `/solicitudes-acceso/${U1}/aprobar`, async (r) => { await llega; await r.fulfill(errorApi(503, 'x')); });
  await page.goto(REVISAR);
  await page.getByRole('button', { name: 'Aprobar acceso' }).click();
  await expect(page.getByRole('button', { name: 'Aprobando…' })).toBeDisabled();
  await expect(page.getByLabel(/Motivo del rechazo/)).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Rechazar solicitud' })).toBeDisabled();
  soltar();
  await expect(page.getByRole('button', { name: 'Aprobar acceso' })).toBeEnabled();
  await expect(page.getByLabel(/Motivo del rechazo/)).toBeEnabled();
});

const fallosEnvio = [
  { n: '404', r: errorApi(404, 'no_encontrado'), texto: yaNoPendiente },
  { n: '409', r: errorApi(409, 'conflicto'), texto: yaNoPendiente },
  { n: '401', r: errorApi(401, 'no_autenticado'), texto: 'Tu sesión no es válida. Inicia sesión para continuar.' },
  { n: '403', r: errorApi(403, 'sin_permiso'), texto: 'Esta sección es solo para el Administrador.' },
  { n: '422', r: errorApi(422, 'datos_invalidos', 'La especialidad es demasiado larga.'), texto: 'La especialidad es demasiado larga.', conserva: true },
  { n: '503', r: errorApi(503, 'x'), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', conserva: true },
  { n: 'no-json', r: { status: 500, contentType: 'text/html', body: 'x' }, texto: 'Algo salió mal. Inténtalo de nuevo.', conserva: true },
];
for (const f of fallosEnvio) {
  test(`revisar: respuesta ${f.n} al aprobar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await simular(page, 'GET', '/solicitudes-acceso', json(200, PENDIENTES));
    await simular(page, 'POST', `/solicitudes-acceso/${U1}/aprobar`, f.r);
    await page.goto(REVISAR);
    await page.getByLabel('Especialidad').fill('Mezcla');
    await page.getByRole('button', { name: 'Aprobar acceso' }).click();
    await expect(page.getByRole('main')).toContainText(f.texto);
    if (f.conserva) {
      await expect(page.locator('[data-avisos] .aviso-error')).toBeFocused();
      await expect(page.getByLabel('Especialidad')).toHaveValue('Mezcla');
      await expect(page.getByRole('button', { name: 'Aprobar acceso' })).toBeEnabled();
    }
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

// --- 3. Usuarios ---
for (const t of tamanos) {
  test(`usuarios: lista con rol y especialidad a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const api = await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
    await page.goto('/app/usuarios');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^usuarios$/i);
    await expect(page.getByRole('row')).toHaveCount(4);
    const eva = page.getByRole('row').filter({ hasText: 'Eva Soto' });
    await expect(eva).toContainText('Cliente');
    await expect(eva).toContainText('—');
    await expect(page.getByRole('row').filter({ hasText: 'Luis Mora' })).toContainText('asesoria');
    await expect(page.getByRole('link', { name: 'Cambiar rol de Luis Mora' })).toHaveAttribute('href', `/app/usuarios/editar?id=${U2}`);
    await expect(page.getByRole('link', { name: 'Todos' })).toHaveAttribute('aria-current', 'true');
    expect(api[0].url.searchParams.has('rol')).toBe(false);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/solicitudes-usuarios-${t.nombre}.png`, fullPage: true });
  });
}

test('usuarios: el filtro por rol llega a la API y se marca con check y aria-current', async ({ page }) => {
  const api = await simular(page, 'GET', '/usuarios', json(200, [USUARIOS[1]]));
  await page.goto('/app/usuarios?rol=personal');
  await expect(page.getByRole('row')).toHaveCount(2);
  expect(api[0].url.searchParams.get('rol')).toBe('personal');
  const filtro = page.getByRole('link', { name: 'Personal', exact: true });
  await expect(filtro).toHaveAttribute('aria-current', 'true');
  await expect(filtro.locator('svg')).toHaveCount(1);
  await expect(page.getByRole('link', { name: 'Todos' })).not.toHaveAttribute('aria-current', 'true');
  await expect(page.getByRole('link', { name: 'Administradores' })).toHaveAttribute('href', '/app/usuarios?rol=administrador');
});

test('usuarios: rol desconocido en la URL se ignora', async ({ page }) => {
  const api = await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
  await page.goto('/app/usuarios?rol=root');
  await expect(page.getByRole('row')).toHaveCount(4);
  expect(api[0].url.searchParams.has('rol')).toBe(false);
});

test('usuarios: sin resultados del filtro', async ({ page }) => {
  await simular(page, 'GET', '/usuarios', json(200, []));
  await page.goto('/app/usuarios?rol=cliente');
  await expect(page.getByText('No hay usuarios con ese rol.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Quitar filtros' })).toHaveAttribute('href', '/app/usuarios');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-usuarios-vacio-1440.png', fullPage: true });
});

test('usuarios: ?aviso=usuario-actualizado', async ({ page }) => {
  await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
  await page.goto('/app/usuarios?aviso=usuario-actualizado');
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Rol actualizado');
  await expect(page.locator('[data-avisos] .aviso')).toBeFocused();
});

// --- Editar usuario ---
const EDITAR = `/app/usuarios/editar?id=${U2}`;
const preparar = async (page, yo = U1) => {
  await simular(page, 'GET', '/usuarios', json(200, USUARIOS));
  await simular(page, 'GET', '/perfil', perfil({ id: yo }));
};

test('editar: id invalido o desconocido', async ({ page }) => {
  await preparar(page);
  await page.goto('/app/usuarios/editar?id=1');
  await expect(page.getByRole('main')).toContainText('No encontramos este usuario.');
  await page.goto(`/app/usuarios/editar?id=${'4'.repeat(8)}-4444-4444-8444-${'4'.repeat(12)}`);
  await expect(page.getByRole('main')).toContainText('No encontramos este usuario.');
  await expect(page.getByRole('link', { name: 'Volver a usuarios' })).toHaveAttribute('href', '/app/usuarios');
});

for (const t of tamanos) {
  test(`editar: datos de la persona, rol y especialidad a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await preparar(page);
    await page.goto(EDITAR);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/cambiar rol/i);
    await expect(page.getByText('El rol decide qué ve Luis Mora en el sistema.')).toBeVisible();
    await expect(page.getByRole('region', { name: /persona/i })).toContainText('luis@correo.com');
    await expect(page.getByRole('radio', { name: /Personal del estudio/ })).toBeChecked();
    await expect(page.getByRole('radio', { name: /Cliente/ })).not.toBeChecked();
    await expect(page.getByRole('textbox', { name: 'Especialidad' })).toHaveValue('asesoria');
    await expect(page.getByText('Déjala vacía si es cliente.')).toBeVisible();
    await expect(page.getByText('Estás cambiando tu propio rol.')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/solicitudes-editar-${t.nombre}.png`, fullPage: true });
  });
}

test('editar: guardar envia rol y especialidad y vuelve a usuarios', async ({ page }) => {
  await preparar(page);
  const patch = await simular(page, 'PATCH', `/usuarios/${U2}`, json(200, USUARIOS[1]));
  await page.goto(EDITAR);
  await page.getByRole('radio', { name: /Cliente/ }).check();
  await page.getByRole('textbox', { name: 'Especialidad' }).fill('');
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await page.waitForURL('**/app/usuarios?aviso=usuario-actualizado');
  expect(patch[0].cuerpo).toEqual({ rol: 'cliente', especialidad: null });
});

test('editar: ultimo administrador se explica en el formulario y conserva los datos', async ({ page }) => {
  await preparar(page, U2);
  await simular(page, 'PATCH', `/usuarios/${U1}`, errorApi(409, 'ultimo_administrador', 'x'));
  await page.goto(`/app/usuarios/editar?id=${U1}`);
  await page.getByRole('radio', { name: /Personal del estudio/ }).check();
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  const aviso = page.locator('[data-avisos] .aviso-error');
  await expect(aviso).toContainText('No puedes quitar el último administrador. Da el rol de Administrador a otra persona antes de cambiar este.');
  await expect(aviso).toBeFocused();
  await expect(page.getByRole('radio', { name: /Personal del estudio/ })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Guardar rol y especialidad' })).toBeEnabled();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-editar-ultimo-administrador-1440.png', fullPage: true });
});

test('editar: a si mismo avisa y, al dejar de ser administrador, va a /app/', async ({ page }) => {
  await preparar(page, U1);
  await simular(page, 'PATCH', `/usuarios/${U1}`, json(200, usr(U1, 'Ana Pérez', 'personal')));
  await page.goto(`/app/usuarios/editar?id=${U1}`);
  await expect(page.getByText('Estás cambiando tu propio rol.')).toBeVisible();
  await expect(page.getByText('Si dejas de ser Administrador, perderás el acceso a esta sección.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/solicitudes-editar-propio-1440.png', fullPage: true });
  await page.getByRole('radio', { name: /Personal del estudio/ }).check();
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await page.waitForURL('**/app/');
});

test('editar: 503 al guardar deja el formulario y avisa', async ({ page }) => {
  await preparar(page);
  await simular(page, 'PATCH', `/usuarios/${U2}`, errorApi(503, 'x'));
  await page.goto(EDITAR);
  await page.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await expect(page.locator('[data-avisos] .aviso-error')).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('textbox', { name: 'Especialidad' })).toHaveValue('asesoria');
});
