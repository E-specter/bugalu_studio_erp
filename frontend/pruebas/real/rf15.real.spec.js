// RF-15 etapa A (profesionales, especialidades, precios, horarios y directorio publico) de punta a punta contra Supabase, Storage,
// backend (8010) y Mailpit reales: sin page.route. `npm run test:e2e:real`.
// Sin estado compartido: crea 4 cuentas, 2 especialidades (con el prefijo de la corrida), un perfil, una foto, horarios y una pre-reserva,
// y al final `limpiar.py` los borra (el registro de cambios del recurso `profesional` incluido) y la foto sale de Storage.
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';
import { API, BACKEND, cargarTextos, llamar, prepararCliente, confirmarReserva, dia, ymd, inicio, vaciarBucket } from './ayudas.js';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const CAPTURAS = 'pruebas/capturas/real-rf15';
const PY = (script, ...args) => execFileSync('uv', ['run', 'python', resolve(import.meta.dirname, script), ...args], { cwd: BACKEND, encoding: 'utf8' }).trim();

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const persona = (rol, nombre) => ({ nombre, telefono: '987654321', artistico: nombre, correo: `rf15-${marca}-${rol}@prueba.bugalu.pe` });
const admin = persona('admin', 'Aldo Asesorias');
const prof = persona('prof', 'Paula Profesional');
const cliente = persona('cliente', 'Clara Cliente');
const correos = [admin.correo, prof.correo, cliente.correo];
const ESP = `Prueba RF15 ${marca}`;
const ESP_OTRA = `Prueba RF15 otra ${marca}`;
const ARTISTICO = `Paula Beat ${marca}`;
const PRESENTACION = `Productora y asesora de voces (${marca}).`;
const PNG = { name: 'retrato.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64') };

