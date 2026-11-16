// Pago de punta a punta (RF-05 CA-01..09, RF-06 CA-01..05) contra Supabase, Storage, backend (8010) y Mailpit reales: sin page.route.
// Fechas desde ahora en Lima (la semana siguiente cae dentro de la ventana de reserva). `npm run test:e2e:real`.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const API = 'http://127.0.0.1:8010/api/v1';
const BACKEND = resolve(import.meta.dirname, '../../../backend');
const PY = (script, ...args) => execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, script), ...args], { cwd: BACKEND, encoding: 'utf8' }).trim();
const FOLIO = /R-\d{4}-\d+/;
const CAPTURAS = 'pruebas/capturas/real-pagos';
// Solo pruebas: la clave de servicio borra los objetos de Storage que crea el recorrido (Configuracion y src/ no la conocen).
const claveServicio = () => process.env.CLAVE_SERVICIO_SUPABASE_PRUEBAS ?? readFileSync(resolve(BACKEND, '.env'), 'utf8').match(/^CLAVE_SERVICIO_SUPABASE_PRUEBAS=(.+)$/m)?.[1].trim();

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `pag-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Admin');
const cliente = persona('a', 'Cora Pagos');
const correos = [admin.correo, cliente.correo];

const lima = new Date(Date.now() - 5 * 3600_000);
const lunesSiguiente = new Date(Date.UTC(lima.getUTCFullYear(), lima.getUTCMonth(), lima.getUTCDate() + (8 - (lima.getUTCDay() || 7))));
const dia = (n) => new Date(lunesSiguiente.getTime() + n * 86400_000);
const ymd = (d) => d.toISOString().slice(0, 10);
const inicio = (d, hora) => `${ymd(d)}T${hora}:00-05:00`;
const MARTES = dia(1);
const MIERCOLES = dia(2);

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const PDF = Buffer.from('%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n');

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ browser }) => {
  try {
    const [auth, mail, api] = await Promise.all([fetch(`${SUPABASE}/auth/v1/health`), fetch(`${MAILPIT}/api/v1/info`), fetch(`${API}/salas`)]);
    if (!auth.ok || !mail.ok || !api.ok) throw new Error(`Auth ${auth.status}, Mailpit ${mail.status}, API ${api.status}`);
    if (!claveServicio()) throw new Error('falta CLAVE_SERVICIO_SUPABASE_PRUEBAS (entorno o backend/.env)');
  } catch (error) {
    const motivo = `Falta el stack local (Supabase ${SUPABASE}, Mailpit ${MAILPIT}, API ${API}) o la clave de pruebas: ${error.message}`;
    if (process.env.EXIGIR_INTEGRACION) throw new Error(motivo);
    test.skip(true, motivo);
  }
  const p = await browser.newPage();
  for (const ruta of ['/acceso', '/acceso/registro', '/acceso/interno', '/app/', '/app/franjas/', '/reservar/confirmar/', '/reservar/listo/', '/app/reservas/', '/app/reservas/detalle', '/app/reservas/pagar', '/app/pagos/', '/app/pagos/revisar']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  // Siempre: sin usuarios, reservas, cuotas, comprobantes, avisos, franjas ni objetos en Storage.
  const ids = JSON.parse(PY('capturas.py', ...correos));
  const clave = claveServicio();
  const cabeceras = { apikey: clave, authorization: `Bearer ${clave}`, 'content-type': 'application/json' };
  let restos = 0;
  let borrados = 0;
  try {
    for (const id of ids) {
      const listar = async () => (await (await fetch(`${SUPABASE}/storage/v1/object/list/comprobantes`, { method: 'POST', headers: cabeceras, body: JSON.stringify({ prefix: id, limit: 100 }) })).json()).map((o) => `${id}/${o.name}`);
      const objetos = await listar();
      borrados += objetos.length;
      if (objetos.length) await fetch(`${SUPABASE}/storage/v1/object/comprobantes`, { method: 'DELETE', headers: cabeceras, body: JSON.stringify({ prefixes: objetos }) });
      restos += (await listar()).length;
    }
  } finally {
    console.log(PY('limpiar.py', ...correos));
  }
  console.log(`Storage: ${borrados} objetos borrados, ${restos} huérfanos en comprobantes.`);
  expect(restos).toBe(0);
});

const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png`, fullPage: true });
const entrar = async (page, ruta, p, boton) => {
  await page.goto(ruta);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: boton }).click();
};
const registrar = async (browser, p) => {
  const page = await nuevaPagina(browser);
  await page.goto('/acceso/registro');
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await page.waitForURL('**/app/perfil?aviso=cuenta-creada');
  return page;
};

