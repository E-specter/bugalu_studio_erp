// RF-17 de punta a punta contra Supabase y el backend (8010) reales: sin page.route. `npm run test:e2e:real`.
// Registro con aceptacion de textos, "Completa tus datos" al reservar, publicacion de versiones, consentimientos y documentos repetidos.
// Los textos y las aceptaciones son inmutables: no se borran; se cuentan de forma relativa (la cuenta, al borrarse, se lleva sus aceptaciones).
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';
import { API, BACKEND, cargarTextos, llamar, dniNuevo, prepararCliente, confirmarReserva, dia, ymd, inicio, hoyMasDias } from './ayudas.js';

const SUPABASE = 'http://127.0.0.1:45621';
const CAPTURAS = 'pruebas/capturas/real-rf17';
const FOLIO = /R-\d{4}-\d+/;

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `ace-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Textos');
const nueva = persona('nueva', 'Nora Aceptaciones');
const gemelaB = persona('b', 'Bruno Documento');
const gemelaC = persona('c', 'Carla Documento');
const correos = [admin.correo, nueva.correo, gemelaB.correo, gemelaC.correo];
const desde = new Date().toISOString(); // los avisos de versiones nuevas se borran desde este instante
const TIPO = 'terminos_uso';
const RUTA_LEGAL = '/legal/terminos-de-uso/';

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ browser }) => {
  cargarTextos();
  try {
    const [auth, api] = await Promise.all([fetch(`${SUPABASE}/auth/v1/health`), fetch(`${API}/textos-legales`)]);
    if (!auth.ok || !api.ok) throw new Error(`Auth ${auth.status}, API ${api.status}`);
  } catch (error) {
    const motivo = `Falta el stack local (Supabase ${SUPABASE}, API ${API}): ${error.message}`;
    if (process.env.EXIGIR_INTEGRACION) throw new Error(motivo);
    test.skip(true, motivo);
  }
  const p = await browser.newPage(); // calienta astro dev (ver rf01.real.spec.js)
  for (const ruta of ['/acceso', '/acceso/registro', '/acceso/interno', '/acceso/textos', '/app/', '/app/franjas/', '/app/perfil/privacidad/', '/app/textos', '/app/textos/publicar', '/app/usuarios', '/legal/terminos-de-uso/', '/reservar/confirmar/', '/reservar/cuenta/', '/reservar/listo/']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  // Siempre: si un paso falla con una version programada sin retirar, se retira; luego no quedan usuarios, reservas, franjas ni avisos.
  if (paginaAdmin) {
    const lista = await (await fetch(`${API}/textos-legales`)).json();
    for (const t of lista.filter((t) => t.programada && t.tipo === TIPO)) await llamar(paginaAdmin, 'DELETE', `/textos-legales/${t.tipo}/versiones/${t.version}`).catch(() => {});
  }
  console.log(execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, 'limpiar.py'), `--avisos-desde=${desde}`, ...correos], { cwd: BACKEND, encoding: 'utf8' }).trim());
});

const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png`, fullPage: true });
const registrarCuenta = async (page, p) => {
  await page.goto('/acceso/registro');
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await page.waitForURL('**/acceso/textos*');
};
const vigente = async (tipo) => (await (await fetch(`${API}/textos-legales`)).json()).find((t) => t.tipo === tipo && !t.programada);
const mias = async (page) => (await llamar(page, 'GET', '/aceptaciones/mias')).cuerpo;

let paginaAdmin, paginaA, paginaB, paginaC, idSala, idServicio, idReserva, folio, aceptacionesIniciales, vigenteInicial, versionParche;

test('1. el cliente nuevo se registra, acepta los textos en /acceso/textos y ve el historial con la versión', async ({ browser }) => {
  paginaA = await nuevaPagina(browser);
  await registrarCuenta(paginaA, nueva);
  await expect(paginaA.getByRole('heading', { level: 1 })).toHaveText('Antes de empezar');
  const terminos = await vigente('terminos_uso');
  const politica = await vigente('politica_privacidad');
  const casilla = paginaA.getByRole('checkbox', { name: /Acepto los Términos de uso/ });
  await expect(casilla).not.toBeChecked(); // CA-13: ninguna casilla viene marcada
  await expect(casilla).toHaveAccessibleName(new RegExp(`versión ${terminos.version}`));
  await captura(paginaA, '1-aceptar-textos');
  await paginaA.getByRole('button', { name: 'Aceptar y continuar' }).click();
  await expect(paginaA.getByText('Marca la casilla para aceptar los términos')).toBeVisible();
  await casilla.check();
  await paginaA.getByRole('button', { name: 'Aceptar y continuar' }).click();
  await paginaA.waitForURL('**/app/perfil?aviso=textos-aceptados');

  await paginaA.goto('/app/perfil/privacidad/');
  const historial = paginaA.getByRole('table', { name: 'Textos que aceptaste' });
  await expect(historial.getByRole('row').filter({ hasText: `Términos de uso` })).toContainText(terminos.version);
  await expect(historial.getByRole('row').filter({ hasText: 'Política de privacidad' })).toContainText(politica.version);
  await expect(historial.getByRole('row').filter({ hasText: 'Registro' })).toHaveCount(2);
  await captura(paginaA, '1-historial-registro');
  aceptacionesIniciales = (await mias(paginaA)).length;
  expect(aceptacionesIniciales).toBe(2);
});

