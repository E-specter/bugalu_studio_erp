// RF-15 etapa B (CA-06, CA-07, CA-17): agendar una asesoria por pasos. La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { PID, AID, PROF, INICIO, asesoria, montarAgendar } from './ayudas-rf15b.js';

const URL1 = `/asesorias/agendar/?profesional=${PID}`;
const URL2 = `/asesorias/agendar/horario/?profesional=${PID}&duracion=60&modalidad=virtual&fecha=2026-11-17`;
const URL4 = `/asesorias/agendar/confirmar/?profesional=${PID}&duracion=60&modalidad=virtual&inicio=${encodeURIComponent(INICIO)}`;
const aviso = (page) => page.locator('bugalu-agendar [data-avisos] .aviso');
const agendar = async (page) => {
  await page.getByRole('checkbox', { name: /Acepto las Condiciones de contratación/ }).check();
  await page.getByRole('button', { name: 'Agendar asesoría' }).click();
};

// ---------- 01 Asesoria ----------
for (const t of tamanos) {
  test(`agendar 01: duraciones con precio e IGV, modalidad y resumen a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await montarAgendar(page);
    await page.goto(URL1);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Elige tu asesoría');
    await expect(page).toHaveTitle('Elige tu asesoría · Paso 1 de 5 · Agendar asesoría · Bugalú Studio');
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    await expect(page.locator('.agd-nombre')).toHaveText('Ana Beat');
    await expect(page.getByText('Producción, Coros')).toBeVisible();
    await expect(page.getByRole('radio', { name: /30 min.*S\/ 80,00 · Incluye IGV \(18 %\): S\/ 12,20/ })).toBeVisible();
    await expect(page.getByRole('radio', { name: /1 h/ })).toBeVisible();
    await expect(page.getByRole('group', { name: 'Modalidad' })).toContainText('Por videollamada de Google Meet.');
    await expect(page.getByRole('navigation', { name: 'Progreso de la asesoría' })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-agendar-01-${t.nombre}.png`, fullPage: true });
  });
}

test('agendar 01: sin elegir muestra los errores de grupo y al elegir sigue al horario con la URL', async ({ page }) => {
  await montarAgendar(page);
  await page.goto(URL1);
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page.getByText('Elige cuánto dura tu asesoría.')).toBeVisible();
  await expect(page.getByText('Elige si es presencial o por videollamada.')).toBeVisible();
  await expect(aviso(page)).toContainText('Revisa 2 campos');
  await page.getByRole('radio', { name: /1 h/ }).check();
  await page.getByRole('radio', { name: /Presencial/ }).check();
  await expect(page.getByText('Elige cuánto dura tu asesoría.')).toBeHidden();
  await expect(page.getByRole('complementary')).toContainText('S/ 140,00');
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page).toHaveURL(new RegExp(`/asesorias/agendar/horario/\\?profesional=${PID}&duracion=60&modalidad=presencial`));
});

test('agendar 01: una duracion no ofrecida no se muestra; con una sola ya viene marcada', async ({ page }) => {
  await montarAgendar(page, { prof: { ...PROF, duraciones: [PROF.duraciones[1]] } });
  await page.goto(URL1);
  await expect(page.getByRole('radio', { name: /30 min/ })).toHaveCount(0);
  await expect(page.getByRole('radio', { name: /1 h/ })).toBeChecked();
});

test('agendar 01: IGV que se suma, desglosado desde la API', async ({ page }) => {
  await montarAgendar(page, { prof: { ...PROF, duraciones: [{ minutos: 30, precio: '94.40', igv: { porcentaje: '18.00', incluido: false, base: '80.00', monto: '14.40' } }] } });
  await page.goto(URL1);
  await expect(page.getByRole('radio', { name: /30 min.*S\/ 80,00 \+ IGV \(18 %\) S\/ 14,40 = S\/ 94,40/ })).toBeVisible();
});

