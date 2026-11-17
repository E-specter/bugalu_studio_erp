// Reserva de punta a punta (RF-02 CA-05, RF-03 CA-02/05/06, RF-04 CA-01/02/05..09) contra Supabase, backend (8010) y Mailpit reales: sin page.route.
// Fechas calculadas desde ahora (hora de Lima): la semana siguiente cae dentro de la ventana de 2 h a 8 semanas. `npm run test:e2e:real`.
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';
import { cargarTextos, prepararCliente, confirmarReserva, dniNuevo } from './ayudas.js';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const API = 'http://127.0.0.1:8010/api/v1';
const BACKEND = resolve(import.meta.dirname, '../../../backend');
const PY = (script, ...args) => execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, script), ...args], { cwd: BACKEND, encoding: 'utf8' }).trim();
const FOLIO = /R-\d{4}-\d+/; // folio real de la base (los simulados usan otro formato)
const CAPTURAS ='pruebas/capturas/real-reservas';

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `res-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Admin');
const clienteA = persona('a', 'Cora Reservas');
const clienteB = persona('b', 'Beto Otro');
const correos = [admin.correo, clienteA.correo, clienteB.correo];

// Fechas desde ahora en Lima (UTC-5, sin horario de verano): el martes y el miércoles de la semana que viene.
const lima = new Date(Date.now() - 5 * 3600_000);
const lunesSiguiente = new Date(Date.UTC(lima.getUTCFullYear(), lima.getUTCMonth(), lima.getUTCDate() + (8 - (lima.getUTCDay() || 7))));
const dia = (n) => new Date(lunesSiguiente.getTime() + n * 86400_000);
const ymd = (d) => d.toISOString().slice(0, 10);
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const etiqueta = (d, hora) => `${DIAS[d.getUTCDay()]} ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}, ${hora}`;
const MARTES = dia(1);
const MIERCOLES = dia(2);
const DUR_MIN = 120; // martes 10:00 a 12:00; el miércoles, 1 h para la caducidad
const inicio = (d, hora) => `${ymd(d)}T${hora}:00-05:00`;

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
  for (const ruta of ['/acceso', '/acceso/registro', '/acceso/interno', '/app/franjas/', '/reservar/', '/reservar/servicio/', '/reservar/confirmar/', '/reservar/listo/', '/app/reservas/', '/app/reservas/detalle', '/app/agenda/']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(() => {
  // Siempre: aunque falle un paso, no quedan usuarios, reservas, franjas ni avisos.
  console.log(PY('limpiar.py', ...correos));
});

const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png`, fullPage: true });
const rellenarRegistro = async (page, p) => {
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
};
const entrar = async (page, ruta, p, boton) => {
  await page.goto(ruta);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: boton }).click();
};
const registrar = async (browser, p) => {
  const page = await nuevaPagina(browser);
  await page.goto('/acceso/registro');
  await rellenarRegistro(page, p);
  await page.waitForURL('**/acceso/textos*'); // desde RF-17 el alta pasa por la aceptacion de textos; aqui se resuelve por la API (rf01 y aceptaciones lo hacen por la UI)
  await prepararCliente(page);
  await page.goto('/app/perfil');
  return page;
};

async function correoDe(correo, asunto) {
  for (let i = 0; i < 100; i++) {
    const { messages } = await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${correo} subject:"${asunto}"`)}`)).json();
    if (messages.length) {
      const m = await (await fetch(`${MAILPIT}/api/v1/message/${messages[0].ID}`)).json();
      return m.Text;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`No llegó el correo "${asunto}" a ${correo}`);
}

const catalogo = async (ruta, nombre) => {
  const lista = await (await fetch(`${API}/${ruta}`)).json();
  return nombre ? lista.find((x) => x.nombre === nombre) : lista[0];
};

let paginaAdmin, paginaA, paginaB, folio, total, idSala, idServicio, idProductor;