test('2. el Administrador publica las franjas de la semana siguiente', async ({ browser }) => {
  paginaAdmin = await nuevaPagina(browser);
  await registrarCuenta(paginaAdmin, admin);
  execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.crear_administrador', admin.correo], { cwd: BACKEND });
  await paginaAdmin.evaluate(() => localStorage.clear());
  await paginaAdmin.goto('/acceso/interno');
  await paginaAdmin.getByLabel('Correo', { exact: true }).fill(admin.correo);
  await paginaAdmin.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await paginaAdmin.getByRole('button', { name: 'Entrar a la sala' }).click();
  await paginaAdmin.waitForURL('**/app/');
  await paginaAdmin.goto('/app/franjas/');
  await paginaAdmin.getByRole('link', { name: 'Semana siguiente' }).click();
  await expect(paginaAdmin.getByText('No hay franjas publicadas esta semana')).toBeVisible();
  const grupo = paginaAdmin.getByRole('group', { name: /^MARTES / });
  if (!(await grupo.getByLabel('Desde').count())) await grupo.getByRole('button', { name: 'Añadir franja al martes' }).click();
  await grupo.getByLabel('Desde').fill('09:00');
  await grupo.getByLabel('Hasta').fill('14:00');
  await paginaAdmin.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(paginaAdmin.getByText('Franjas publicadas. Ya se ven en el calendario.')).toBeVisible();
  idSala = (await (await fetch(`${API}/salas`)).json())[0].id;
  idServicio = (await (await fetch(`${API}/servicios`)).json()).find((s) => s.nombre === 'Grabación de voces').id;
});