test('agendar 01: sin precios publicados, perfil inexistente y fallos de carga', async ({ page }) => {
  await montarAgendar(page, { prof: { ...PROF, duraciones: [] } });
  await page.goto(URL1);
  await expect(page.getByText('Ana Beat aún no tiene precios publicados. Vuelve pronto.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver el directorio' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continuar' })).toBeHidden();
  await simular(page, 'GET', `/profesionales/${PID}`, errorApi(404, 'no_encontrado'));
  await page.goto(URL1);
  await expect(page.getByText('[404] Perfil no disponible')).toBeVisible();
  await expect(page.getByText('Este perfil no existe o ya no está publicado.')).toBeVisible();
  await page.goto('/asesorias/agendar/');
  await expect(page.getByText('Este perfil no existe o ya no está publicado.')).toBeVisible();
});

for (const [n, r, texto] of [
  ['503', (x) => x.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde.'],
  ['red', (x) => x.abort('connectionrefused'), 'Sin conexión.'],
  ['no-json', (x) => x.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), 'No pudimos cargar al profesional.'],
]) {
  test(`agendar 01: el profesional falla (${n}) y se puede reintentar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await montarAgendar(page, { prof: r });
    await page.goto(URL1);
    await expect(page.getByText(texto)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await simular(page, 'GET', `/profesionales/${PID}`, json(200, PROF));
    await page.getByRole('button', { name: 'Reintentar' }).click();
    await expect(page.getByRole('radio', { name: /1 h/ })).toBeVisible();
    expect(consola).toEqual([]);
  });
}

test('agendar: sin JavaScript el contenido estatico explica que hace falta', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(URL1);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Elige tu asesoría');
  expect(await page.content()).toContain('Para agendar necesitas JavaScript. Actívalo en tu navegador y recarga la página.');
  await ctx.close();
});

// ---------- 02 Horario ----------
for (const t of tamanos) {
  test(`agendar 02: inicios validos y NO CABE, elegir y continuar a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await montarAgendar(page);
    await page.goto(URL2);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Elige tu horario');
    await expect(page.getByText('Tu asesoría dura 1 h: elige dónde empieza.')).toBeVisible();
    await expect(page.getByText('Horario de Lima', { exact: true })).toBeVisible();
    const botones = page.locator('bugalu-calendario button[data-inicio]:visible');
    await expect(botones).toHaveCount(t.ancho < 1000 ? 2 : 2); // 10:00 y 12:00: el resto no cabe en el bloque o choca con la asesoria de las 11:00
    if (t.ancho >= 1000) await expect(botones.first()).toHaveAttribute('aria-label', /martes 17 de noviembre, 10:00, libre/);
    if (t.ancho >= 1000) await expect(page.locator('bugalu-calendario td[data-estado="nocabe"]').first()).toContainText('NO CABE 1 h');
    await botones.first().click();
    await expect(page.locator('[data-anuncio]').first()).toContainText('Inicio: martes 17 nov, 10:00 a 11:00');
    await expect(page.getByRole('complementary')).toContainText('10:00 – 11:00');
    await sinViolaciones(page);
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(page).toHaveURL(/\/asesorias\/agendar\/confirmar\/\?.*inicio=/);
    expect(consola).toEqual([]);
    if (t.ancho < 1000) await page.goBack();
  });
}

test('agendar 02: sin inicio al continuar avisa y manda el foco al primer inicio', async ({ page }) => {
  await montarAgendar(page);
  await page.goto(URL2);
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(aviso(page)).toContainText('Elige una hora de inicio en el calendario.');
  await expect(page.locator('bugalu-calendario button[data-inicio]:visible').first()).toBeFocused();
});

test('agendar 02: faltan datos de pasos anteriores y la URL vuelve al primer paso incompleto', async ({ page }) => {
  await montarAgendar(page);
  await page.goto(`/asesorias/agendar/horario/?profesional=${PID}`);
  await expect(page).toHaveURL(new RegExp(`/asesorias/agendar/\\?profesional=${PID}$`));
  await page.goto(`/asesorias/agendar/confirmar/?profesional=${PID}&duracion=60&modalidad=virtual`);
  await expect(page).toHaveURL(/\/asesorias\/agendar\/horario\//);
});

test('agendar 02: el calendario falla y se puede reintentar', async ({ page }) => {
  await montarAgendar(page);
  await simular(page, 'GET', `/profesionales/${PID}/disponibilidad`, errorApi(503, 'servicio_no_disponible'));
  await page.goto(URL2);
  await expect(page.locator('.aviso-titulo', { hasText: 'Los horarios no responden' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
});

test('agendar 03: sin sesion, continuar lleva al acceso con volver al paso 04', async ({ page }) => {
  await montarAgendar(page, { sesion: false });
  await page.goto(URL2);
  await page.locator('bugalu-calendario button[data-inicio]:visible').first().click();
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page).toHaveURL(/\/acceso\?volver=/);
  expect(decodeURIComponent(page.url())).toContain('/asesorias/agendar/confirmar/?profesional=p1&duracion=60&modalidad=virtual&fecha=2026-11-17&inicio=');
});

// ---------- 04 Confirmar ----------
for (const t of tamanos) {
  test(`agendar 04: revision, precio, lugar y condiciones a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await montarAgendar(page);
    await page.goto(URL4);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Confirma tu asesoría');
    const r1 = page.getByRole('region', { name: /Tu asesoría/ }).first();
    await expect(r1).toContainText('Ana Beat');
    await expect(r1).toContainText('1 h');
    await expect(r1).toContainText('Virtual (Google Meet)');
    await expect(r1).toContainText('17 nov, 10:00 – 11:00 (Horario de Lima)');
    await expect(page.getByRole('link', { name: /Cambiar fecha y horario/ })).toBeVisible();
    const tabla = page.getByRole('table', { name: 'Precio de la asesoría' });
    await expect(tabla).toContainText('Asesoría de 1 h con Ana Beat');
    await expect(tabla).toContainText('S/ 140,00');
    await expect(tabla).toContainText('Incluye IGV (18 %)');
    await expect(page.getByText('Pagas el total en un solo pago para confirmar.')).toBeVisible();
    await expect(page.getByText('El enlace de Google Meet te llega por correo')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'Acepto las Condiciones de contratación (versión 0.4.0).' })).not.toBeChecked();
    await expect(page.getByText('La asesoría dura 30 o 60 minutos')).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-agendar-04-${t.nombre}.png`, fullPage: true });
  });
}

test('agendar 04: presencial dice como se acuerda el lugar; sin marcar la casilla no agenda', async ({ page }) => {
  const envios = await montarAgendar(page, { crear: (r) => r.fulfill(json(201, asesoria())) });
  await page.goto(URL4.replace('virtual', 'presencial'));
  await expect(page.getByText('Ana Beat y el estudio te confirmarán el lugar antes de la cita')).toBeVisible();
  await page.getByRole('button', { name: 'Agendar asesoría' }).click();
  await expect(page.getByText('Marca la casilla para aceptar las condiciones; sin ella no podemos agendar tu asesoría.')).toBeVisible();
  expect(envios).toHaveLength(0);
});

test('agendar 04: agenda con el cuerpo del contrato y llega a Listo con "Registrar pago"', async ({ page }) => {
  const envios = await montarAgendar(page, { crear: (r) => r.fulfill(json(201, asesoria())) });
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, asesoria()));
  await page.goto(URL4);
  await agendar(page);
  await expect(page).toHaveURL(new RegExp(`/asesorias/agendar/listo/\\?id=${AID}`));
  expect(envios[0].cuerpo).toEqual({ id_profesional: PID, inicio: INICIO, duracion: 60, modalidad: 'virtual', version_condiciones: '0.4.0' });
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Asesoría agendada');
  await expect(page.getByRole('heading', { name: /A-2026-00001/ })).toBeVisible();
  await expect(page.getByText('PENDIENTE DE PAGO')).toBeVisible();
  await expect(page.getByText(/Paga S\/ 140,00 antes del/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Registrar pago' })).toHaveAttribute('href', /\/app\/asesorias\/pagar\?id=.*&cuota=/);
  await expect(page.getByRole('link', { name: 'Ver mi asesoría' })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf15-agendar-05-1440.png', fullPage: true });
});

test('agendar 05: sin datos de la asesoria muestra el exito corto', async ({ page }) => {
  await montarAgendar(page);
  await simular(page, 'GET', `/asesorias/${AID}`, errorApi(503, 'servicio_no_disponible'));
  await page.goto(`/asesorias/agendar/listo/?id=${AID}`);
  await expect(page.getByText('Asesoría agendada.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver mis asesorías' })).toHaveAttribute('href', '/app/asesorias/mias');
});

// Cada error de POST /asesorias (spec RF-15-agendar, Estados).
const ERRORES = [
  ['409 horario_no_disponible', errorApi(409, 'horario_no_disponible'), 'Alguien agendó ese horario hace un momento. Elige otro; lo demás se conserva.', 'Elegir otro horario'],
  ['409 duracion_no_ofrecida', errorApi(409, 'duracion_no_ofrecida'), 'Ana Beat ya no ofrece asesorías de 1 h. Elige otra.', 'Cambiar duración'],
  ['422 fuera_de_horario', errorApi(422, 'fuera_de_horario'), 'Ese horario ya no está publicado.', 'Elegir otro horario'],
  ['422 anticipacion_insuficiente', errorApi(422, 'anticipacion_insuficiente'), 'Ese horario empieza demasiado pronto para agendarlo.', 'Elegir otro horario'],
  ['422 anticipacion_excesiva', errorApi(422, 'anticipacion_excesiva'), 'Ese horario aún no se puede agendar: está demasiado lejos.', 'Elegir otro horario'],
  ['422 datos_invalidos', errorApi(422, 'datos_invalidos'), 'Algo en tu asesoría no es válido. Revisa los pasos.'],
  ['403', errorApi(403, 'sin_permiso'), 'Las cuentas de profesional no agendan asesorías. Para agendar como artista, usa otra cuenta.', 'Volver al inicio'],
  ['401', errorApi(401, 'no_autenticado'), 'Tu sesión caducó. Inicia sesión para agendar; tu elección se conserva.', 'Iniciar sesión'],
  ['503', errorApi(503, 'servicio_no_disponible'), 'El servicio no responde. Tu asesoría no se guardó; inténtalo en unos minutos.'],
  ['no-json', { status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }, 'Algo salió mal. Tu asesoría no se guardó. Revisa en Mis asesorías si se guardó antes de repetir.'],
];
for (const [nombre, respuesta, texto, enlace] of ERRORES) {
  test(`agendar 04: ${nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await montarAgendar(page, { crear: (r) => r.fulfill(respuesta) });
    await page.goto(URL4);
    await agendar(page);
    await expect(aviso(page)).toContainText(texto);
    await expect(aviso(page)).toBeFocused();
    if (enlace) await expect(aviso(page).getByRole('link', { name: enlace })).toBeVisible();
    if (nombre === '403') await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toBeHidden();
    else await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toBeEnabled();
    if (nombre.startsWith('409 h') || nombre.startsWith('422 f')) await expect(page.locator('.pasos [data-paso="horario"]')).toContainText('REVISAR');
    expect(consola).toEqual([]);
  });
}

test('agendar 04: red caida al agendar no pierde la eleccion', async ({ page }) => {
  await montarAgendar(page, { crear: (r) => r.abort('connectionrefused') });
  await page.goto(URL4);
  await agendar(page);
  await expect(aviso(page)).toContainText('Sin conexión. Tu asesoría no se guardó; revisa tu red.');
});

test('agendar 04: elegir otro horario quita el inicio y conserva lo demas', async ({ page }) => {
  await montarAgendar(page, { crear: (r) => r.fulfill(errorApi(409, 'horario_no_disponible')) });
  await page.goto(URL4);
  await agendar(page);
  await aviso(page).getByRole('link', { name: 'Elegir otro horario' }).click();
  await expect(page).toHaveURL(new RegExp(`/asesorias/agendar/horario/\\?profesional=${PID}&duracion=60&modalidad=virtual&fecha=2026-11-17`));
  expect(page.url()).not.toContain('inicio=');
});

test('agendar 04: texto desactualizado vuelve a pedir la casilla con la version nueva', async ({ page }) => {
  await montarAgendar(page, { crear: (r) => r.fulfill(json(409, { error: { codigo: 'texto_desactualizado', mensaje: 'x', detalles: { vigente: { version: '0.5.0' } } } })) });
  await page.goto(URL4);
  await agendar(page);
  await expect(page.getByText('Las condiciones cambiaron. Lee la versión 0.5.0 y vuelve a marcar la casilla.')).toBeVisible();
  await expect(page.getByRole('checkbox', { name: /Acepto las Condiciones/ })).not.toBeChecked();
});

test('agendar 04: condiciones que no cargan deshabilitan Agendar', async ({ page }) => {
  await montarAgendar(page);
  await simular(page, 'GET', '/textos-legales', errorApi(503, 'servicio_no_disponible'));
  await page.goto(URL4);
  await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toBeDisabled();
  await expect(page.getByText('Necesitamos mostrarte las condiciones antes de continuar.')).toBeVisible();
});

for (const [codigo, aviso_] of [['reaceptacion_requerida', 'textos-pendientes'], ['perfil_incompleto', 'faltan-datos'], ['autorizacion_menor_pendiente', 'menor']]) {
  test(`agendar 04: 409 ${codigo} lleva al paso 03 con la eleccion intacta`, async ({ page }) => {
    await montarAgendar(page, { crear: (r) => r.fulfill(errorApi(409, codigo)) });
    await page.goto(URL4);
    await agendar(page);
    await expect(page).toHaveURL(new RegExp(`/asesorias/agendar/cuenta/\\?profesional=${PID}&duracion=60&modalidad=virtual&inicio=.*`));
    if (aviso_ === 'menor') await expect(page.getByText('Aún no puedes agendar en línea')).toBeVisible();
    else await expect(page.getByRole('heading', { level: 1 })).toHaveText('Completa tus datos');
  });
}

test('agendar 04: la cuenta de profesional ve el aviso y no el formulario', async ({ page }) => {
  await montarAgendar(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'profesional', datos_para_reservar: true, pendientes: [] })));
  await page.goto(URL4);
  await expect(aviso(page)).toContainText('Las cuentas de profesional no agendan asesorías. Para agendar como artista, usa otra cuenta.');
  await expect(page.getByRole('button', { name: 'Agendar asesoría' })).toBeHidden();
});

// ---------- 03 Cuenta ----------
test('agendar 03: con todo completo salta al paso 04', async ({ page }) => {
  await montarAgendar(page);
  await page.goto(URL4.replace('confirmar', 'cuenta'));
  await expect(page).toHaveURL(/\/asesorias\/agendar\/confirmar\//);
});

test('agendar 03: faltan datos, se completan y sigue al paso 04', async ({ page }) => {
  await montarAgendar(page, { perfilExtra: { telefono: null, documento: null, datos_para_reservar: false } });
  let guardado = null;
  await simular(page, 'PATCH', '/perfil', (r) => { guardado = r.request().postDataJSON(); return r.fulfill(json(200, { id: 'u1', nombre: 'Ana Pérez', telefono: '999111222', rol: 'cliente' })); });
  await page.goto(URL4.replace('confirmar', 'cuenta'));
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Completa tus datos');
  await page.getByRole('button', { name: 'Guardar y continuar' }).click();
  await expect(page.getByText('Elige el tipo de documento.')).toBeVisible();
  await page.getByLabel('Tipo de documento').selectOption('dni');
  await page.getByLabel('Número').fill('12345678');
  await page.getByLabel(/Teléfono/).fill('999111222');
  await page.getByRole('button', { name: 'Guardar y continuar' }).click();
  await expect(page).toHaveURL(/\/asesorias\/agendar\/confirmar\//);
  expect(guardado.documento).toEqual({ tipo: 'dni', numero: '12345678' });
});