test('1. el Administrador publica las franjas de la semana siguiente desde la plantilla editable', async ({ browser }) => {
  paginaAdmin = await registrar(browser, admin);
  execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.crear_administrador', admin.correo], { cwd: BACKEND });
  await paginaAdmin.evaluate(() => localStorage.clear());
  await entrar(paginaAdmin, '/acceso/interno', admin, 'Entrar a la sala');
  await paginaAdmin.waitForURL('**/app/');
  await paginaAdmin.goto('/app/franjas/');
  await paginaAdmin.getByRole('link', { name: 'Semana siguiente' }).click();
  await expect(paginaAdmin.getByText('No hay franjas publicadas esta semana')).toBeVisible();
  for (const nombre of ['martes', 'miércoles']) {
    const grupo = paginaAdmin.getByRole('group', { name: new RegExp(`^${nombre.toUpperCase()} `) });
    if (!(await grupo.getByLabel('Desde').count())) await grupo.getByRole('button', { name: `Añadir franja al ${nombre}` }).click();
    await grupo.getByLabel('Desde').fill('09:00');
    await grupo.getByLabel('Hasta').fill('14:00');
  }
  await captura(paginaAdmin, '1-franjas-plantilla');
  await paginaAdmin.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(paginaAdmin.getByText('Franjas publicadas. Ya se ven en el calendario.')).toBeVisible();
  await expect(paginaAdmin.getByRole('table', { name: 'Franjas publicadas' }).getByRole('row')).toHaveCount(3); // cabecera + 2
  await captura(paginaAdmin, '1-franjas-publicadas');
  idSala = (await catalogo('salas')).id;
  idServicio = (await catalogo('servicios', 'Grabación de voces')).id;
  idProductor = (await catalogo('especialistas', 'Productor o arreglista')).id;
});

test('2. el visitante elige horario, servicio y especialista, ve la simulación y reserva tras registrarse', async ({ browser }) => {
  paginaA = await nuevaPagina(browser);
  const p = paginaA;
  const libre = p.getByRole('button', { name: etiqueta(MARTES, '10:00') + ', libre' });
  await p.goto(`/reservar/?fecha=${ymd(MARTES)}`);
  await expect(libre).toBeVisible();
  await libre.click();
  await p.getByRole('combobox', { name: 'Duración' }).selectOption(String(DUR_MIN));
  await captura(p, '2-horario');
  await p.getByRole('button', { name: 'Continuar' }).click();
  await expect(p.getByRole('heading', { level: 1 })).toHaveText('Servicio y precio');
  await p.getByRole('radio', { name: /Grabación de voces/ }).check();
  await p.getByRole('checkbox', { name: /Productor o arreglista/ }).check();
  const precio = p.getByRole('region', { name: 'Precio simulado' });
  const fila = precio.getByRole('row', { name: /^Total/i });
  await expect(fila).toBeVisible();
  const simulacion = await (await fetch(`${API}/simulaciones`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ id_sala: idSala, id_servicio: idServicio, inicio: inicio(MARTES, '10:00'), fin: inicio(MARTES, '12:00'), especialistas: [idProductor] }),
  })).json();
  const soles = (m) => `S/ ${Number(m).toFixed(2).replace('.', ',')}`; // la simulación de prueba queda bajo S/ 1 000: sin separador de millares
  await expect(fila).toContainText(soles(simulacion.total));
  await expect(precio.getByRole('row', { name: /Anticipo/i })).toContainText(soles(simulacion.anticipo));
  total = soles(simulacion.total);
  await captura(p, '2-servicio-simulacion');
  await p.getByRole('button', { name: 'Continuar' }).click();
  // Sin sesión: el acceso conserva la elección en `volver`; se crea la cuenta desde ahí y se vuelve a confirmar.
  await expect(p).toHaveURL(/\/acceso\/?\?volver=/);
  await captura(p, '2-acceso');
  await p.getByRole('link', { name: 'Crear cuenta de artista' }).click();
  await rellenarRegistro(p, clienteA);
  // RF-17: sin documento ni textos aceptados, el alta vuelve por "Completa tus datos" (paso 03) y de ahi al tramo elegido.
  await p.waitForURL(/\/reservar\/cuenta\//);
  await expect(p.getByRole('heading', { level: 1 })).toHaveText('Completa tus datos');
  await p.locator('[name="tipo_documento"]').selectOption('dni');
  await p.locator('[name="numero_documento"]').fill(dniNuevo());
  await p.getByRole('checkbox', { name: /Acepto los Términos de uso/ }).check();
  await p.getByRole('button', { name: 'Guardar y continuar' }).click();
  await p.waitForURL(/\/reservar\/confirmar\//);
  await expect(p.getByRole('heading', { level: 1 })).toHaveText('Confirma tu reserva');
  await p.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
  await captura(p, '2-confirmar');
  await confirmarReserva(p);
  await p.waitForURL(/\/reservar\/listo\/\?id=/);
  await expect(p.getByRole('heading', { level: 1 })).toHaveText('Reserva registrada');
  folio = (await p.getByText(FOLIO).first().textContent()).match(FOLIO)[0];
  await expect(p.getByText('PRE-RESERVADA')).toBeVisible();
  await expect(p.getByText(/Paga el anticipo de .* antes del/)).toBeVisible();
  await captura(p, '2-listo');
});