test('3. reservar sin documento lleva a "Completa tus datos", vuelve al tramo y reserva con la casilla de condiciones', async () => {
  const martes = dia(1);
  expect((await llamar(paginaA, 'GET', '/perfil')).cuerpo.datos_para_reservar).toBe(false);
  await paginaA.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(martes, '10:00'))}&duracion=60&sala=${idSala}&servicio=${idServicio}`);
  await paginaA.waitForURL(/\/reservar\/cuenta\//);
  await expect(paginaA.getByRole('heading', { level: 1 })).toHaveText('Completa tus datos');
  await captura(paginaA, '3-completa-tus-datos');
  await paginaA.getByRole('button', { name: 'Guardar y continuar' }).click();
  await expect(paginaA.locator('main')).toContainText(/documento|Elige/i); // sin documento no avanza
  await paginaA.locator('[name="tipo_documento"]').selectOption('dni');
  await paginaA.locator('[name="numero_documento"]').fill(dniNuevo());
  await paginaA.getByRole('button', { name: 'Guardar y continuar' }).click();
  await paginaA.waitForURL(/\/reservar\/confirmar\//);
  expect(new URL(paginaA.url()).searchParams.get('inicio')).toBe(inicio(martes, '10:00')); // vuelve al mismo tramo
  const condiciones = paginaA.getByRole('checkbox', { name: /Acepto las Condiciones de contratación/ });
  await expect(condiciones).not.toBeChecked();
  const version = (await vigente('condiciones_contratacion')).version;
  await expect(condiciones).toHaveAccessibleName(new RegExp(`versión ${version}`));
  await paginaA.getByRole('button', { name: 'Confirmar reserva' }).click();
  await expect(paginaA.getByText('Marca la casilla para aceptar las condiciones')).toBeVisible(); // sin casilla no reserva
  await captura(paginaA, '3-confirmar-sin-casilla');
  await confirmarReserva(paginaA);
  await paginaA.waitForURL(/\/reservar\/listo\/\?id=/);
  idReserva = new URL(paginaA.url()).searchParams.get('id');
  folio = (await paginaA.getByText(FOLIO).first().textContent()).match(FOLIO)[0];
  await captura(paginaA, '3-reserva-registrada');

  const reserva = (await llamar(paginaA, 'GET', `/reservas/${idReserva}`)).cuerpo;
  expect(reserva.version_condiciones).toBe(version);
  const lista = await mias(paginaA);
  expect(lista.length).toBe(aceptacionesIniciales + 1);
  const deReserva = lista.filter((a) => a.contexto === 'reserva');
  expect(deReserva).toHaveLength(1);
  expect(deReserva[0]).toMatchObject({ tipo: 'condiciones_contratacion', version, id_operacion: idReserva });
  await paginaA.goto('/app/perfil/privacidad/');
  await expect(paginaA.getByRole('table', { name: 'Textos que aceptaste' }).getByRole('row').filter({ hasText: 'Reserva' })).toContainText(version);
  await captura(paginaA, '3-historial-reserva');
});

test('4. el Administrador publica un parche que rige ya y una versión mayor programada, y cada versión se lee por su número', async () => {
  vigenteInicial = (await vigente(TIPO)).version;
  for (const t of (await (await fetch(`${API}/textos-legales`)).json()).filter((t) => t.programada && t.tipo === TIPO)) {
    await llamar(paginaAdmin, 'DELETE', `/textos-legales/${t.tipo}/versiones/${t.version}`); // resto de una corrida que falló
  }
  const publicar = async (cambio, contenido, fecha) => {
    await paginaAdmin.goto(`/app/textos/publicar?tipo=${TIPO}`);
    await paginaAdmin.getByRole('radio', { name: new RegExp(`^${cambio}`) }).check();
    if (fecha) await paginaAdmin.locator('[name="vigente_desde"]').fill(fecha);
    await paginaAdmin.locator('[name="resumen_registro"]').fill(`Resumen de la prueba ${marca}.`);
    await paginaAdmin.locator('[name="contenido"]').fill(contenido);
    const version = await paginaAdmin.locator('[name="version"]').inputValue();
    await paginaAdmin.getByRole('button', { name: 'Revisar y publicar' }).click();
    await captura(paginaAdmin, `4-revisar-${cambio.toLowerCase()}`);
    await paginaAdmin.getByRole('button', { name: 'Publicar versión' }).click();
    await paginaAdmin.waitForURL('**/app/textos?aviso=version-publicada');
    return version;
  };

  // Parche: rige al publicarse, sin fecha ni aviso.
  versionParche = await publicar('Parche', `# Términos de la prueba ${marca}\n\nParche de la prueba.`);
  expect(versionParche).not.toBe(vigenteInicial);
  expect((await vigente(TIPO)).version).toBe(versionParche);
  await paginaAdmin.goto(`${RUTA_LEGAL}?version=${versionParche}`);
  await expect(paginaAdmin.locator('[data-linea]')).toContainText(`VERSIÓN ${versionParche}`);
  await expect(paginaAdmin.locator('main')).toContainText(`Términos de la prueba ${marca}`);
  await captura(paginaAdmin, '4-legal-parche');
  await paginaAdmin.goto(`${RUTA_LEGAL}?version=${vigenteInicial}`);
  await expect(paginaAdmin.getByText(`Estás leyendo la versión ${vigenteInicial}, que ya no está vigente.`)).toBeVisible();
  await captura(paginaAdmin, '4-legal-version-anterior');

  // Mayor programada: exige 15 dias de aviso.
  const mayor = await publicar('Mayor', `# Términos mayores ${marca}\n\nVersión mayor programada.`, hoyMasDias(16));
  const lista = await (await fetch(`${API}/textos-legales`)).json();
  expect(lista.find((t) => t.tipo === TIPO && t.programada)).toMatchObject({ version: mayor });
  expect((await vigente(TIPO)).version).toBe(versionParche); // la mayor aun no rige
  await expect(paginaAdmin.getByText(new RegExp(`^${mayor} · desde`))).toBeVisible();
  await captura(paginaAdmin, '4-lista-programada');
  await paginaAdmin.goto(`${RUTA_LEGAL}?version=${mayor}`);
  await expect(paginaAdmin.getByText(`Estás leyendo la versión ${mayor}, que aún no está vigente.`)).toBeVisible();
  await expect(paginaAdmin.locator('main')).toContainText(`Términos mayores ${marca}`);
  await captura(paginaAdmin, '4-legal-mayor-programada');

  // Con una programada, otra publicacion se rechaza; se retira desde la lista y vuelve a quedar libre.
  await paginaAdmin.goto('/app/textos');
  await paginaAdmin.getByRole('button', { name: `Retirar versión ${mayor} de Términos de uso` }).click();
  await captura(paginaAdmin, '4-retirar-programada');
  await paginaAdmin.getByRole('button', { name: 'Retirar versión', exact: true }).click();
  await paginaAdmin.waitForURL('**/app/textos?aviso=version-retirada');
  expect((await (await fetch(`${API}/textos-legales`)).json()).filter((t) => t.programada && t.tipo === TIPO)).toHaveLength(0);
  expect((await fetch(`${API}/textos-legales/${TIPO}/versiones/${mayor}`)).status).toBe(404);
  // El parche no pidio nada: la cuenta nueva sigue sin pendientes.
  expect((await llamar(paginaA, 'GET', '/perfil')).cuerpo.pendientes).toEqual([]);
});

