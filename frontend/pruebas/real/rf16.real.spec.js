// RF-16 (Libro de Reclamaciones) de punta a punta contra Supabase, Storage, backend (8010) y Mailpit reales: sin page.route
// (salvo una vez, para abortar la respuesta y simular la perdida de red del reintento). `npm run test:e2e:real`.
// Las hojas son inmutables y no se borran: al borrar las cuentas quedan con `id_cuenta` nulo. Se crean las imprescindibles (4).
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';
import { API, BACKEND, cargarTextos, llamar, prepararCliente, hoyMasDias } from './ayudas.js';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const CAPTURAS = 'pruebas/capturas/real-rf16';
const NUMERO = /\d{9}-\d{4}/;

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `rf16-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Reclamos');
const cliente = persona('cliente', 'Clara Reclamante');
const visitante = { nombre: 'Víctor Visitante', correo: `rf16-${marca}-visita@prueba.bugalu.pe` };
const fisica = { nombre: 'Fabiola Fisica', correo: `rf16-${marca}-fisica@prueba.bugalu.pe` };
const reintento = { nombre: 'Rita Reintento', correo: `rf16-${marca}-reintento@prueba.bugalu.pe` };
const correos = [admin.correo, cliente.correo, visitante.correo, fisica.correo, reintento.correo];
const desde = new Date().toISOString(); // avisos e intentos de limite que se borran desde este instante

const PDF = { name: 'comprobante.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n') };

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ browser }) => {
  cargarTextos();
  try {
    const [auth, mail, api] = await Promise.all([fetch(`${SUPABASE}/auth/v1/health`), fetch(`${MAILPIT}/api/v1/info`), fetch(`${API}/salas`)]);
    if (!auth.ok || !mail.ok || !api.ok) throw new Error(`Auth ${auth.status}, Mailpit ${mail.status}, API ${api.status}`);
  } catch (error) {
    const motivo = `Falta el stack local (Supabase ${SUPABASE}, Mailpit ${MAILPIT}, API ${API}): ${error.message}`;
    if (process.env.EXIGIR_INTEGRACION) throw new Error(motivo);
    test.skip(true, motivo);
  }
  const p = await browser.newPage(); // calienta astro dev (ver rf01.real.spec.js)
  for (const ruta of ['/', '/acceso/registro', '/acceso/interno', '/acceso/textos', '/app/', '/libro-de-reclamaciones/', '/app/reclamos/', '/app/reclamos/detalle', '/app/reclamos/transcribir']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  // Las hojas y sus adjuntos se conservan (inmutables); se van las cuentas, sus avisos y los intentos del limite por IP.
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

// Busca el correo en Mailpit (la bandeja se envia cada 2 s) y devuelve su texto.
async function correoDe(correo, asunto) {
  for (let i = 0; i < 100; i++) {
    const { messages } = await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${correo} subject:"${asunto}"`)}`)).json();
    if (messages.length) return (await (await fetch(`${MAILPIT}/api/v1/message/${messages[0].ID}`)).json()).Text;
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`No llegó el correo "${asunto}" a ${correo}`);
}

const llenar = async (page, c, detalle) => {
  await page.locator('#rc-nombre').fill(c.nombre);
  await page.locator('#rc-tipo-documento').selectOption('dni');
  await page.locator('#rc-documento').fill(c.documento);
  await page.locator('#rc-domicilio').fill('Av. Siempre Viva 123, Lima');
  await page.locator('#rc-correo').fill(c.correo);
  await page.locator('#rc-tipo-reclamo').check();
  await page.locator('#rc-detalle').fill(detalle);
  await page.locator('#rc-pedido').fill('Que me devuelvan la mitad del importe.');
};
const revisar = async (page) => {
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'REVISA TU HOJA' })).toBeFocused();
};
const enviar = async (page) => {
  await page.getByRole('button', { name: 'Enviar reclamación' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  return (await page.locator('article.hoja h2').textContent()).match(NUMERO)[0];
};

let paginaAdmin, paginaCliente, numeroV, numeroC, numeroF, idV, idC;
const dniVisitante = '40111222';
const dniCliente = '40333444';

test('a. el visitante llega con un clic desde la portada, confirma, envía con un PDF y recibe constancia y copia sin "Mis reclamos"', async ({ browser }) => {
  const page = await nuevaPagina(browser);
  await page.goto('/');
  await page.getByRole('contentinfo').getByRole('link', { name: 'Libro de Reclamaciones' }).click();
  await expect(page).toHaveURL('/libro-de-reclamaciones/');
  await expect(page.getByRole('heading', { level: 1, name: 'LIBRO DE RECLAMACIONES' })).toBeVisible();
  await captura(page, 'a-formulario');
  await llenar(page, { ...visitante, documento: dniVisitante }, `Entregaron la mezcla con tres días de retraso (${marca}).`);
  await page.locator('#rc-adjuntos').setInputFiles(PDF);
  await revisar(page);
  await expect(page.locator('article.hoja')).toContainText('comprobante.pdf');
  await captura(page, 'a-confirmacion');
  numeroV = await enviar(page);
  const constancia = page.locator('[data-avisos] .aviso');
  await expect(constancia).toContainText(`Registramos tu hoja N.º ${numeroV}`);
  await expect(constancia).toContainText(`Te enviamos una copia a ${visitante.correo}`);
  await expect(constancia).not.toContainText('Mis reclamos');
  await expect(page.locator('article.hoja time[data-fecha]')).toHaveText(/^\d{1,2} [a-z]{3} \d{4}, \d{2}:\d{2}$/); // fecha y hora
  await expect(page.locator('article.hoja')).toContainText('comprobante.pdf');
  await expect(page.getByRole('link', { name: 'Ver mis reclamos' })).toBeHidden();
  await expect(page.getByRole('button', { name: 'Imprimir o guardar en PDF' })).toBeVisible();
  await captura(page, 'a-constancia');

  const texto = await correoDe(visitante.correo, `Hoja de reclamación N.º ${numeroV}`);
  expect(texto).toContain(`Hoja N.º: ${numeroV}`);
  expect(texto).toContain(visitante.nombre);
  expect(texto).toContain(`DNI ${dniVisitante}`);
  expect(texto).toContain('comprobante.pdf');
  expect(texto).toContain(`tres días de retraso (${marca})`);
  expect(texto).not.toMatch(/Mis reclamos/i);
  await page.context().close();
});

test('b. el cliente con sesión ve sus datos prellenados, envía y la constancia promete Mis reclamos', async ({ browser }) => {
  paginaCliente = await nuevaPagina(browser);
  await registrarCuenta(paginaCliente, cliente);
  await prepararCliente(paginaCliente, dniCliente);
  await paginaCliente.goto('/libro-de-reclamaciones/');
  await expect(paginaCliente.getByText('Usamos los datos de tu cuenta')).toBeVisible();
  await expect(paginaCliente.locator('#rc-nombre')).toHaveValue(cliente.nombre);
  await expect(paginaCliente.locator('#rc-correo')).toHaveValue(cliente.correo);
  await expect(paginaCliente.locator('#rc-tipo-documento')).toHaveValue('dni');
  await expect(paginaCliente.locator('#rc-documento')).toHaveValue(dniCliente);
  await expect(paginaCliente.locator('#rc-telefono')).toHaveValue(cliente.telefono);
  await captura(paginaCliente, 'b-prellenado');
  await paginaCliente.locator('#rc-domicilio').fill('Jr. Los Pinos 456, Lima');
  await paginaCliente.locator('#rc-tipo-queja').check();
  await paginaCliente.locator('#rc-detalle').fill(`Me atendieron con mala cara en recepción (${marca}).`);
  await paginaCliente.locator('#rc-pedido').fill('Que me pidan disculpas por escrito.');
  await revisar(paginaCliente);
  numeroC = await enviar(paginaCliente);
  await expect(paginaCliente.locator('[data-avisos] .aviso')).toContainText('También la encuentras en Mis reclamos.');
  await captura(paginaCliente, 'b-constancia');
  await paginaCliente.getByRole('link', { name: 'Ver mis reclamos' }).click();
  await paginaCliente.waitForURL('**/app/reclamos/');
  const fila = paginaCliente.getByRole('table').getByRole('row').filter({ hasText: numeroC });
  await expect(fila).toContainText('Queja');
  await expect(fila).toContainText('EN TRÁMITE');
  await expect(paginaCliente.getByRole('table').getByRole('row').filter({ hasText: numeroV })).toHaveCount(0); // la del visitante no es suya
  await captura(paginaCliente, 'b-mis-reclamos');
  const mias = (await llamar(paginaCliente, 'GET', '/reclamaciones/mias')).cuerpo;
  idC = mias.find((h) => h.numero === numeroC).id;
  expect(mias.map((h) => h.numero)).toEqual([numeroC]);
  expect((await llamar(paginaCliente, 'GET', '/reclamaciones')).estado).toBe(403); // la bandeja es del Administrador
});

test('c1. el Administrador ve la bandeja con "Vence en N días hábiles", el detalle y el adjunto por URL firmada', async ({ browser }) => {
  paginaAdmin = await nuevaPagina(browser);
  await registrarCuenta(paginaAdmin, admin);
  execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.crear_administrador', admin.correo], { cwd: BACKEND });
  await paginaAdmin.evaluate(() => localStorage.clear());
  await paginaAdmin.goto('/acceso/interno');
  await paginaAdmin.getByLabel('Correo', { exact: true }).fill(admin.correo);
  await paginaAdmin.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await paginaAdmin.getByRole('button', { name: 'Entrar a la sala' }).click();
  await paginaAdmin.waitForURL('**/app/');

  await paginaAdmin.goto('/app/reclamos/');
  const filaV = paginaAdmin.getByRole('table').getByRole('row').filter({ hasText: numeroV });
  await expect(filaV).toContainText(/VENCE EN \d+ DÍAS? HÁBILES?/i);
  await expect(filaV).toContainText(visitante.nombre);
  await expect(paginaAdmin.getByRole('table').getByRole('row').filter({ hasText: numeroC })).toContainText(/VENCE EN \d+ DÍAS? HÁBILES?/i);
  await captura(paginaAdmin, 'c-bandeja');
  idV = (await llamar(paginaAdmin, 'GET', '/reclamaciones')).cuerpo.find((h) => h.numero === numeroV).id;

  await paginaAdmin.getByRole('link', { name: `Revisar hoja ${numeroV}` }).click();
  await expect(paginaAdmin.getByRole('heading', { level: 1 })).toHaveText(`HOJA N.º ${numeroV}`);
  await expect(paginaAdmin.locator('article.hoja')).toContainText(`DNI ${dniVisitante}`);
  await expect(paginaAdmin.locator('article.hoja')).toContainText(`tres días de retraso (${marca})`);
  await captura(paginaAdmin, 'c-detalle');

  // El adjunto: la API entrega una URL firmada que se abre y se descarga sin token.
  // El PDF se abre en una pestana nueva y el navegador de pruebas lo baja (descarga) en vez de mostrarlo.
  const descargaPestana = new Promise((res) => paginaAdmin.context().once('page', (p) => p.once('download', res)));
  await paginaAdmin.getByRole('link', { name: 'Abrir comprobante.pdf (pestaña nueva)' }).click();
  const bajada = await descargaPestana;
  expect(bajada.url()).toMatch(/\/storage\/v1\/object\/sign\/.+token=/);
  expect((await readFile(await bajada.path(), 'utf8')).startsWith('%PDF-1.4')).toBe(true);
  const { estado, cuerpo } = await llamar(paginaAdmin, 'GET', `/reclamaciones/${idV}/adjuntos/1`);
  expect(estado).toBe(200);
  expect(cuerpo.url).toMatch(/\/storage\/v1\/object\/sign\/.+token=/);
  const descarga = await fetch(cuerpo.url);
  expect(descarga.status).toBe(200);
  expect((await descarga.text()).startsWith('%PDF-1.4')).toBe(true);
  expect((await llamar(paginaAdmin, 'GET', `/reclamaciones/${idV}/adjuntos/2`)).estado).toBe(404);
});

test('c2. el Administrador responde por correo una sola vez; el correo llega y el cliente ve la respuesta en Mis reclamos', async () => {
  const respuesta = `Lamentamos lo ocurrido. Te pedimos disculpas por escrito (${marca}).`;
  await paginaAdmin.goto(`/app/reclamos/detalle?id=${idC}`);
  const panel = paginaAdmin.getByRole('region', { name: /R1/ });
  await paginaAdmin.locator('#rec-texto').fill(respuesta);
  await panel.getByRole('button', { name: 'Revisar respuesta' }).click();
  await expect(paginaAdmin.getByText(`Enviamos esta respuesta a ${cliente.correo}`)).toBeVisible();
  await captura(paginaAdmin, 'c-revisar-respuesta');
  await paginaAdmin.getByRole('button', { name: 'Enviar respuesta' }).click();
  await expect(paginaAdmin.getByText('RESPONDIDA').first()).toBeVisible();
  await expect(panel.getByRole('button')).toHaveCount(0); // sin segundo intento en la pantalla
  await expect(paginaAdmin.locator('article.hoja')).toContainText(admin.nombre);
  await expect(paginaAdmin.locator('article.hoja')).toContainText(respuesta);
  await captura(paginaAdmin, 'c-respondida');
  // Segundo intento por la API: bloqueado y sin cambiar la respuesta.
  const otra = await llamar(paginaAdmin, 'POST', `/reclamaciones/${idC}/respuesta`, { texto: 'Una segunda respuesta distinta.' });
  expect(otra.estado).toBe(409);
  expect(otra.cuerpo.error.codigo).toBe('ya_respondida');
  expect((await llamar(paginaAdmin, 'GET', `/reclamaciones/${idC}`)).cuerpo.respuesta.texto).toBe(respuesta);

  const texto = await correoDe(cliente.correo, `Respuesta a tu hoja de reclamación N.º ${numeroC}`);
  expect(texto).toContain(respuesta);
  expect(texto).toContain(`Hoja N.º: ${numeroC}`);
  expect(await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${cliente.correo} subject:"Respuesta a tu hoja"`)}`)).json().then((r) => r.messages.length)).toBe(1); // un solo correo

  await paginaCliente.goto(`/app/reclamos/detalle?id=${idC}`);
  await expect(paginaCliente.locator('article.hoja')).toContainText(respuesta, { timeout: 20_000 });
  await expect(paginaCliente.locator('article.hoja')).not.toContainText('SIN RESPUESTA');
  await captura(paginaCliente, 'c-cliente-ve-respuesta');
  await paginaCliente.goto('/app/reclamos/');
  await expect(paginaCliente.getByRole('table').getByRole('row').filter({ hasText: numeroC })).toContainText(/respondida/i);
});

test('c3. el Administrador exporta el CSV del día y descarga las hojas', async () => {
  await paginaAdmin.goto('/app/reclamos/');
  await paginaAdmin.getByLabel('Desde').fill(hoyMasDias(-1));
  await paginaAdmin.getByLabel('Hasta').fill(hoyMasDias(1));
  const [descarga] = await Promise.all([paginaAdmin.waitForEvent('download'), paginaAdmin.getByRole('button', { name: 'Exportar CSV' }).click()]);
  expect(descarga.suggestedFilename()).toBe(`reclamaciones-${hoyMasDias(-1)}-${hoyMasDias(1)}.csv`);
  const csv = await readFile(await descarga.path(), 'utf8');
  expect(csv).toContain(numeroV);
  expect(csv).toContain(numeroC);
  expect(csv).toContain(visitante.nombre);
  expect(csv).toContain(`Te pedimos disculpas por escrito (${marca})`); // incluye la respuesta
  expect((await llamar(paginaAdmin, 'GET', `/reclamaciones/exportar?desde=${hoyMasDias(1)}&hasta=${hoyMasDias(-1)}`)).estado).toBe(422);
});

test('d. la transcripción del libro físico acepta la fecha de ayer con su número de hoja y rechaza la de hace 100 días', async () => {
  await paginaAdmin.goto('/app/reclamos/transcribir');
  const rellenar = async (fecha) => {
    await paginaAdmin.locator('#rc-numero-fisica').fill(`F-${marca}`);
    await paginaAdmin.locator('#rc-fecha-original').fill(fecha);
    await paginaAdmin.locator('#rc-hora-original').fill('10:00');
    await llenar(paginaAdmin, { ...fisica, documento: '40555666' }, `Anotado a mano en el libro de respaldo (${marca}).`);
    await paginaAdmin.locator('#rc-medio-correo').check();
  };
  await rellenar(hoyMasDias(-100));
  await paginaAdmin.getByRole('button', { name: 'Revisar la hoja' }).click();
  await paginaAdmin.getByRole('button', { name: 'Registrar hoja' }).click();
  const campo = paginaAdmin.locator('#rc-fecha-original');
  await expect(campo).toHaveAttribute('aria-invalid', 'true');
  await expect(paginaAdmin.locator('#rc-fecha-original-error')).toBeVisible();
  await captura(paginaAdmin, 'd-fecha-100-dias');

  await paginaAdmin.goto('/app/reclamos/transcribir');
  await rellenar(hoyMasDias(-1));
  await paginaAdmin.getByRole('button', { name: 'Revisar la hoja' }).click();
  await expect(paginaAdmin.locator('article.hoja')).toContainText(`F-${marca}`.toUpperCase());
  await paginaAdmin.getByRole('button', { name: 'Registrar hoja' }).click();
  await paginaAdmin.waitForURL(/\/app\/reclamos\/detalle\?id=/);
  await expect(paginaAdmin.getByRole('heading', { level: 1 })).toHaveText(/^HOJA N\.º \d{9}-\d{4}$/);
  numeroF = (await paginaAdmin.getByRole('heading', { level: 1 }).textContent()).match(NUMERO)[0];
  await expect(paginaAdmin.locator('[data-avisos] .aviso')).toContainText(`Hoja transcrita con el N.º ${numeroF}.`);
  await expect(paginaAdmin.locator('article.hoja')).toContainText(/TRANSCRITA DEL LIBRO FÍSICO · HOJA/);
  await expect(paginaAdmin.locator('article.hoja')).toContainText(`F-${marca}`.toUpperCase());
  await captura(paginaAdmin, 'd-transcrita');
  const hoja = (await llamar(paginaAdmin, 'GET', `/reclamaciones/${new URL(paginaAdmin.url()).searchParams.get('id')}`)).cuerpo;
  expect(hoja).toMatchObject({ origen: 'libro_fisico', numero_hoja_fisica: `F-${marca}` });
  expect(hoja.fecha_original.slice(0, 10)).toBe(hoyMasDias(-1));
  // Con correo, la copia llega al consumidor.
  expect(await correoDe(fisica.correo, `Hoja de reclamación N.º ${numeroF}`)).toContain(`Hoja N.º: ${numeroF}`);
});

test('e. un reintento con la misma clave_envio y los mismos datos tras perder la respuesta deja una sola hoja', async ({ browser }) => {
  const page = await nuevaPagina(browser);
  const detalle = `Cobro duplicado de la reserva (${marca}).`;
  let peticiones = 0;
  await page.route(`${API}/reclamaciones`, async (ruta) => {
    if (ruta.request().method() !== 'POST') return ruta.fallback();
    peticiones++;
    if (peticiones === 1) {
      await ruta.fetch(); // la hoja llega al backend y se registra...
      return ruta.abort('connectionreset'); // ...pero la respuesta se pierde
    }
    return ruta.continue();
  });
  await page.goto('/libro-de-reclamaciones/');
  await llenar(page, { ...reintento, documento: '40777888' }, detalle);
  await revisar(page);
  await page.getByRole('button', { name: 'Enviar reclamación' }).click();
  await expect(page.getByText('Sin conexión')).toBeVisible();
  await captura(page, 'e-sin-conexion');
  const numero = await enviar(page); // mismo boton, misma clave
  expect(peticiones).toBe(2);
  await expect(page.locator('[data-avisos] .aviso')).toContainText(`Registramos tu hoja N.º ${numero}`);
  await captura(page, 'e-reintento');
  const hojas = (await llamar(paginaAdmin, 'GET', '/reclamaciones')).cuerpo.filter((h) => h.consumidor.nombre === reintento.nombre);
  expect(hojas.map((h) => h.numero)).toEqual([numero]);
  // El reintento no reenvia la copia: un solo correo.
  await correoDe(reintento.correo, `Hoja de reclamación N.º ${numero}`);
  await new Promise((r) => setTimeout(r, 4000));
  const { messages } = await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${reintento.correo}`)}`)).json();
  expect(messages).toHaveLength(1);
  await page.context().close();
});