test('3. el correo reserva_creada llega a Mailpit con el folio y la fecha límite', async () => {
  const texto = await correoDe(clienteA.correo, `Reserva ${folio} registrada`);
  expect(texto).toContain(`Folio: ${folio}`);
  expect(texto).toMatch(/Fecha límite de pago: \S+ \d+ de \S+ de \d{4}, \d{2}:\d{2}/);
  expect(texto).toContain(`Total: ${total}`);
});

test('4. Mis reservas muestra el plazo; otro cliente ve el tramo ocupado sin datos; el Administrador ve la agenda', async ({ browser }) => {
  await paginaA.goto('/app/reservas/');
  const filas = paginaA.getByRole('row').filter({ hasText: folio });
  await expect(filas).toHaveCount(1);
  await expect(filas).toContainText(/faltan|vence|antes/i);
  await captura(paginaA, '4-mis-reservas');

  paginaB = await registrar(browser, clienteB);
  await paginaB.goto(`/reservar/?fecha=${ymd(MARTES)}`);
  await expect(paginaB.getByText(/^OCUPADO/).first()).toBeVisible();
  await expect(paginaB.getByRole('button', { name: etiqueta(MARTES, '10:00') + ', libre' })).toHaveCount(0);
  await expect(paginaB.locator('main')).not.toContainText(clienteA.nombre);
  await expect(paginaB.locator('main')).not.toContainText(folio);
  await captura(paginaB, '4-tramo-ocupado-otro-cliente');

  await paginaAdmin.goto(`/app/agenda/?vista=semana&fecha=${ymd(MARTES)}`);
  await expect(paginaAdmin.locator('main')).toContainText(clienteA.nombre);
  await expect(paginaAdmin.locator('main')).toContainText('Grabación de voces');
  await captura(paginaAdmin, '4-agenda-administrador');
});

test('5. el cliente cancela desde el detalle y el tramo vuelve a estar libre', async () => {
  await paginaA.goto('/app/reservas/');
  await paginaA.getByRole('link', { name: new RegExp(`Ver reserva ${folio}`) }).click();
  await expect(paginaA.getByRole('heading', { level: 1 })).toHaveText(new RegExp(folio, 'i'));
  await paginaA.getByRole('button', { name: 'Solicitar cancelación' }).click(); // desde RF-18 el cliente ve la vista previa y confirma
  await captura(paginaA, '5-confirmar-cancelacion');
  await paginaA.getByRole('button', { name: 'Confirmar cancelación' }).click();
  await expect(paginaA.getByText('Cancelada', { exact: true }).first()).toBeVisible();
  await captura(paginaA, '5-cancelada');
  await paginaB.goto(`/reservar/?fecha=${ymd(MARTES)}`);
  await expect(paginaB.getByRole('button', { name: etiqueta(MARTES, '10:00') + ', libre' })).toBeVisible();
  await captura(paginaB, '5-tramo-libre');
});

test('6. una reserva vencida caduca: el tramo queda libre y llega reserva_caducada', async () => {
  await paginaA.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(MIERCOLES, '10:00'))}&duracion=60&sala=${idSala}&servicio=${idServicio}`);
  await confirmarReserva(paginaA);
  await paginaA.waitForURL(/\/reservar\/listo\/\?id=/);
  const segunda = (await paginaA.getByText(FOLIO).first().textContent()).match(FOLIO)[0];
  expect(PY('caducar.py', segunda)).toBe('1');
  const texto = await correoDe(clienteA.correo, `Reserva ${segunda} caducada`);
  expect(texto).toContain(segunda);
  await paginaB.goto(`/reservar/?fecha=${ymd(MIERCOLES)}`);
  await expect(paginaB.getByRole('button', { name: etiqueta(MIERCOLES, '10:00') + ', libre' })).toBeVisible();
  await paginaA.goto('/app/reservas/?ver=historial');
  await expect(paginaA.getByRole('row').filter({ hasText: segunda })).toContainText(/Caducó sin pago|Caducada/);
  await captura(paginaA, '6-historial-caducada');
});
