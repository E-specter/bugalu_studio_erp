// Cambios sensibles de punta a punta (RF-20 CA-04..CA-09) contra Supabase, backend (8010) y Mailpit reales: sin page.route.
// Fechas desde ahora en Lima (la semana siguiente cae dentro de la ventana de reserva). `npm run test:e2e:real`.
// Cambia tarifa, IGV y adelanto por la UI y los restaura por la UI al terminar; el registro de cambios es inmutable (no se limpia, se cuenta relativo).
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const API = 'http://127.0.0.1:8010/api/v1';
const BACKEND = resolve(import.meta.dirname, '../../../backend');
const PY = (script, ...args) => execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, script), ...args], { cwd: BACKEND, encoding: 'utf8' }).trim();
const FOLIO = /R-\d{4}-\d+/;
const CAPTURAS = 'pruebas/capturas/real-rf20';

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `cam-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Cambios');
const cliente = persona('a', 'Cora Cambios');
const correos = [admin.correo, cliente.correo];

const lima = new Date(Date.now() - 5 * 3600_000);
const lunesSiguiente = new Date(Date.UTC(lima.getUTCFullYear(), lima.getUTCMonth(), lima.getUTCDate() + (8 - (lima.getUTCDay() || 7))));
const dia = (n) => new Date(lunesSiguiente.getTime() + n * 86400_000);
const ymd = (d) => d.toISOString().slice(0, 10);
const inicio = (d, hora) => `${ymd(d)}T${hora}:00-05:00`;
const fin = (d, hora, minutos) => new Date(new Date(inicio(d, hora)).getTime() + minutos * 60_000).toISOString();
const MARTES = dia(1);
const MIERCOLES = dia(2);

const soles = (n) => `S/ ${Number(n).toFixed(2).replace('.', ',')}`;
const pct = (n) => `${Number(n)} %`;
const centimos = (texto) => Math.round(Number(texto) * 100);

test.describe.configure({ mode: 'serial' });

let paginaAdmin, paginaA, idSala, idServicio, idA, idC, inicial, precioA, nRegistro0;

// Llamada a la API desde la pagina con el token de esa sesion (el de supabase-js en localStorage).
const llamar = (page, metodo, ruta, cuerpo) =>
  page.evaluate(async ({ url, metodo, cuerpo }) => {
    const token = JSON.parse(localStorage.getItem('bugalu-sesion')).access_token;
    const r = await fetch(url, { method: metodo, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    return { estado: r.status, cuerpo: await r.json().catch(() => null) };
  }, { url: API + ruta, metodo, cuerpo });
const publico = async (ruta, cuerpo) => (await fetch(`${API}${ruta}`, cuerpo ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(cuerpo) } : undefined)).json();
const simular = (d, hora, minutos) => publico('/simulaciones', { id_sala: idSala, id_servicio: idServicio, inicio: inicio(d, hora), fin: fin(d, hora, minutos), especialistas: [] });
const servicioActual = async () => (await publico('/servicios')).find((s) => s.id === idServicio);
const registro = async () => (await llamar(paginaAdmin, 'GET', '/registro-cambios')).cuerpo;

test.beforeAll(async ({ browser }) => {
  try {
    const [auth, mail, api] = await Promise.all([fetch(`${SUPABASE}/auth/v1/health`), fetch(`${MAILPIT}/api/v1/info`), fetch(`${API}/salas`)]);
    if (!auth.ok || !mail.ok || !api.ok) throw new Error(`Auth ${auth.status}, Mailpit ${mail.status}, API ${api.status}`);
  } catch (error) {
    const motivo = `Falta el stack local (Supabase ${SUPABASE}, Mailpit ${MAILPIT}, API ${API}): ${error.message}`;
    if (process.env.EXIGIR_INTEGRACION) throw new Error(motivo);
    test.skip(true, motivo);
  }
  const p = await browser.newPage();
  for (const ruta of ['/acceso', '/acceso/registro', '/acceso/interno', '/app/', '/app/franjas/', '/app/franjas/parametros', '/app/tarifas/', '/app/tarifas/servicio', '/app/tarifas/impuestos', '/app/cambios', '/reservar/servicio/', '/reservar/confirmar/', '/reservar/listo/', '/app/reservas/', '/app/reservas/detalle']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  // Red de seguridad: si algun paso fallo antes de restaurar, devuelve los valores por la API (vista previa + confirmar) y luego limpia.
  try {
    if (inicial && paginaAdmin) {
      const casos = [
        ['servicio', idServicio, { tarifa_hora: inicial.tarifa_hora }, async () => (await servicioActual()).tarifa_hora],
        ['impuestos', undefined, { porcentaje_igv: inicial.impuestos.porcentaje_igv, precios_incluyen_igv: inicial.impuestos.precios_incluyen_igv }, async () => (await publico('/impuestos')).porcentaje_igv],
        ['parametros', undefined, { porcentaje_adelanto: inicial.porcentaje_adelanto }, async () => (await llamar(paginaAdmin, 'GET', '/parametros')).cuerpo.porcentaje_adelanto],
      ];
      for (const [recurso, id_recurso, cambios] of casos) {
        const previa = await llamar(paginaAdmin, 'POST', '/cambios-sensibles/previsualizar', { recurso, id_recurso, cambios });
        if (previa.estado === 200) {
          const hecho = await llamar(paginaAdmin, 'POST', '/cambios-sensibles/confirmar', { token: previa.cuerpo.token, palabra: 'CONFIRMAR' });
          console.log(`Restauracion de seguridad (${recurso}): ${hecho.estado}`);
        }
      }
    }
  } finally {
    console.log(PY('limpiar.py', ...correos));
  }
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
const reservar = async (page, d, hora, duracion) => {
  await page.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(d, hora))}&duracion=${duracion}&sala=${idSala}&servicio=${idServicio}`);
  await page.getByRole('button', { name: 'Confirmar reserva' }).click();
  await page.waitForURL(/\/reservar\/listo\/\?id=/);
  const id = new URL(page.url()).searchParams.get('id');
  return { id, folio: (await page.getByText(FOLIO).first().textContent()).match(FOLIO)[0] };
};
const reservaDe = async (id) => (await llamar(paginaA, 'GET', `/reservas/${id}`)).cuerpo;
const aplicar = (page) => page.getByRole('button', { name: 'Aplicar cambio' });
const palabra = (page) => page.getByLabel('Escribe CONFIRMAR');
const dice = (page, texto) => expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
const confirmar = async (page) => {
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'true');
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
};
const pasoServicio = (d, hora, minutos) => `/reservar/servicio/?inicio=${encodeURIComponent(inicio(d, hora))}&duracion=${minutos}&sala=${idSala}&servicio=${idServicio}`;