test('5. consentimientos: promociones por correo se dan y se retiran; WhatsApp sin teléfono está deshabilitado', async ({ browser }) => {
  await paginaA.goto('/app/perfil/privacidad/');
  const correo = paginaA.getByRole('checkbox', { name: 'Quiero recibir promociones por correo.' });
  await expect(correo).not.toBeChecked();
  await correo.check();
  await paginaA.getByRole('button', { name: 'Guardar preferencias' }).click();
  await expect(paginaA.locator('.aviso').first()).toBeVisible();
  await paginaA.reload();
  await expect(correo).toBeChecked();
  const historial = paginaA.getByRole('table', { name: 'Textos que aceptaste' });
  await expect(historial.getByRole('row').filter({ hasText: 'Promociones' })).toHaveCount(1);
  await captura(paginaA, '5-promociones-dadas');
  await correo.uncheck();
  await paginaA.getByRole('button', { name: 'Guardar preferencias' }).click();
  await expect(paginaA.locator('.aviso').first()).toBeVisible();
  await paginaA.reload();
  await expect(correo).not.toBeChecked();
  expect((await mias(paginaA)).find((a) => a.contexto === 'promociones').retirada_en).not.toBeNull();
  await captura(paginaA, '5-promociones-retiradas');

  // Sin telefono: la cuenta C lo borra y WhatsApp queda deshabilitado (CA-12).
  paginaC = await nuevaPagina(browser);
  await registrarCuenta(paginaC, gemelaC);
  await prepararCliente(paginaC, '11223344');
  const sinTelefono = await llamar(paginaC, 'PATCH', '/perfil', { telefono: null });
  expect(sinTelefono.estado, JSON.stringify(sinTelefono.cuerpo)).toBe(200);
  await paginaC.goto('/app/perfil/privacidad/');
  const whatsapp = paginaC.getByRole('checkbox', { name: 'Quiero recibir promociones por WhatsApp.' });
  await expect(whatsapp).toHaveAttribute('aria-disabled', 'true');
  await expect(paginaC.getByText('Añade tu teléfono en Tus datos para elegir WhatsApp.')).toBeVisible();
  await captura(paginaC, '5-whatsapp-sin-telefono');
  expect((await llamar(paginaC, 'PUT', '/perfil/consentimientos', { promociones_whatsapp: true })).estado).toBe(422);
});

test('6. dos cuentas con el mismo documento quedan marcadas y el Administrador las lista', async ({ browser }) => {
  paginaB = await nuevaPagina(browser);
  await registrarCuenta(paginaB, gemelaB);
  await prepararCliente(paginaB, '11223344'); // el documento de C: no se bloquea
  await paginaAdmin.goto('/app/usuarios?documento=repetido');
  const tabla = paginaAdmin.getByRole('table');
  await expect(tabla.getByRole('row').filter({ hasText: gemelaB.nombre })).toBeVisible();
  await expect(tabla.getByRole('row').filter({ hasText: gemelaC.nombre })).toBeVisible();
  await expect(tabla.getByRole('row').filter({ hasText: nueva.nombre })).toHaveCount(0); // su documento no se repite
  await captura(paginaAdmin, '6-documento-repetido');
  const repetidos = (await llamar(paginaAdmin, 'GET', '/usuarios?documento_repetido=true')).cuerpo.map((u) => u.nombre);
  expect(repetidos).toEqual(expect.arrayContaining([gemelaB.nombre, gemelaC.nombre]));
});

test('7. al terminar no quedan versiones programadas y las versiones publicadas se conservan', async () => {
  const lista = await (await fetch(`${API}/textos-legales`)).json();
  expect(lista.filter((t) => t.programada)).toHaveLength(0);
  expect((await vigente(TIPO)).version).toBe(versionParche); // el parche queda publicado: es inmutable y no se limpia
  expect((await fetch(`${API}/textos-legales/${TIPO}/versiones/${vigenteInicial}`)).status).toBe(200);
});