// Semana ISO (AAAA-Www) de una fecha UTC.
const semanaDe = (fecha) => {
  const d = new Date(Date.UTC(fecha.getUTCFullYear(), fecha.getUTCMonth(), fecha.getUTCDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const anio = d.getUTCFullYear();
  return `${anio}-W${String(Math.ceil(((d - Date.UTC(anio, 0, 1)) / 86400_000 + 1) / 7)).padStart(2, '0')}`;
};
const SEMANA1 = semanaDe(dia(0));
const SEMANA2 = semanaDe(dia(7));
const MARTES = dia(1);
const MIERCOLES = dia(2);
const MARTES2 = dia(8);

test.describe.configure({ mode: 'serial' });

let paginaAdmin, paginaProf, paginaCliente, idProf, idCliente, idSala, idServicio, horarioMiercoles;

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
  for (const ruta of ['/', '/acceso/registro', '/acceso/interno', '/acceso/textos', '/app/', '/app/usuarios', '/app/usuarios/editar', '/app/franjas/', '/reservar/confirmar/', '/reservar/listo/',
    '/app/asesorias/', '/app/asesorias/especialidades', '/app/asesorias/profesional', '/app/asesorias/horarios', '/app/ficha/', '/app/horarios/', '/asesorias/', '/asesorias/profesional/']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(async () => {
  try {
    const ids = JSON.parse(PY('capturas.py', ...correos));
    console.log(`Storage: ${await vaciarBucket('profesionales', ids)} objetos borrados de profesionales/, sin huerfanos.`);
  } finally {
    console.log(PY('limpiar.py', `--especialidades=Prueba RF15 `, ...correos).trim());
  }
});

const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png`, fullPage: true });
const registrarCuenta = async (browser, p) => {
  const page = await nuevaPagina(browser);
  await page.goto('/acceso/registro');
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await page.waitForURL('**/acceso/textos*');
  return page;
};
const entrarInterno = async (page, p) => {
  await page.evaluate(() => localStorage.clear());
  await page.goto('/acceso/interno');
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: 'Entrar a la sala' }).click();
  await page.waitForURL('**/app/');
};
const publico = async (ruta) => (await fetch(`${API}${ruta}`)).json();
const idDe = async (correo) => (await llamar(paginaAdmin, 'GET', '/usuarios')).cuerpo.find((u) => u.correo === correo).id;
const aviso = (page, texto) => expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();

test('1. el Administrador crea especialidades, asigna el rol, fija precios con CONFIRMAR y activa el perfil (aun sin publicar)', async ({ browser }) => {
  paginaAdmin = await registrarCuenta(browser, admin);
  execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.crear_administrador', admin.correo], { cwd: BACKEND });
  await entrarInterno(paginaAdmin, admin);
  paginaProf = await registrarCuenta(browser, prof);
  paginaCliente = await registrarCuenta(browser, cliente);
  await prepararCliente(paginaCliente);
  idProf = await idDe(prof.correo);
  idCliente = await idDe(cliente.correo);

  // Especialidades por la UI: crear, rechazar el duplicado (sin tildes ni mayusculas) y crear otra.
  await paginaAdmin.goto('/app/asesorias/especialidades');
  for (const nombre of [ESP, ESP.toLowerCase(), ESP_OTRA]) {
    await paginaAdmin.getByLabel('Nombre', { exact: true }).fill(nombre);
    await paginaAdmin.getByRole('button', { name: 'Crear especialidad' }).click();
    if (nombre === ESP.toLowerCase()) await expect(paginaAdmin.getByText('Ya existe una especialidad con ese nombre (sin contar mayúsculas ni tildes).').first()).toBeVisible();
    else await aviso(paginaAdmin, 'Especialidad creada.');
  }
  await expect(paginaAdmin.getByRole('table').getByRole('row').filter({ hasText: ESP_OTRA })).toContainText('ACTIVA');
  await captura(paginaAdmin, '1-especialidades');

  // Rol por la UI: la cuenta pasa a Profesional y el perfil nace solo, inactivo.
  await paginaAdmin.goto(`/app/usuarios/editar?id=${idProf}`);
  await paginaAdmin.getByLabel('Profesional artístico').check();
  await paginaAdmin.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await paginaAdmin.waitForURL(/\/app\/asesorias\/\?aviso=profesional-asignado/);
  await aviso(paginaAdmin, 'Rol asignado. Completa su ficha y fija sus precios para publicarlo.');
  const fila = paginaAdmin.getByRole('table', { name: 'Profesionales' }).getByRole('row').filter({ hasText: prof.nombre });
  await expect(fila).toContainText('INACTIVO');
  await captura(paginaAdmin, '1-lista-profesionales');
  const nuevo = await llamar(paginaAdmin, 'GET', `/profesionales/${idProf}`);
  expect(nuevo.estado).toBe(200);
  expect(nuevo.cuerpo).toMatchObject({ id: idProf, activo: false, publicado: false, especialidades: [], duraciones: [] });

  // Precios de 30 y 60 min con la vista previa y CONFIRMAR de RF-20; activar el perfil.
  await paginaAdmin.goto(`/app/asesorias/profesional?id=${idProf}`);
  await expect(paginaAdmin.getByRole('heading', { level: 1 })).toHaveText(new RegExp(`ficha de ${prof.nombre}`, 'i'));
  await paginaAdmin.getByLabel('Activo').check();
  await paginaAdmin.getByLabel('Precio 30 min (S/)').fill('80');
  await paginaAdmin.getByLabel('Precio 1 h (S/)').fill('140');
  await paginaAdmin.getByRole('button', { name: 'Guardar ficha' }).click();
  await expect(paginaAdmin.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  const cambia = paginaAdmin.getByRole('table', { name: 'Qué cambia' });
  await expect(cambia).toContainText('PRECIO 30 MIN');
  await expect(cambia).toContainText('S/ 140,00');
  await expect(paginaAdmin.getByRole('button', { name: 'Aplicar cambio' })).toHaveAttribute('aria-disabled', 'true');
  await captura(paginaAdmin, '1-revision-precios');
  await paginaAdmin.getByLabel('Escribe CONFIRMAR').fill('CONFIRMAR');
  await paginaAdmin.getByRole('button', { name: 'Aplicar cambio' }).click();
  await aviso(paginaAdmin, `Ficha de ${prof.nombre} guardada.`);
  await expect(paginaAdmin.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=profesional');
  const ficha = (await llamar(paginaAdmin, 'GET', `/profesionales/${idProf}`)).cuerpo;
  expect(ficha).toMatchObject({ activo: true, publicado: false }); // falta la especialidad: la elige el profesional
  expect(ficha.duraciones.map((d) => [d.minutos, d.precio])).toEqual([[30, '80.00'], [60, '140.00']]);
  expect(ficha.duraciones[0].igv).toMatchObject({ incluido: true });
  // Un PATCH directo con precios sin confirmar responde 428 y no cambia nada.
  const directo = await llamar(paginaAdmin, 'PATCH', `/profesionales/${idProf}`, { precios: { 30: 999 } });
  expect(directo.estado).toBe(428);
  expect(directo.cuerpo.error.codigo).toBe('confirmacion_requerida');
  // El registro de cambios del recurso `profesional` anota los dos precios.
  const registro = (await llamar(paginaAdmin, 'GET', '/registro-cambios?recurso=profesional')).cuerpo.filter((c) => c.id_recurso === idProf);
  expect(registro.map((c) => c.campo).sort()).toEqual(['precio_30', 'precio_60']);
  await paginaAdmin.goto('/app/cambios?recurso=profesional');
  await expect(paginaAdmin.getByRole('table', { name: /^Cambios del / }).getByRole('row').filter({ hasText: prof.nombre }).first()).toContainText(/PRECIO/);
  await captura(paginaAdmin, '1-registro-cambios');
});

test('2. el profesional entra con correo y contrasena, edita su ficha, sube su foto y queda publicado', async () => {
  await entrarInterno(paginaProf, prof);
  expect((await llamar(paginaProf, 'GET', '/perfil')).cuerpo.rol).toBe('profesional');
  await paginaProf.goto('/app/ficha/');
  await expect(paginaProf.getByRole('heading', { level: 1 })).toHaveText(/ficha pública/i);
  await aviso(paginaProf, 'Falta: elegir al menos una especialidad.');
  await expect(paginaProf.getByLabel('Precio 30 min (S/)')).toHaveCount(0); // los precios no son suyos
  await captura(paginaProf, '2-ficha-sin-publicar');
  await paginaProf.getByLabel('Nombre artístico').fill(ARTISTICO);
  await paginaProf.getByLabel('Presentación', { exact: true }).fill(PRESENTACION);
  await paginaProf.getByLabel(ESP, { exact: true }).check();
  await paginaProf.getByRole('button', { name: 'Añadir red' }).click();
  await paginaProf.getByRole('group', { name: 'Red 1' }).getByLabel('Usuario o enlace').fill('@paulabeat');
  await paginaProf.getByRole('button', { name: 'Guardar ficha' }).click();
  await aviso(paginaProf, 'Ficha guardada. Ya está en el directorio.');
  await expect(paginaProf.getByRole('link', { name: 'Ver mi perfil público' })).toBeVisible();

  // Foto real: JPG, PNG o WebP validado por su contenido; el bucket `profesionales` la sirve sin sesion.
  await paginaProf.locator('input[type=file]').setInputFiles(PNG);
  await paginaProf.getByRole('button', { name: 'Subir foto' }).click();
  await aviso(paginaProf, 'Foto actualizada.');
  await expect(paginaProf.getByRole('button', { name: 'Quitar foto' })).toBeVisible();
  await captura(paginaProf, '2-ficha-publicada');
  const yo = (await llamar(paginaProf, 'GET', `/profesionales/${idProf}`)).cuerpo;
  expect(yo).toMatchObject({ nombre_artistico: ARTISTICO, presentacion: PRESENTACION, activo: true, publicado: true, redes: [{ red: 'instagram', valor: '@paulabeat' }] });
  expect(yo.especialidades.map((e) => e.nombre)).toEqual([ESP]);
  expect(yo.foto_url).toContain('/storage/v1/object/public/profesionales/');
  const imagen = await fetch(yo.foto_url);
  expect(imagen.status).toBe(200);
  expect(imagen.headers.get('content-type')).toBe('image/png');
  // El profesional no cambia lo que no es suyo: activo y precios, por la API, son 403.
  expect((await llamar(paginaProf, 'PATCH', `/profesionales/${idProf}`, { activo: false })).estado).toBe(403);
  expect((await llamar(paginaProf, 'PATCH', `/profesionales/${idProf}`, { precios: { 30: 1 } })).estado).toBe(403);
});

test('3. el profesional publica la semana siguiente, copia la sugerencia a la otra y retira un bloque', async () => {
  const bloque = async (grupo, desde, hasta) => {
    if (!(await grupo.getByLabel('Desde').count())) await grupo.getByRole('button', { name: /^Añadir bloque al/ }).click();
    await grupo.getByLabel('Desde').first().fill(desde);
    await grupo.getByLabel('Hasta').first().fill(hasta);
  };
  const dia1 = (nombre) => paginaProf.getByRole('group', { name: new RegExp(`^${nombre.toUpperCase()} `) });
  await paginaProf.goto(`/app/horarios/?semana=${SEMANA1}`);
  await expect(paginaProf.getByRole('heading', { level: 1 })).toHaveText(/mis horarios/i);
  await expect(paginaProf.getByText('No hay horarios publicados esta semana')).toBeVisible();
  await bloque(dia1('martes'), '10:00', '12:00');
  await bloque(dia1('miércoles'), '10:00', '13:00');
  await paginaProf.getByRole('button', { name: 'Publicar horarios' }).click();
  await aviso(paginaProf, 'Horarios publicados.');
  const tabla = paginaProf.getByRole('table', { name: 'Horarios publicados' });
  await expect(tabla.getByRole('row')).toHaveCount(3);
  await expect(tabla).toContainText('10:00–12:00');
  await expect(tabla).toContainText('10:00–13:00');
  await captura(paginaProf, '3-semana-publicada');

  // Semana siguiente: la sugerencia copia la ultima publicada y se publica tal cual.
  await paginaProf.getByRole('link', { name: 'Semana siguiente' }).click();
  await expect(paginaProf).toHaveURL(new RegExp(`semana=${SEMANA2}`));
  await aviso(paginaProf, 'Te proponemos tu última semana publicada. Cambia lo que haga falta antes de publicar.');
  await expect(dia1('martes').getByLabel('Desde')).toHaveValue('10:00');
  await expect(dia1('martes').getByLabel('Hasta')).toHaveValue('12:00');
  await expect(dia1('miércoles').getByLabel('Hasta')).toHaveValue('13:00');
  await captura(paginaProf, '3-sugerencia');
  await paginaProf.getByRole('button', { name: 'Publicar horarios' }).click();
  await aviso(paginaProf, 'Horarios publicados.');
  const semana2 = async (id = idProf) => (await llamar(paginaProf, 'GET', `/profesionales/${id}/disponibilidad?desde=${encodeURIComponent(`${ymd(dia(7))}T00:00:00-05:00`)}&hasta=${encodeURIComponent(`${ymd(dia(14))}T00:00:00-05:00`)}`)).cuerpo;
  expect((await semana2()).horarios).toHaveLength(2);

  // Un bloque que se solapa con otro publicado: 409 sin tocar lo publicado.
  const solapado = await llamar(paginaProf, 'POST', `/profesionales/${idProf}/horarios`, { horarios: [{ inicio: inicio(MARTES, '11:00'), fin: inicio(MARTES, '12:30') }] });
  expect(solapado.estado).toBe(409);
  expect(solapado.cuerpo.error.codigo).toBe('horario_solapado');

  // Retirar el bloque del miercoles de la primera semana.
  await paginaProf.goto(`/app/horarios/?semana=${SEMANA1}`);
  const miercoles = tabla.getByRole('row').filter({ hasText: '10:00–13:00' });
  horarioMiercoles = (await llamar(paginaProf, 'GET', `/profesionales/${idProf}/disponibilidad?desde=${encodeURIComponent(`${ymd(dia(0))}T00:00:00-05:00`)}&hasta=${encodeURIComponent(`${ymd(dia(7))}T00:00:00-05:00`)}`)).cuerpo.horarios.find((h) => Date.parse(h.inicio) === Date.parse(inicio(MIERCOLES, "10:00"))).id;
  await miercoles.getByRole('button', { name: /Retirar bloque del miércoles/ }).click();
  await aviso(paginaProf, 'Bloque retirado.');
  await expect(tabla.getByRole('row')).toHaveCount(2);
  await expect(tabla).not.toContainText('10:00–13:00');
  await captura(paginaProf, '3-bloque-retirado');
  expect((await llamar(paginaProf, 'DELETE', `/profesionales/${idProf}/horarios/${horarioMiercoles}`)).estado).toBe(404); // ya retirado
});

test('4. el visitante ve el directorio filtrado por especialidad y el perfil con precios, IGV y disponibilidad', async ({ browser }) => {
  const page = await nuevaPagina(browser); // sin sesion
  await page.goto('/asesorias/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('PROFESIONALES DEL ESTUDIO');
  const tarjeta = page.locator('.dir-item').filter({ hasText: ARTISTICO });
  await expect(tarjeta).toHaveCount(1);
  await expect(tarjeta).toContainText(prof.nombre);
  await expect(tarjeta).toContainText('S/ 80,00');
  await expect(page.getByRole('main')).toContainText(/Precios en soles con IGV incluido \(\d+ %\)\./);

  await page.getByRole('navigation', { name: 'Filtrar por especialidad' }).getByRole('link', { name: ESP, exact: true }).click();
  await expect(page).toHaveURL(/\?especialidad=/);
  await expect(page.locator('.dir-item')).toHaveCount(1);
  await expect(page.locator('.dir-item')).toContainText(ARTISTICO);
  await captura(page, '4-directorio-filtrado');
  await page.getByRole('navigation', { name: 'Filtrar por especialidad' }).getByRole('link', { name: ESP_OTRA, exact: true }).click();
  await expect(page.getByText(`Nadie ofrece ${ESP_OTRA} por ahora.`).first()).toBeVisible();
  await expect(page.locator('.dir-item')).toHaveCount(0);

  const filtrado = await publico(`/profesionales?especialidad=${(await publico('/especialidades-asesoria')).find((e) => e.nombre === ESP).id}`);
  expect(filtrado.map((p) => p.id)).toEqual([idProf]);
  expect(filtrado[0]).not.toHaveProperty('activo'); // el visitante no ve el estado interno
  expect((await publico('/especialidades-asesoria')).every((e) => e.activa)).toBe(true);

  // Perfil publico de la semana siguiente: identidad, precios con su IGV y los bloques publicados.
  await page.goto(`/asesorias/profesional/?id=${idProf}&fecha=${ymd(MARTES)}`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(ARTISTICO);
  await expect(page.locator('.dir-presentacion')).toHaveText(PRESENTACION);
  await expect(page.getByRole('list', { name: 'Redes' })).toContainText('@paulabeat');
  const precios = page.getByRole('table', { name: `Precio de una asesoría con ${ARTISTICO}` });
  await expect(precios).toContainText('S/ 80,00');
  await expect(precios).toContainText('S/ 140,00');
  await expect(precios.getByRole('columnheader', { name: /INCLUYE IGV \(\d+ %\)/ })).toBeAttached();
  await expect(page.getByText('Horario de Lima')).toBeVisible();
  await expect(page.getByRole('cell', { name: /10:00, libre/i }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toHaveAttribute('aria-disabled', 'true'); // la agenda es de la etapa B
  await expect(page.locator('[aria-busy]')).toHaveCount(0);
  await captura(page, '4-perfil-publico');
  const foto = page.locator('img[src*="/storage/v1/object/public/profesionales/"]').first();
  await expect(foto).toBeAttached();
  const disp = await publico(`/profesionales/${idProf}/disponibilidad?desde=${encodeURIComponent(`${ymd(dia(0))}T00:00:00-05:00`)}&hasta=${encodeURIComponent(`${ymd(dia(7))}T00:00:00-05:00`)}`);
  expect(disp.horarios).toHaveLength(1); // el del miercoles se retiro
  expect(disp.dias.find((d) => d.fecha === ymd(MARTES)).minutos_libres).toBe(120);
  expect(disp.ocupados).toEqual([]);
  expect(disp.duraciones.map((d) => d.minutos)).toEqual([30, 60]);
  expect(disp).not.toHaveProperty('cliente');
  // Ver el perfil de otra semana no pide sesion y muestra la semana con bloques (la segunda copia).
  await page.goto(`/asesorias/profesional/?id=${idProf}&fecha=${ymd(MARTES2)}`);
  await expect(page.getByRole('cell', { name: /10:00, libre/i }).first()).toBeVisible();
  await page.context().close();
});

test('5. el profesional no reserva la sala (403) y un cliente con una pre-reserva viva no pasa a profesional (409)', async () => {
  // Una pre-reserva viva de sala necesita franjas: las publica el Administrador por la UI.
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

  // Profesional: la agenda y las reservas de sala no son suyas.
  const condiciones = (await publico('/textos-legales')).find((t) => t.tipo === 'condiciones' && !t.programada);
  const cuerpo = { id_sala: idSala, id_servicio: idServicio, inicio: inicio(MARTES2, '15:00'), fin: inicio(MARTES2, '16:00'), especialistas: [], version_condiciones: condiciones?.version };
  const reservo = await llamar(paginaProf, 'POST', '/reservas', cuerpo);
  expect(reservo.estado, JSON.stringify(reservo.cuerpo)).toBe(403);
  expect((await llamar(paginaProf, 'GET', `/reservas?desde=${encodeURIComponent(inicio(MARTES, '00:00'))}&hasta=${encodeURIComponent(inicio(MIERCOLES, '00:00'))}`)).estado).toBe(403);
  expect((await llamar(paginaProf, 'GET', '/usuarios')).estado).toBe(403);
  expect((await llamar(paginaProf, 'GET', '/reservas/mias')).estado).toBe(403);

  // Cliente con una pre-reserva viva.
  await paginaCliente.goto(`/reservar/confirmar/?inicio=${encodeURIComponent(inicio(MARTES, '10:00'))}&duracion=120&sala=${idSala}&servicio=${idServicio}`);
  await confirmarReserva(paginaCliente);
  await paginaCliente.waitForURL(/\/reservar\/listo\/\?id=/);
  const viva = (await llamar(paginaCliente, 'GET', '/reservas/mias')).cuerpo;
  expect(viva.map((r) => r.estado)).toEqual(['pre_reservada']);

  // Por la API: 409 cliente_con_operaciones y el rol no cambia.
  const api = await llamar(paginaAdmin, 'PATCH', `/usuarios/${idCliente}`, { rol: 'profesional' });
  expect(api.estado).toBe(409);
  expect(api.cuerpo.error.codigo).toBe('cliente_con_operaciones');
  expect((await llamar(paginaAdmin, 'GET', '/usuarios')).cuerpo.find((u) => u.id === idCliente).rol).toBe('cliente');
  expect((await llamar(paginaAdmin, 'GET', `/profesionales/${idCliente}`)).estado).toBe(404); // no nacio perfil

  // Por la UI: el aviso dice que pasó y cómo corregirlo, y el formulario se conserva.
  await paginaAdmin.goto(`/app/usuarios/editar?id=${idCliente}`);
  await paginaAdmin.getByLabel('Profesional artístico').check();
  await paginaAdmin.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await aviso(paginaAdmin, `${cliente.nombre} tiene reservas, créditos, pagos o devoluciones vivos`);
  await expect(paginaAdmin.getByLabel('Profesional artístico')).toBeChecked();
  await captura(paginaAdmin, '5-cliente-con-operaciones');
});

test('6. al quitar el rol, el perfil sale del directorio y de la vista publica', async ({ browser }) => {
  await paginaAdmin.goto(`/app/usuarios/editar?id=${idProf}`);
  await paginaAdmin.getByLabel('Personal del estudio').check();
  await paginaAdmin.getByRole('textbox', { name: 'Especialidad' }).fill('Mezcla');
  await paginaAdmin.getByRole('button', { name: 'Guardar rol y especialidad' }).click();
  await paginaAdmin.waitForURL(/\/app\/usuarios\?aviso=usuario-actualizado/);
  expect((await llamar(paginaAdmin, 'GET', '/usuarios')).cuerpo.find((u) => u.id === idProf).rol).toBe('personal');
  expect((await publico('/profesionales')).map((p) => p.id)).not.toContain(idProf);
  expect((await fetch(`${API}/profesionales/${idProf}`)).status).toBe(404);
  expect((await fetch(`${API}/profesionales/${idProf}/disponibilidad?desde=${encodeURIComponent(`${ymd(dia(0))}T00:00:00-05:00`)}&hasta=${encodeURIComponent(`${ymd(dia(7))}T00:00:00-05:00`)}`)).status).toBe(404);

  const page = await nuevaPagina(browser);
  await page.goto('/asesorias/');
  await expect(page.locator('.dir-item').filter({ hasText: ARTISTICO })).toHaveCount(0);
  expect((await publico('/especialidades-asesoria')).map((e) => e.nombre)).toContain(ESP); // la especialidad sigue en el catalogo
  await captura(page, '6-directorio-sin-profesional');
  await page.goto(`/asesorias/profesional/?id=${idProf}`);
  await expect(page.locator('.aviso-titulo').filter({ hasText: 'Este perfil no existe o ya no está publicado.' })).toBeVisible();
  await captura(page, '6-perfil-no-disponible');
  await page.context().close();
});