async function correoDe(correo, asunto) {
  for (let i = 0; i < 100; i++) {
    const { messages } = await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${correo} subject:"${asunto}"`)}`)).json();
    if (messages.length) return (await (await fetch(`${MAILPIT}/api/v1/message/${messages[0].ID}`)).json()).Text;
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`No llegó el correo "${asunto}" a ${correo}`);
}
const catalogo = async (ruta, nombre) => {
  const lista = await (await fetch(`${API}/${ruta}`)).json();
  return nombre ? lista.find((x) => x.nombre === nombre) : lista[0];
};

let paginaAdmin, paginaA, folio, idReserva, idSala, idServicio;
const op1 = `OP${marca}1`.toUpperCase(); // la app guarda el número de operación en mayúsculas
const op2 = `OP${marca}2`.toUpperCase();

const reservar = async (page, d, hora, duracion) => {
  await page.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(d, hora))}&duracion=${duracion}&sala=${idSala}&servicio=${idServicio}`);
  await page.getByRole('button', { name: 'Confirmar reserva' }).click();
  await page.waitForURL(/\/reservar\/listo\/\?id=/);
  return (await page.getByText(FOLIO).first().textContent()).match(FOLIO)[0];
};
const abrirDetalle = async (page, f, lista = '/app/reservas/') => {
  await page.goto(lista);
  await page.getByRole('link', { name: new RegExp(`Ver reserva ${f}`) }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(new RegExp(f, 'i'));
};
const registrarPago = async (page, operacion, archivo) => {
  await page.getByRole('link', { name: 'Registrar pago' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/registrar pago/i);
  await page.getByRole('radio', { name: 'Yape' }).check();
  await page.getByLabel(/Número de operación/).fill(operacion);
  await page.getByLabel(/Captura del comprobante/).setInputFiles(archivo);
  await page.getByRole('button', { name: 'Registrar pago' }).click();
  await page.waitForURL(/\/app\/reservas\/detalle\?id=.*/);
};

test('1. el Administrador publica franjas y el cliente reserva', async ({ browser }) => {
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
  await paginaAdmin.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(paginaAdmin.getByText('Franjas publicadas. Ya se ven en el calendario.')).toBeVisible();
  idSala = (await catalogo('salas')).id;
  idServicio = (await catalogo('servicios', 'Grabación de voces')).id;
  paginaA = await registrar(browser, cliente);
  folio = await reservar(paginaA, MARTES, '10:00', 120);
  await expect(paginaA.getByText('PRE-RESERVADA')).toBeVisible();
});

test('2. el cliente registra el pago con un PNG y queda en validación; el Administrador recibe pago_registrado', async () => {
  await abrirDetalle(paginaA, folio);
  idReserva = new URL(paginaA.url()).searchParams.get('id');
  await captura(paginaA, '1-detalle-pendiente');
  await paginaA.getByRole('link', { name: 'Registrar pago' }).click();
  await paginaA.getByRole('radio', { name: 'Yape' }).check();
  await expect(paginaA.getByLabel(/Monto pagado/)).not.toHaveValue('');
  await paginaA.getByLabel(/Número de operación/).fill(op1);
  await paginaA.getByLabel(/Captura del comprobante/).setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await captura(paginaA, '2-formulario-pago');
  await paginaA.getByRole('button', { name: 'Registrar pago' }).click();
  await paginaA.waitForURL(/\/app\/reservas\/detalle\?id=/);
  await expect(paginaA.locator('[data-estado-reserva]')).toContainText('Pago en validación');
  await expect(paginaA.getByText('Pago por validar', { exact: true })).toBeVisible();
  await expect(paginaA.getByRole('row', { name: /Al reservar/ })).toContainText('En validación');
  await captura(paginaA, '3-detalle-en-validacion');
  const texto = await correoDe(admin.correo, `Pago por validar de la reserva ${folio}`);
  expect(texto).toContain(`Número de operación: ${op1}`);
});

test('3. el Administrador ve el contador, la captura cargada desde Storage y rechaza con motivo', async () => {
  await paginaAdmin.goto('/app/');
  await expect(paginaAdmin.locator('[data-contador="pagos"]:visible')).toContainText('1');
  await captura(paginaAdmin, '4-contador-pagos');
  await paginaAdmin.goto('/app/pagos/');
  await paginaAdmin.getByRole('link', { name: `Revisar pago de ${folio}` }).click();
  const img = paginaAdmin.getByRole('img', { name: /Captura del comprobante/ });
  await expect(img).toBeVisible();
  await expect(img).toHaveAttribute('src', new RegExp(`^${SUPABASE}/storage/v1/`));
  await expect.poll(() => img.evaluate((i) => i.complete && i.naturalWidth)).toBeGreaterThan(0);
  await captura(paginaAdmin, '5-revisar-captura');
  await paginaAdmin.getByRole('button', { name: 'Rechazar pago' }).click();
  await paginaAdmin.getByLabel(/Motivo del rechazo/).fill('La captura no se lee');
  await paginaAdmin.getByRole('button', { name: 'Rechazar pago' }).last().click();
  await expect(paginaAdmin).toHaveURL(/aviso=pago-rechazado|\/app\/pagos\/$/);
  const texto = await correoDe(cliente.correo, `Pago rechazado de la reserva ${folio}`);
  expect(texto).toContain('Motivo: La captura no se lee');
  await paginaA.goto(`/app/reservas/detalle?id=${idReserva}`);
  await expect(paginaA.getByRole('row', { name: /Al reservar/ })).toContainText('La captura no se lee');
  await captura(paginaA, '6-detalle-rechazo');
});

test('4. otro pago con un PDF: el cliente ve el contacto en vez de Cancelar; el Administrador lo aprueba y la reserva queda Confirmada', async () => {
  await registrarPago(paginaA, op2, { name: 'voucher.pdf', mimeType: 'application/pdf', buffer: PDF });
  await expect(paginaA.getByRole('row', { name: /Al reservar/ })).toContainText('En validación');
  // Con un pago registrado (reserva aún pre-reservada) el cliente no cancela: ve el aviso y el contacto del estudio.
  await expect(paginaA.getByRole('button', { name: 'Cancelar reserva' })).toHaveCount(0);
  await expect(paginaA.getByText('Ya registraste un pago, así que la cancelación la gestiona el estudio.')).toBeVisible();
  await expect(paginaA.getByText(/Escribenos por WhatsApp al 999 999 999/)).toBeVisible();
  await captura(paginaA, '9-sin-cancelar-contacto');
  await paginaAdmin.goto('/app/pagos/');
  await paginaAdmin.getByRole('link', { name: `Revisar pago de ${folio}` }).click();
  await expect(paginaAdmin.getByRole('link', { name: /Abrir comprobante\.pdf/ })).toHaveAttribute('href', new RegExp(`^${SUPABASE}/storage/v1/`));
  await captura(paginaAdmin, '7-revisar-pdf');
  await paginaAdmin.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(paginaAdmin).toHaveURL(/aviso=reserva-confirmada/);
  const texto = await correoDe(cliente.correo, `Pago aprobado de la reserva ${folio}`);
  expect(texto).toContain('confirmada');
  await paginaA.goto(`/app/reservas/detalle?id=${idReserva}`);
  await expect(paginaA.locator('[data-estado-reserva]')).toContainText('Confirmada');
  await captura(paginaA, '8-detalle-confirmada');
});

test('5. confirmada y con pagos el cliente no cancela y el Administrador cancela con nota', async () => {
  await expect(paginaA.getByRole('button', { name: 'Cancelar reserva' })).toHaveCount(0);
  await paginaAdmin.goto(`/app/reservas/detalle?id=${idReserva}`);
  await paginaAdmin.getByRole('button', { name: 'Cancelar reserva', exact: true }).click();
  await paginaAdmin.getByRole('button', { name: `Cancelar reserva ${folio}` }).click();
  await expect(paginaAdmin.getByText('Escribe qué pasa con el pago: cómo se devuelve o por qué no.', { exact: true }).first()).toBeVisible();
  await paginaAdmin.getByLabel(/Nota sobre el reembolso/).fill('Devolvemos todo por Yape en 48 h');
  await captura(paginaAdmin, '10-cancelar-nota');
  await paginaAdmin.getByRole('button', { name: `Cancelar reserva ${folio}` }).click();
  await expect(paginaAdmin.locator('[data-avisos] .aviso')).toContainText('Reserva cancelada');
  await paginaA.goto(`/app/reservas/detalle?id=${idReserva}`);
  await expect(paginaA.locator('[data-estado-reserva]')).toContainText('Nota del estudio: Devolvemos todo por Yape en 48 h');
  await captura(paginaA, '11-detalle-cancelada-nota');
  const texto = await correoDe(cliente.correo, `Reserva ${folio} cancelada por el estudio`);
  expect(texto).toContain('Nota del estudio: Devolvemos todo por Yape en 48 h');
});

test('6. una reserva confirmada que ya terminó pasa a Finalizada con saldo y aviso', async () => {
  const segunda = await reservar(paginaA, MIERCOLES, '10:00', 60);
  expect(PY('finalizar.py', segunda)).toBe('1');
  const texto = await correoDe(cliente.correo, `Saldo pendiente de la reserva ${segunda}`);
  expect(texto).toContain('saldo pendiente');
  await abrirDetalle(paginaA, segunda, '/app/reservas/?ver=historial'); // las finalizadas viven en el historial
  await expect(paginaA.locator('[data-estado-reserva]')).toContainText(/Falta pagar el resto: S\/ /);
  await expect(paginaA.getByRole('link', { name: 'Registrar pago' })).toBeVisible();
  await captura(paginaA, '12-finalizada-saldo');
});
