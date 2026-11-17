// RF-18 de punta a punta contra Supabase, Storage, backend (8010) y Mailpit reales: sin page.route. `npm run test:e2e:real`.
// Cancelar por niveles, crédito, devolución, pagar con crédito, reprogramar, cancelación del estudio, inasistencia y caso excepcional.
// Los niveles 2 y 3 y la inasistencia dependen de la hora: la reserva se crea con el horario de la semana siguiente (anticipación mínima) y mover.py
// le cambia el inicio por SQL de administración (solo pruebas), igual que finalizar.py y caducar.py.
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';
import { API, BACKEND, cargarTextos, llamar, prepararCliente, confirmarReserva, dia, inicio, vaciarComprobantes } from './ayudas.js';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const PY = (script, ...args) => execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, script), ...args], { cwd: BACKEND, encoding: 'utf8' }).trim();
const FOLIO = /R-\d{4}-\d+/;
const CAPTURAS = 'pruebas/capturas/real-rf18';
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `r18-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Cancelaciones');
const ana = persona('ana', 'Ana Creditos');
const dora = persona('dora', 'Dora Estudio');
const eva = persona('eva', 'Eva Niveles');
const pablo = persona('pablo', 'Pablo Personal');
const correos = [admin.correo, ana.correo, dora.correo, eva.correo, pablo.correo];
const MARTES = dia(1);
const MIERCOLES = dia(2);
const JUEVES = dia(3);

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
  for (const ruta of ['/acceso', '/acceso/registro', '/acceso/interno', '/app/', '/app/franjas/', '/reservar/confirmar/', '/reservar/listo/', '/app/reservas/', '/app/reservas/detalle', '/app/reservas/pagar', '/app/reservas/creditos', '/app/reservas/reprogramar', '/app/pagos/', '/app/pagos/revisar', '/app/pagos/devoluciones/', '/app/pagos/devoluciones/revisar', '/app/agenda/']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  // Siempre: sin usuarios, reservas, créditos, devoluciones, reprogramaciones, comprobantes, avisos, franjas ni objetos en Storage.
  let borrados = 0;
  try {
    borrados = await vaciarComprobantes(JSON.parse(PY('capturas.py', ...correos)));
  } finally {
    console.log(PY('limpiar.py', ...correos));
  }
  console.log(`Storage: ${borrados} objetos borrados, 0 huérfanos en comprobantes.`);
});

const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png`, fullPage: true });
const registrar = async (browser, p) => {
  const page = await nuevaPagina(browser);
  await page.goto('/acceso/registro');
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await page.waitForURL('**/acceso/textos*');
  await prepararCliente(page);
  await page.goto('/app/perfil');
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
const soles = (texto) => Number(texto);

let paginaAdmin, paginaAna, paginaDora, paginaEva, paginaPablo, idSala, idServicio, n = 0;

// Reserva y devuelve folio e id (la reserva queda pre-reservada).
const reservar = async (page, d, hora, duracion) => {
  await page.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(d, hora))}&duracion=${duracion}&sala=${idSala}&servicio=${idServicio}`);
  await confirmarReserva(page);
  await page.waitForURL(/\/reservar\/listo\/\?id=/);
  const id = new URL(page.url()).searchParams.get('id');
  return { id, folio: (await page.getByText(FOLIO).first().textContent()).match(FOLIO)[0] };
};
// El cliente registra el pago del adelanto (captura) y el Administrador lo aprueba: la reserva queda confirmada.
const pagarYAprobar = async (page, { id, folio }) => {
  await page.goto(`/app/reservas/detalle?id=${id}`);
  await page.getByRole('link', { name: 'Registrar pago' }).click();
  await page.getByRole('radio', { name: 'Yape' }).check();
  await page.getByLabel(/Número de operación/).fill(`OP${marca}${++n}`.toUpperCase());
  await page.getByLabel(/Captura del comprobante/).setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await page.getByRole('button', { name: 'Registrar pago' }).click();
  await page.waitForURL(/\/app\/reservas\/detalle\?id=/);
  await aprobar(folio);
  await page.goto(`/app/reservas/detalle?id=${id}`);
  await expect(page.locator('[data-estado-reserva]')).toContainText('Confirmada');
};
const aprobar = async (folio) => {
  await paginaAdmin.goto('/app/pagos/');
  await paginaAdmin.getByRole('link', { name: `Revisar pago de ${folio}` }).click();
  await paginaAdmin.getByRole('button', { name: 'Aprobar pago' }).click();
  await expect(paginaAdmin.getByText('La reserva quedó confirmada y avisamos al cliente.')).toBeVisible();
};
const reservaApi = async (page, id) => (await llamar(page, 'GET', `/reservas/${id}`)).cuerpo;
const creditos = async (page) => (await llamar(page, 'GET', '/creditos')).cuerpo;

let ra, saldoAna, devolucionAna; // reserva de (a)

test('0. el Administrador publica franjas; los clientes y el personal se registran', async ({ browser }) => {
  paginaAdmin = await registrar(browser, admin);
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
  for (const nombre of ['martes', 'miércoles', 'jueves']) {
    const grupo = paginaAdmin.getByRole('group', { name: new RegExp(`^${nombre.toUpperCase()} `) });
    if (!(await grupo.getByLabel('Desde').count())) await grupo.getByRole('button', { name: `Añadir franja al ${nombre}` }).click();
    await grupo.getByLabel('Desde').fill('09:00');
    await grupo.getByLabel('Hasta').fill('20:00');
  }
  await paginaAdmin.getByRole('button', { name: 'Publicar franjas' }).click();
  await expect(paginaAdmin.getByText('Franjas publicadas. Ya se ven en el calendario.')).toBeVisible();
  idSala = (await catalogo('salas')).id;
  idServicio = (await catalogo('servicios', 'Grabación de voces')).id;
  paginaAna = await registrar(browser, ana);
  paginaDora = await registrar(browser, dora);
  paginaEva = await registrar(browser, eva);
  // Personal: solicita acceso y el Administrador lo aprueba por la API (la UI de solicitudes ya la cubre rf01.real.spec.js).
  paginaPablo = await registrar(browser, pablo);
  const solicitud = await llamar(paginaPablo, 'POST', '/solicitudes-acceso', { especialidad: 'Ingeniería de sonido' });
  expect(solicitud.estado, JSON.stringify(solicitud.cuerpo)).toBe(201);
  const aprobada = await llamar(paginaAdmin, 'POST', `/solicitudes-acceso/${solicitud.cuerpo.id}/aprobar`, { rol: 'personal', especialidad: 'Ingeniería de sonido' });
  expect(aprobada.estado, JSON.stringify(aprobada.cuerpo)).toBe(200);
});

test('a1. cancelación en nivel 1 desde "Mis reservas": vista previa, confirmación y crédito en "Mis créditos"', async () => {
  ra = await reservar(paginaAna, MARTES, '10:00', 120);
  await pagarYAprobar(paginaAna, ra);
  const antes = await reservaApi(paginaAna, ra.id);
  const pagado = antes.pagado;
  expect(soles(pagado)).toBeGreaterThan(0);

  await paginaAna.goto('/app/reservas/');
  await paginaAna.getByRole('link', { name: new RegExp(`Ver reserva ${ra.folio}`) }).click();
  await paginaAna.getByRole('button', { name: 'Solicitar cancelación' }).click();
  const panel = paginaAna.getByRole('region', { name: new RegExp(`Cancelar reserva ${ra.folio}`) });
  await expect(panel).toContainText('Nivel 1: avisas con más de 48 h.');
  await expect(panel.locator('dl')).toContainText('S/ 0,00'); // retiene 0
  await expect(panel.getByRole('link', { name: 'Leer las condiciones de cancelación' })).toHaveAttribute('href', '/legal/condiciones-de-contratacion/');
  await expect(panel.getByRole('button', { name: 'Volver a la reserva' })).toBeVisible();
  await captura(paginaAna, 'a1-vista-previa-nivel1');
  await panel.getByRole('button', { name: 'Confirmar cancelación' }).click();
  await expect(paginaAna.locator('[data-estado-reserva]')).toContainText('Cancelada');
  await captura(paginaAna, 'a1-cancelada');

  const despues = await reservaApi(paginaAna, ra.id);
  expect(despues.estado).toBe('cancelada');
  expect(despues.cancelacion).toMatchObject({ nivel: 1, por: 'cliente', pagado, retenido: '0.00', credito: pagado });
  await paginaAna.goto('/app/reservas/creditos');
  const fila = paginaAna.getByRole('row', { name: new RegExp(ra.folio) }).first();
  await expect(fila).toBeVisible();
  await expect(fila).toContainText('Vigente');
  await captura(paginaAna, 'a1-mis-creditos');
  const lista = await creditos(paginaAna);
  expect(lista).toHaveLength(1);
  expect(lista[0]).toMatchObject({ tipo: 'nivel_1', saldo: pagado, estado: 'vigente' });
  const texto = await correoDe(ana.correo, `Cancelamos tu reserva ${ra.folio}`);
  expect(texto).toContain(ra.folio);
});

test('a2. pide la devolución; el Administrador la decide parcial y la marca realizada', async () => {
  const [credito] = await creditos(paginaAna);
  await paginaAna.goto('/app/reservas/creditos');
  await paginaAna.getByRole('button', { name: `Pedir devolución de ${ra.folio}` }).click();
  const region = paginaAna.getByRole('region', { name: new RegExp(`Pedir devolución · ${ra.folio}`) });
  await region.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(paginaAna.getByText('Escribe el motivo, de 10 a 500 caracteres.')).toBeVisible();
  await region.getByLabel(/Motivo/).fill('Prefiero el dinero, no voy a reservar de nuevo.');
  await region.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(paginaAna.getByRole('row', { name: new RegExp(ra.folio) }).first()).toContainText('Devolución pedida el');
  await captura(paginaAna, 'a2-devolucion-pedida');
  const pendiente = (await creditos(paginaAna))[0];
  expect(pendiente.devolucion).toMatchObject({ estado: 'pendiente', motivo: 'Prefiero el dinero, no voy a reservar de nuevo.' });
  devolucionAna = pendiente.devolucion.id;
  await correoDe(admin.correo, 'Devolución por decidir'); // el Administrador recibe el aviso de la solicitud

  // El Administrador la ve en la cola y decide una parte (la mitad).
  const parte = (soles(credito.saldo) / 2).toFixed(2);
  await paginaAdmin.goto('/app/pagos/devoluciones/');
  await expect(paginaAdmin.getByRole('row').filter({ hasText: ra.folio })).toBeVisible();
  await paginaAdmin.getByRole('link', { name: `Revisar devolución de ${ra.folio}` }).click();
  await paginaAdmin.getByRole('radio', { name: /Devolver una parte/ }).check();
  await paginaAdmin.getByLabel(/Monto a devolver/).fill(parte.replace('.', ','));
  await paginaAdmin.getByLabel(/^Motivo/).fill('Devolvemos la mitad y el resto queda como crédito.');
  await captura(paginaAdmin, 'a2-decidir-parcial');
  await paginaAdmin.getByRole('button', { name: /Registrar decisión|Aprobar|Rechazar/ }).first().click();
  await paginaAdmin.waitForURL(/aviso=devolucion-decidida/);
  const decidida = (await llamar(paginaAdmin, 'GET', `/devoluciones/${devolucionAna}`)).cuerpo;
  expect(decidida).toMatchObject({ estado: 'aprobada', monto_aprobado: parte });
  saldoAna = (soles(credito.saldo) - soles(parte)).toFixed(2);
  expect(soles((await creditos(paginaAna))[0].saldo)).toBe(soles(saldoAna)); // el resto queda como crédito

  await paginaAdmin.goto(`/app/pagos/devoluciones/revisar?id=${devolucionAna}`);
  await paginaAdmin.getByLabel(/Nota/).fill(`Yape ${marca} operación 123456`);
  await paginaAdmin.getByRole('button', { name: 'Marcar como realizada' }).click();
  await expect.poll(async () => (await llamar(paginaAdmin, 'GET', `/devoluciones/${devolucionAna}`)).cuerpo.estado).toBe('realizada');
  await captura(paginaAdmin, 'a2-realizada');
  await correoDe(ana.correo, 'Te devolvimos el dinero');
});

let rb; // reserva de (b), luego reprogramada en (c)

test('b. pago con crédito parcial de una reserva nueva y captura por el resto; aprobación y reserva confirmada', async () => {
  rb = await reservar(paginaAna, MIERCOLES, '10:00', 60);
  await paginaAna.goto(`/app/reservas/detalle?id=${rb.id}`);
  await paginaAna.getByRole('link', { name: 'Registrar pago' }).click();
  const casilla = paginaAna.getByRole('checkbox', { name: /Usar mi crédito/ });
  await expect(paginaAna.getByText(/Usar mi crédito \(S\/ .* disponible\)/)).toBeVisible();
  await casilla.check();
  await paginaAna.getByRole('button', { name: 'Aplicar crédito' }).click();
  await expect(paginaAna.getByText(/Aplicaste S\/ .* de crédito/)).toBeVisible();
  await captura(paginaAna, 'b-credito-aplicado');
  expect((await creditos(paginaAna))[0]).toMatchObject({ saldo: '0.00', estado: 'agotado' });
  const r = await reservaApi(paginaAna, rb.id);
  const adelanto = r.cuotas.find((c) => c.hito === 'al_reservar');
  expect(soles(adelanto.pagado)).toBe(soles(saldoAna));
  expect(adelanto.estado).not.toBe('pagada'); // el crédito cubrió solo una parte
  expect(r.estado).toBe('pre_reservada');
  // Captura por el resto: el monto viene calculado.
  await paginaAna.getByRole('radio', { name: 'Yape' }).check();
  await expect(paginaAna.getByLabel(/Monto pagado/)).toHaveValue(new RegExp((soles(adelanto.monto) - soles(saldoAna)).toFixed(2).replace('.', '[.,]')));
  await paginaAna.getByLabel(/Número de operación/).fill(`OP${marca}${++n}`.toUpperCase());
  await paginaAna.getByLabel(/Captura del comprobante/).setInputFiles({ name: 'voucher.png', mimeType: 'image/png', buffer: PNG });
  await paginaAna.getByRole('button', { name: 'Registrar pago' }).click();
  await paginaAna.waitForURL(/\/app\/reservas\/detalle\?id=/);
  await expect(paginaAna.locator('[data-estado-reserva]')).toContainText('Pago en validación');
  await aprobar(rb.folio);
  await paginaAna.goto(`/app/reservas/detalle?id=${rb.id}`);
  await expect(paginaAna.locator('[data-estado-reserva]')).toContainText('Confirmada');
  await captura(paginaAna, 'b-confirmada');
  const final = await reservaApi(paginaAna, rb.id);
  expect(final.pagado).toBe(adelanto.monto);
});

test('c. reprogramar una confirmada en nivel 1 a otro horario, incluso 30 min (solapando el suyo), con historial y nuevo saldo', async () => {
  const antes = await reservaApi(paginaAna, rb.id);
  await paginaAna.goto(`/app/reservas/detalle?id=${rb.id}`);
  await paginaAna.getByRole('link', { name: 'Reprogramar', exact: true }).click();
  await expect(paginaAna.getByRole('heading', { name: /R1\s*Elige el nuevo horario/ })).toBeVisible();
  // 10:30 solapa con el horario actual (10:00 a 11:00): la disponibilidad excluye la propia reserva.
  const nuevo = new Date(inicio(MIERCOLES, '10:30')).toISOString();
  await paginaAna.locator(`bugalu-calendario button[data-inicio="${nuevo}"]`).locator('visible=true').first().click();
  await expect(paginaAna.getByRole('region', { name: /Cómo queda/ })).toBeVisible();
  await captura(paginaAna, 'c-reprogramar-vista-previa');
  await paginaAna.getByRole('button', { name: 'Confirmar reprogramación' }).click();
  await paginaAna.waitForURL(/\/app\/reservas\/detalle\?id=/);
  const despues = await reservaApi(paginaAna, rb.id);
  expect(new Date(despues.inicio).toISOString()).toBe(nuevo);
  expect(despues.id).toBe(antes.id);
  expect(despues.folio).toBe(antes.folio);
  expect(despues.reprogramaciones).toHaveLength(1);
  expect(despues.reprogramaciones[0]).toMatchObject({ nivel: 1, penalizacion: '0.00' });
  expect(despues.reprogramaciones[0].total_nuevo).toBe(despues.reprogramaciones[0].total_anterior); // mismas tarifas, mismo precio
  expect(new Date(despues.reprogramaciones[0].anterior_inicio).toISOString()).toBe(new Date(antes.inicio).toISOString());
  expect(despues.estado).toBe('confirmada');
  expect(despues.pagado).toBe(antes.pagado);
  const saldo = despues.cuotas.find((c) => c.hito === 'al_terminar');
  await expect(paginaAna.getByText(/Reprogramaste|reprogram/i).first()).toBeVisible();
  await expect(paginaAna.locator('main')).toContainText(new RegExp(`S/ ${soles(saldo.monto).toFixed(2).replace('.', ',')}`));
  await captura(paginaAna, 'c-detalle-reprogramada');
  await correoDe(ana.correo, `Reprogramamos tu reserva ${rb.folio}`);
});

let rd;

test('d. el Administrador cancela por el estudio una reserva con pagos; el cliente elige la devolución íntegra y aparece en la cola con su plazo', async () => {
  rd = await reservar(paginaDora, JUEVES, '10:00', 60);
  await pagarYAprobar(paginaDora, rd);
  const pagado = (await reservaApi(paginaDora, rd.id)).pagado;
  await paginaAdmin.goto(`/app/reservas/detalle?id=${rd.id}`);
  await paginaAdmin.getByRole('button', { name: 'Cancelar reserva', exact: true }).click();
  const panel = paginaAdmin.getByRole('region', { name: new RegExp(`Cancelar reserva ${rd.folio}`) });
  await panel.getByRole('radio', { name: /El estudio/ }).check();
  await panel.getByLabel(/Nota para el cliente/).fill('Falla eléctrica en la cabina');
  await captura(paginaAdmin, 'd-cancelar-por-el-estudio');
  await panel.getByRole('button', { name: `Cancelar reserva ${rd.folio}` }).click();
  await expect(paginaAdmin.locator('[data-avisos] .aviso')).toContainText('Reserva cancelada');
  expect((await reservaApi(paginaDora, rd.id)).eleccion_estudio).toBe('pendiente');
  await correoDe(dora.correo, `Reserva ${rd.folio} cancelada por el estudio`);

  await paginaDora.goto(`/app/reservas/detalle?id=${rd.id}`);
  await expect(paginaDora.getByRole('link', { name: 'Reprogramar sin costo' })).toBeVisible();
  await captura(paginaDora, 'd-elegir');
  await paginaDora.getByRole('button', { name: 'Pedir la devolución íntegra' }).click();
  await expect(paginaDora.getByRole('region', { name: new RegExp(`Devolución íntegra · ${rd.folio}`) })).toBeVisible();
  await paginaDora.getByRole('button', { name: 'Confirmar devolución' }).click();
  await expect.poll(async () => (await reservaApi(paginaDora, rd.id)).eleccion_estudio).toBe('devolucion');
  await captura(paginaDora, 'd-devolucion-elegida');
  const dev = (await reservaApi(paginaDora, rd.id)).devolucion;
  expect(dev).toMatchObject({ tipo: 'estudio', estado: 'aprobada', monto_aprobado: pagado });
  expect(dev.limite).toBeTruthy();

  await paginaAdmin.goto('/app/pagos/devoluciones/?estado=aprobada');
  const fila = paginaAdmin.getByRole('row').filter({ hasText: rd.folio });
  await expect(fila).toBeVisible();
  await captura(paginaAdmin, 'd-cola-con-plazo');
  await paginaAdmin.goto(`/app/pagos/devoluciones/revisar?id=${dev.id}`);
  await paginaAdmin.getByLabel(/Nota/).fill(`Yape ${marca} operación 654321`);
  await paginaAdmin.getByRole('button', { name: 'Marcar como realizada' }).click();
  await expect.poll(async () => (await llamar(paginaAdmin, 'GET', `/devoluciones/${dev.id}`)).cuerpo.estado).toBe('realizada');
});

test('e1. nivel 2: penalización y "Tratar como nivel 1" del Administrador lo pasa a crédito de excepción', async () => {
  const r = await reservar(paginaEva, JUEVES, '14:00', 60);
  await pagarYAprobar(paginaEva, r);
  PY('mover.py', r.folio, '30', '60'); // faltan entre 24 y 48 h
  await paginaEva.goto(`/app/reservas/detalle?id=${r.id}`);
  await paginaEva.getByRole('button', { name: 'Solicitar cancelación' }).click();
  const panel = paginaEva.getByRole('region', { name: new RegExp(`Cancelar reserva ${r.folio}`) });
  await expect(panel).toContainText('Nivel 2: avisas entre 24 y 48 h antes.');
  await expect(panel).toContainText('penalización');
  await captura(paginaEva, 'e1-nivel2');
  await panel.getByRole('button', { name: 'Confirmar cancelación' }).click();
  await expect(paginaEva.locator('[data-estado-reserva]')).toContainText('Cancelada');
  const cancelada = await reservaApi(paginaEva, r.id);
  expect(cancelada.cancelacion.nivel).toBe(2);
  expect(soles(cancelada.cancelacion.retenido)).toBeGreaterThan(0);
  expect((await creditos(paginaEva)).map((c) => c.tipo)).toEqual(['nivel_2']);

  await paginaAdmin.goto(`/app/reservas/detalle?id=${r.id}`);
  await paginaAdmin.getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
  const excepcion = paginaAdmin.getByRole('region', { name: new RegExp(`Tratar como nivel 1 · ${r.folio}`) });
  await excepcion.getByLabel(/Motivo/).fill('El cliente avisó por teléfono a tiempo.');
  await captura(paginaAdmin, 'e1-tratar-como-nivel-1');
  await excepcion.getByRole('button', { name: 'Tratar como nivel 1' }).click();
  await expect.poll(async () => (await creditos(paginaEva)).map((c) => c.tipo).sort()).toEqual(['excepcion', 'nivel_2']);
  const despues = await reservaApi(paginaEva, r.id);
  expect(despues.cancelacion.excepcion).toMatchObject({ motivo: 'El cliente avisó por teléfono a tiempo.' });
});

test('e2. nivel 3: se retiene todo y no hay crédito', async () => {
  const r = await reservar(paginaEva, JUEVES, '16:00', 60);
  await pagarYAprobar(paginaEva, r);
  PY('mover.py', r.folio, '10', '60'); // faltan 24 h o menos
  await paginaEva.goto(`/app/reservas/detalle?id=${r.id}`);
  await paginaEva.getByRole('button', { name: 'Solicitar cancelación' }).click();
  const panel = paginaEva.getByRole('region', { name: new RegExp(`Cancelar reserva ${r.folio}`) });
  await expect(panel).toContainText('Nivel 3: avisas con 24 h o menos.');
  await expect(panel).toContainText('Se retiene todo lo que pagaste y no hay crédito.');
  await captura(paginaEva, 'e2-nivel3');
  await panel.getByRole('button', { name: 'Confirmar cancelación' }).click();
  await expect(paginaEva.locator('[data-estado-reserva]')).toContainText('Cancelada');
  const c = (await reservaApi(paginaEva, r.id)).cancelacion;
  expect(c).toMatchObject({ nivel: 3, credito: '0.00' });
  expect(c.retenido).toBe(c.pagado);
  expect(await creditos(paginaEva)).toHaveLength(2); // los del caso anterior (nivel 2 y excepción): el nivel 3 no genera crédito
});

for (const [quien, pagina] of [['el Administrador', () => paginaAdmin], ['el personal', () => paginaPablo]]) {
  test(`e3. "No asistió" lo marca ${quien} tras la tolerancia y "Tratar como nivel 1" lo pasa a crédito`, async () => {
    const r = await reservar(paginaEva, MIERCOLES, quien === 'el personal' ? '14:00' : '16:00', 60);
    await pagarYAprobar(paginaEva, r);
    const pronto = await llamar(paginaAdmin, 'POST', `/reservas/${r.id}/inasistencia`);
    expect(pronto.estado).toBe(409); // antes de inicio + tolerancia
    expect(pronto.cuerpo.error?.codigo ?? pronto.cuerpo.codigo).toBe('tolerancia_no_cumplida');
    PY('mover.py', r.folio, '-0.5', '60'); // empezó hace 30 a 60 min: tolerancia cumplida, no terminó
    const p = pagina();
    await p.goto(`/app/reservas/detalle?id=${r.id}`);
    await p.getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
    const panel = p.getByRole('region', { name: new RegExp(`Marcar inasistencia · ${r.folio}`) });
    await captura(p, `e3-no-asistio-${quien === 'el personal' ? 'personal' : 'admin'}`);
    await panel.getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
    await expect.poll(async () => (await reservaApi(paginaEva, r.id)).estado).toBe('no_asistio');
    const cancelada = (await reservaApi(paginaEva, r.id)).cancelacion;
    expect(cancelada).toMatchObject({ por: 'inasistencia', credito: '0.00' });
    expect(cancelada.retenido).toBe(cancelada.pagado);
    await correoDe(eva.correo, `Marcamos tu inasistencia en la reserva ${r.folio}`);
    if (quien === 'el personal') {
      // El personal no decide el caso excepcional.
      await expect(p.getByRole('button', { name: 'Tratar como nivel 1', exact: true })).toHaveCount(0);
      expect((await llamar(p, 'POST', `/reservas/${r.id}/excepcion`, { motivo: 'Intento del personal sin permiso.' })).estado).toBe(403);
      return;
    }
    await p.goto(`/app/reservas/detalle?id=${r.id}`);
    await p.getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
    const excepcion = p.getByRole('region', { name: new RegExp(`Tratar como nivel 1 · ${r.folio}`) });
    await excepcion.getByLabel(/Motivo/).fill('Hubo un corte de luz en la zona.');
    await excepcion.getByRole('button', { name: 'Tratar como nivel 1' }).click();
    await expect.poll(async () => (await creditos(paginaEva)).filter((c) => c.tipo === 'excepcion').length).toBe(2);
    await captura(p, 'e3-inasistencia-excepcion');
    PY('mover.py', r.folio, '60', '60'); // la inasistencia no libera el tramo: se aparta para la siguiente prueba
  });
}