test('1. el Administrador publica franjas, el cliente reserva y se anota el estado inicial', async ({ browser }) => {
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
  idSala = (await publico('/salas'))[0].id;
  idServicio = (await publico('/servicios')).find((s) => s.nombre === 'Grabación de voces').id;
  inicial = {
    tarifa_hora: (await servicioActual()).tarifa_hora,
    impuestos: await publico('/impuestos'),
    porcentaje_adelanto: (await llamar(paginaAdmin, 'GET', '/parametros')).cuerpo.porcentaje_adelanto,
  };
  nRegistro0 = (await registro()).length;
  paginaA = await registrar(browser, cliente);
  ({ id: idA } = await reservar(paginaA, MARTES, '10:00', 120));
  precioA = (await reservaDe(idA)).precio;
  expect(precioA.impuesto.incluido).toBe(inicial.impuestos.precios_incluyen_igv);
});

test('2. una tarifa cambia por la vista previa con CONFIRMAR: rige para una simulacion nueva y la reserva anterior conserva su precio', async () => {
  const antes = Number(inicial.tarifa_hora);
  const despues = antes + 10;
  await paginaAdmin.goto(`/app/tarifas/servicio?id=${idServicio}`);
  await paginaAdmin.getByLabel('Tarifa por hora (S/)').fill(String(despues));
  await paginaAdmin.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(paginaAdmin.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  const c1 = paginaAdmin.getByRole('table', { name: 'Qué cambia' });
  await expect(c1).toContainText('TARIFA POR HORA');
  await expect(c1).toContainText(soles(antes));
  await expect(c1).toContainText(soles(despues));
  await expect(paginaAdmin.getByRole('table', { name: 'Impacto' })).toContainText(/S\/ /);
  await expect(paginaAdmin.locator('.aviso').filter({ hasText: /reservas? vigentes? conservan? sus condiciones/ }).first()).toBeVisible();
  await captura(paginaAdmin, '1-revision-tarifa');
  await confirmar(paginaAdmin);
  await expect(paginaAdmin).toHaveURL(/\/app\/tarifas\/?(\?.*)?$/);
  expect(Number((await servicioActual()).tarifa_hora)).toBe(despues);
  const nueva = await simular(MARTES, '10:00', 120);
  expect(centimos(nueva.total) - centimos(precioA.total)).toBe(2 * 1000); // 2 h x 10,00
  const reservaA = await reservaDe(idA);
  expect(reservaA.precio.total).toBe(precioA.total);
  await paginaA.goto(`/app/reservas/detalle?id=${idA}`);
  await expect(paginaA.getByRole('heading', { level: 1 })).toHaveText(new RegExp(reservaA.folio, 'i'));
  await expect(paginaA.getByText(soles(precioA.total)).first()).toBeVisible();
  await captura(paginaA, '2-reserva-anterior-conserva-precio');
});

test('3. el IGV pasa a "no incluido" con otro porcentaje: la simulacion nueva muestra subtotal, mas IGV y total; la reserva existente conserva su desglose', async () => {
  const p0 = Number(inicial.impuestos.porcentaje_igv);
  const p1 = p0 + 2;
  await paginaAdmin.goto('/app/tarifas/impuestos');
  await expect(paginaAdmin.getByLabel('Porcentaje de IGV (%)')).toHaveValue(String(p0));
  await paginaAdmin.getByLabel('Porcentaje de IGV (%)').fill(String(p1));
  await paginaAdmin.getByRole('radio', { name: /^No/ }).check();
  await paginaAdmin.getByRole('button', { name: 'Revisar cambio' }).click();
  const c1 = paginaAdmin.getByRole('table', { name: 'Qué cambia' });
  await expect(c1).toContainText('PORCENTAJE DE IGV');
  await expect(c1).toContainText(pct(p0));
  await expect(c1).toContainText(pct(p1));
  await expect(c1).toContainText('LOS PRECIOS INCLUYEN IGV');
  await captura(paginaAdmin, '3-revision-impuestos');
  await confirmar(paginaAdmin);
  await dice(paginaAdmin, 'IGV actualizado. Rige para las simulaciones y reservas nuevas.');
  expect(await publico('/impuestos')).toEqual({ porcentaje_igv: p1.toFixed(2), precios_incluyen_igv: false });
  const nueva = await simular(MARTES, '10:00', 120);
  expect(nueva.impuesto).toMatchObject({ incluido: false, porcentaje: p1.toFixed(2) });
  expect(centimos(nueva.impuesto.base) + centimos(nueva.impuesto.monto)).toBe(centimos(nueva.total));
  expect(centimos(nueva.impuesto.monto)).toBe(Math.round((centimos(nueva.impuesto.base) * p1) / 100));
  // La pantalla de reservar: subtotal, mas IGV y total, en ese orden.
  await paginaA.goto(pasoServicio(MARTES, '10:00', 120));
  const resumen = paginaA.getByRole('region', { name: 'Tu reserva' });
  await expect(resumen).toContainText(`Más IGV (${pct(p1)})`);
  expect(await resumen.innerText()).toMatch(new RegExp(`Subtotal\\s*${soles(nueva.impuesto.base)}\\s*Más IGV \\(${pct(p1)}\\)\\s*${soles(nueva.impuesto.monto)}\\s*Total\\s*${soles(nueva.total)}`, 'i'));
  await captura(paginaA, '4-simulacion-igv-no-incluido');
  // La reserva existente no cambia.
  const reservaA = await reservaDe(idA);
  expect(reservaA.precio.impuesto).toEqual(precioA.impuesto);
  await paginaA.goto(`/app/reservas/detalle?id=${idA}`);
  await expect(paginaA.getByText(`Incluye IGV (${pct(inicial.impuestos.porcentaje_igv)})`).first()).toBeVisible();
  await captura(paginaA, '5-reserva-anterior-conserva-igv');
});

test('4. el porcentaje de adelanto cambia por el flujo y una reserva nueva usa el adelanto nuevo', async () => {
  const a0 = inicial.porcentaje_adelanto;
  const a1 = a0 === 30 ? 40 : 30;
  await paginaAdmin.goto('/app/franjas/parametros');
  await paginaAdmin.getByLabel('Adelanto para confirmar (%)').fill(String(a1));
  await paginaAdmin.getByRole('button', { name: 'Guardar parámetros' }).click();
  const c1 = paginaAdmin.getByRole('table', { name: 'Qué cambia' });
  await expect(c1).toContainText('ADELANTO PARA CONFIRMAR');
  await expect(c1).toContainText(pct(a0));
  await expect(c1).toContainText(pct(a1));
  await captura(paginaAdmin, '6-revision-parametros');
  await confirmar(paginaAdmin);
  await dice(paginaAdmin, 'Parámetros guardados');
  const c = await reservar(paginaA, MIERCOLES, '10:00', 60);
  idC = c.id;
  const reservaC = await reservaDe(idC);
  expect(Number(reservaC.precio.porcentaje_adelanto)).toBe(a1);
  expect(centimos(reservaC.precio.anticipo)).toBe(Math.round((centimos(reservaC.precio.total) * a1) / 100));
  expect(reservaC.precio.impuesto.incluido).toBe(false); // la reserva nueva guarda el IGV vigente al crearse (parametros_aplicados no se expone en la API)
  await paginaA.goto(`/app/reservas/detalle?id=${idC}`);
  await expect(paginaA.getByText(`Anticipo ${a1} %`).first()).toBeVisible();
  await captura(paginaA, '7-reserva-nueva-adelanto');
  // La reserva anterior sigue con su adelanto.
  const reservaA = await reservaDe(idA);
  expect(Number(reservaA.precio.porcentaje_adelanto)).toBe(a0);
  expect(reservaA.precio.anticipo).toBe(precioA.anticipo);
});

test('5. el registro de cambios muestra cada cambio con autor, antes y despues', async () => {
  const lista = await registro();
  expect(lista.length - nRegistro0).toBe(4); // tarifa, porcentaje de IGV, "incluye IGV" y adelanto
  expect(lista.slice(0, 4).every((c) => c.autor.nombre === admin.nombre)).toBe(true);
  await paginaAdmin.goto('/app/cambios');
  const tabla = paginaAdmin.getByRole('table', { name: /^Cambios del / });
  const fila = (campo) => tabla.getByRole('row').filter({ hasText: admin.nombre }).filter({ hasText: campo }).first();
  const p0 = inicial.impuestos.porcentaje_igv;
  const a0 = inicial.porcentaje_adelanto;
  await expect(fila('TARIFA POR HORA')).toContainText(soles(inicial.tarifa_hora));
  await expect(fila('TARIFA POR HORA')).toContainText(soles(Number(inicial.tarifa_hora) + 10));
  await expect(fila('TARIFA POR HORA')).toContainText('Grabación de voces');
  await expect(fila('PORCENTAJE DE IGV')).toContainText(pct(p0));
  await expect(fila('PORCENTAJE DE IGV')).toContainText(pct(Number(p0) + 2));
  await expect(fila('LOS PRECIOS INCLUYEN IGV')).toContainText('Sí');
  await expect(fila('LOS PRECIOS INCLUYEN IGV')).toContainText('No');
  await expect(fila('ADELANTO PARA CONFIRMAR')).toContainText(pct(a0));
  await captura(paginaAdmin, '8-registro-cambios');
});

test('6. un PATCH directo con un campo sensible responde 428 y no cambia nada', async () => {
  const servicio = await servicioActual();
  const r = await llamar(paginaAdmin, 'PATCH', `/servicios/${idServicio}`, { tarifa_hora: '999.00' });
  expect(r.estado).toBe(428);
  expect(r.cuerpo.error.codigo).toBe('confirmacion_requerida');
  expect(r.cuerpo.error.detalles.campos).toContain('tarifa_hora');
  const p = await llamar(paginaAdmin, 'PATCH', '/parametros', { porcentaje_adelanto: 77 });
  expect(p.estado).toBe(428);
  expect(p.cuerpo.error.detalles.campos).toContain('porcentaje_adelanto');
  const i = await llamar(paginaAdmin, 'PATCH', '/parametros', { porcentaje_adelanto: 77, anticipacion_minima_horas: 3 });
  expect(i.estado).toBe(428); // un campo no sensible no se aplica si viene con uno sensible
  expect((await servicioActual()).tarifa_hora).toBe(servicio.tarifa_hora);
  expect((await llamar(paginaAdmin, 'GET', '/parametros')).cuerpo).toMatchObject({ porcentaje_adelanto: expect.any(Number) });
  expect((await llamar(paginaAdmin, 'GET', '/parametros')).cuerpo.porcentaje_adelanto).not.toBe(77);
  // El mismo valor de un campo sensible sigue en un paso.
  const igual = await llamar(paginaAdmin, 'PATCH', `/servicios/${idServicio}`, { tarifa_hora: servicio.tarifa_hora });
  expect(igual.estado).toBe(200);
});

test('7. se restauran los valores iniciales por el flujo y el registro suma otros cuatro cambios', async () => {
  const p0 = Number(inicial.impuestos.porcentaje_igv);
  await paginaAdmin.goto(`/app/tarifas/servicio?id=${idServicio}`);
  await paginaAdmin.getByLabel('Tarifa por hora (S/)').fill(String(Number(inicial.tarifa_hora)));
  await paginaAdmin.getByRole('button', { name: 'Guardar servicio' }).click();
  await confirmar(paginaAdmin);
  await expect(paginaAdmin).toHaveURL(/\/app\/tarifas\/?(\?.*)?$/);
  await paginaAdmin.goto('/app/tarifas/impuestos');
  await paginaAdmin.getByLabel('Porcentaje de IGV (%)').fill(String(p0));
  await paginaAdmin.getByRole('radio', { name: inicial.impuestos.precios_incluyen_igv ? /^Sí/ : /^No/ }).check();
  await paginaAdmin.getByRole('button', { name: 'Revisar cambio' }).click();
  await confirmar(paginaAdmin);
  await dice(paginaAdmin, 'IGV actualizado. Rige para las simulaciones y reservas nuevas.');
  await paginaAdmin.goto('/app/franjas/parametros');
  await paginaAdmin.getByLabel('Adelanto para confirmar (%)').fill(String(inicial.porcentaje_adelanto));
  await paginaAdmin.getByRole('button', { name: 'Guardar parámetros' }).click();
  await confirmar(paginaAdmin);
  await dice(paginaAdmin, 'Parámetros guardados');
  expect((await servicioActual()).tarifa_hora).toBe(inicial.tarifa_hora);
  expect(await publico('/impuestos')).toEqual(inicial.impuestos);
  expect((await llamar(paginaAdmin, 'GET', '/parametros')).cuerpo.porcentaje_adelanto).toBe(inicial.porcentaje_adelanto);
  expect((await simular(MARTES, '10:00', 120)).total).toBe(precioA.total);
  expect((await registro()).length - nRegistro0).toBe(8);
  await paginaAdmin.goto('/app/cambios');
  await expect(paginaAdmin.getByRole('table', { name: /^Cambios del / }).getByRole('row').filter({ hasText: 'ADELANTO PARA CONFIRMAR' }).first()).toContainText(pct(inicial.porcentaje_adelanto));
  await captura(paginaAdmin, '9-registro-tras-restaurar');
});
