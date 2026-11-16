// RF-04 (CA-01, CA-02, CA-09, CA-10) y RF-02 (CA-05): reserva por pasos. La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const R1 = '11111111-1111-4111-8111-111111111111';
const INI = '2026-11-19T10:00:00-05:00';
const t = (dia, hora) => `2026-11-${dia}T${hora}:00-05:00`;
const SERV = [
  { id: 's1', nombre: 'Grabación', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '0.00', especialistas_por_defecto: ['e1'], activo: true },
  { id: 's2', nombre: 'Ensayo', categoria: 'ensayo', ocupa_sala: true, tarifa_hora: '60.00', monto_fijo: '0.00', especialistas_por_defecto: [], activo: true },
  { id: 's3', nombre: 'Mezcla', categoria: 'posproduccion', ocupa_sala: false, tarifa_hora: '0.00', monto_fijo: '300.00', especialistas_por_defecto: [], activo: true },
  { id: 's4', nombre: 'Live viejo', categoria: 'live', ocupa_sala: true, tarifa_hora: '90.00', monto_fijo: '0.00', especialistas_por_defecto: [], activo: false },
];
const ESP = [
  { id: 'e1', nombre: 'Ingeniero de sonido', monto_fijo: '30.00', monto_variable: '25.00', unidad: 'hora', activo: true },
  { id: 'e2', nombre: 'Productor', monto_fijo: '0.00', monto_variable: '15.00', unidad: 'lapso_30', activo: true },
  { id: 'e3', nombre: 'Baja', monto_fijo: '0.00', monto_variable: '1.00', unidad: 'hora', activo: false },
];
const SIM = {
  lineas: [{ concepto: 'Grabación', cantidad: '2.0', unidad: 'hora', monto: '240.00' }, { concepto: 'Ingeniero de sonido (monto fijo)', cantidad: '1', unidad: 'fijo', monto: '30.00' }],
  recargos: [{ tipo: 'noche', bloques: 2, monto: '20.00' }],
  total: '290.00',
  anticipo: '145.00',
};
const RESERVA = { id: R1, folio: 'RSV-0013', estado: 'pre_reservada', motivo_cancelacion: null, inicio: INI, fin: t('19', '12:00'), fin_buffer: t('19', '12:30'), sala: 'La Molina', servicio: 'Grabación', especialistas: [{ id: 'e1', nombre: 'Ingeniero de sonido' }], precio: SIM, cuotas: [], vence_pago: '2026-11-17T10:00:00-05:00' };
const DISP = {
  limites: { desde: t('16', '10:00'), hasta: '2026-12-15T10:00:00-05:00' },
  franjas: [{ id: 'f1', inicio: t('19', '10:00'), fin: t('19', '14:00') }],
  ocupados: [], cierres: [],
  dias: ['16', '17', '18', '19', '20', '21', '22'].map((d) => ({ fecha: `2026-11-${d}`, minutos_libres: d === '19' ? 240 : 0 })),
};
const PASO2 = `/reservar/servicio/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1`;
const PASO4 = `/reservar/confirmar/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`;

// `sesion`: con cuenta; `sim` / `crear`: funciones (ruta) -> respuesta; devuelve los cuerpos enviados.
async function montar(page, { sesion = true, sim = (r) => r.fulfill(json(200, SIM)), crear = (r) => r.fulfill(json(201, RESERVA)), servicios = () => json(200, SERV), especialistas = () => json(200, ESP) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  if (sesion) await conSesion(page);
  await silenciarApi(page);
  const envios = { sim: [], crear: [] };
  if (sesion) await page.route(`${API}/perfil`, (r) => r.fulfill(perfil()));
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [{ id: 'sala-1', nombre: 'La Molina' }])));
  await page.route(`${API}/disponibilidad?**`, (r) => r.fulfill(json(200, DISP)));
  await page.route(`${API}/servicios`, (r) => r.fulfill(servicios()));
  await page.route(`${API}/especialistas`, (r) => r.fulfill(especialistas()));
  await page.route(`${API}/simulaciones`, (r) => { envios.sim.push(r.request().postDataJSON()); return sim(r); });
  await page.route(`${API}/reservas`, (r) => { envios.crear.push(r.request().postDataJSON()); return crear(r); });
  await page.route(`${API}/reservas/${R1}`, (r) => r.fulfill(json(200, RESERVA)));
  return envios;
}
const aviso = (page) => page.locator('bugalu-reserva [data-avisos] [role="alert"], bugalu-reserva [data-avisos] [role="status"]');
const total = (page) => page.getByRole('row', { name: /Total/i });

test.describe('01 Horario', () => {
  test('elige inicio y duración; continuar lleva al servicio con todo en la URL', async ({ page }) => {
    const consola = vigilarConsola(page);
    await montar(page, { sesion: false });
    await page.goto('/reservar/?fecha=2026-11-16');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Elige tu horario');
    await expect(page.getByText('PASO 01 / 05')).toBeVisible();
    await expect(page.getByRole('combobox', { name: 'Duración' })).toBeDisabled();
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(aviso(page)).toContainText('Elige una hora de inicio en el calendario.');
    await page.getByRole('button', { name: 'jueves 19 de noviembre, 10:00, libre' }).click();
    const duracion = page.getByRole('combobox', { name: 'Duración' });
    await expect(duracion).toBeEnabled();
    await expect(duracion).toHaveValue('60');
    expect(await duracion.locator('option').allTextContents()).toEqual(['30 min', '1 h', '1 h 30 min', '2 h', '2 h 30 min', '3 h', '3 h 30 min']);
    await duracion.selectOption('120');
    await page.screenshot({ path: 'pruebas/capturas/reservar-01-horario-1440.png', fullPage: true });
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(page).toHaveURL(/\/reservar\/servicio\/\?/);
    const p = new URL(page.url()).searchParams;
    expect([p.get('inicio'), p.get('duracion'), p.get('sala')]).toEqual([INI, '120', 'sala-1']);
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    expect(consola).toEqual([]);
  });

  test('la selección de la URL se restaura', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto(`/reservar/?fecha=2026-11-16&inicio=${encodeURIComponent(INI)}&duracion=90`);
    await expect(page.getByRole('combobox', { name: 'Duración' })).toHaveValue('90');
  });

  test('al restaurar el inicio de la URL, la duración se limita a lo que cabe', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto(`/reservar/?fecha=2026-11-16&inicio=${encodeURIComponent(INI)}&duracion=420`);
    const duracion = page.getByRole('combobox', { name: 'Duración' });
    expect(await duracion.locator('option').allTextContents()).toEqual(['30 min', '1 h', '1 h 30 min', '2 h', '2 h 30 min', '3 h', '3 h 30 min']);
    await expect(duracion).toHaveValue('60');
  });

  for (const tm of tamanos) {
    test(`axe en horario a ${tm.nombre}`, async ({ page }) => {
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { sesion: false });
      await page.goto('/reservar/?fecha=2026-11-16');
      await expect(page.getByRole('combobox', { name: 'Duración' })).toBeDisabled();
      await page.getByRole('button', { name: 'Continuar' }).click();
      await expect(aviso(page)).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-01-error-${tm.nombre}.png`, fullPage: true });
    });

    test(`axe en horario con un inicio seleccionado a ${tm.nombre}`, async ({ page }) => {
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { sesion: false });
      await page.goto(`/reservar/?fecha=2026-11-16&inicio=${encodeURIComponent(INI)}&duracion=90`);
      await expect(page.getByRole('combobox', { name: 'Duración' })).toBeEnabled();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-01-inicio-${tm.nombre}.png`, fullPage: true });
    });
  }

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('explica qué hace falta', async ({ page }) => {
      await page.goto('/reservar/');
      // Playwright ignora el texto de <noscript>: se comprueba en el HTML y en lo que se ve.
      expect(await page.content()).toContain('El calendario necesita JavaScript. Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-calendario noscript .aviso-titulo')).toBeVisible();
      await expect(page.locator('bugalu-reserva [data-cuerpo]')).toBeHidden();
      await page.screenshot({ path: 'pruebas/capturas/reservar-sin-js.png', fullPage: true });
    });
  });
});

test.describe('02 Servicio', () => {
  test('lista solo servicios que ocupan sala, marca los especialistas incluidos y simula', async ({ page }) => {
    const consola = vigilarConsola(page);
    const envios = await montar(page, { sesion: false });
    await page.goto(PASO2);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Servicio y precio');
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    const servicios = page.getByRole('group', { name: 'Servicio' });
    await expect(servicios.getByRole('radio')).toHaveCount(2);
    await expect(servicios).toContainText('S/ 120,00 por hora');
    await expect(servicios).toContainText('Graba voces, instrumentos o tu banda en vivo.');
    await expect(page.getByRole('group', { name: 'Especialistas' }).getByRole('checkbox')).toHaveCount(2);
    await expect(page.getByRole('group', { name: 'Especialistas' })).toContainText('S/ 15,00 por media hora');
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(aviso(page)).toContainText('Elige un servicio.');
    await page.getByRole('radio', { name: /Grabación/ }).check();
    const incluido = page.getByRole('checkbox', { name: /Ingeniero de sonido/ });
    await expect(incluido).toBeChecked();
    await expect(incluido).toHaveAttribute('aria-disabled', 'true');
    await expect(page.getByRole('group', { name: 'Especialistas' })).toContainText('Incluido con este servicio');
    await incluido.click({ force: true });
    await expect(incluido).toBeChecked();
    const precio = page.getByRole('region', { name: 'Precio simulado' });
    await expect(precio.getByRole('cell', { name: 'S/ 240,00' })).toBeVisible();
    await expect(precio).toContainText('Recargo de noche');
    await expect(precio.getByRole('row', { name: /Total.*S\/ 290,00/i })).toBeVisible();
    await expect(precio.getByRole('row', { name: /Anticipo 50 %.*S\/ 145,00/i })).toBeVisible();
    await expect(precio).toContainText('Esta simulación no tiene valor de cotización.');
    expect(envios.sim.at(-1)).toEqual({ id_sala: 'sala-1', id_servicio: 's1', inicio: INI, fin: t('19', '12:00'), especialistas: [] });
    await expect(page.locator('bugalu-reserva [data-anuncio]')).toHaveText('Total S/ 290,00, anticipo S/ 145,00');
    // Un especialista adicional recalcula una sola vez y viaja en `esp`.
    const antes = envios.sim.length;
    await page.getByRole('checkbox', { name: /Productor/ }).check();
    await expect.poll(() => envios.sim.length).toBe(antes + 1);
    expect(envios.sim.at(-1).especialistas).toEqual(['e2']);
    expect(new URL(page.url()).searchParams.get('esp')).toBe('e2');
    await expect(page.getByRole('region', { name: 'Tu reserva' })).toContainText('Grabación');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/reservar-02-servicio-1440.png', fullPage: true });
    expect(consola).toEqual([]);
  });

  test('sin sesión, continuar va al acceso y vuelve a confirmar con la elección', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto(`${PASO2}&servicio=s1`);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(page).toHaveURL(/\/acceso\/?\?volver=/);
    const volver = new URL(page.url()).searchParams.get('volver');
    expect(volver).toBe(`/reservar/confirmar/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`);
  });

  test('teclado: servicio con flechas, especialista con Espacio y Continuar con Enter', async ({ page }) => {
    const envios = await montar(page);
    await page.goto(PASO2);
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    await page.keyboard.press('Tab'); // primero los pasos: HECHO es enlace
    await expect(pasos(page).getByRole('link', { name: /Horario/ })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('radio', { name: /Grabación/ })).toBeFocused();
    await page.keyboard.press('Space');
    await expect(page.getByRole('radio', { name: /Grabación/ })).toBeChecked();
    await page.keyboard.press('Tab'); // el incluido sigue enfocable
    await expect(page.getByRole('checkbox', { name: /Ingeniero de sonido/ })).toBeFocused();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Space');
    await expect(page.getByRole('checkbox', { name: /Productor/ })).toBeChecked();
    await expect.poll(() => envios.sim.at(-1)?.especialistas).toEqual(['e2']);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Continuar' }).focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/reservar\/confirmar\/\?.*esp=e2/);
  });

  test('con sesión, continuar va a confirmar', async ({ page }) => {
    await montar(page);
    await page.goto(`${PASO2}&servicio=s1`);
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(page).toHaveURL(/\/reservar\/confirmar\/\?/);
  });

  test('sin inicio en la URL vuelve al horario', async ({ page }) => {
    await montar(page);
    await page.goto('/reservar/servicio/');
    await expect(page).toHaveURL(/\/reservar\/?$/);
  });

  for (const [nombre, sim, texto, enlace] of [
    ['tramo_invalido', (r) => r.fulfill(errorApi(422, 'tramo_invalido')), 'Ese horario ya no es válido. Vuelve a elegirlo.', 'Elegir otro horario'],
    ['servicio_no_reservable', (r) => r.fulfill(errorApi(422, 'servicio_no_reservable')), 'Ese servicio no se reserva en sala. Elige otro.'],
    ['datos_invalidos', (r) => r.fulfill(errorApi(422, 'datos_invalidos')), 'No pudimos calcular el precio con estos datos. Revisa tu elección.'],
    ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde.', 'Reintentar'],
    ['red', (r) => r.abort(), 'Sin conexión.', 'Reintentar'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<html>' }), 'Algo salió mal al calcular el precio.', 'Reintentar'],
  ]) {
    test(`simulación ${nombre}`, async ({ page }) => {
      await montar(page, { sesion: false, sim });
      await page.goto(`${PASO2}&servicio=s1`);
      const precio = page.getByRole('region', { name: 'Precio simulado' });
      await expect(precio).toContainText(texto);
      if (enlace) await expect(precio.getByRole(enlace === 'Reintentar' ? 'button' : 'link', { name: enlace })).toBeVisible();
      await sinViolaciones(page);
    });
  }

  test('reintentar recalcula', async ({ page }) => {
    let n = 0;
    await montar(page, { sesion: false, sim: (r) => r.fulfill(n++ ? json(200, SIM) : errorApi(503, 'x')) });
    await page.goto(`${PASO2}&servicio=s1`);
    await page.getByRole('button', { name: 'Reintentar' }).click();
    await expect(total(page)).toBeVisible();
  });

  test('catálogo en error', async ({ page }) => {
    await montar(page, { sesion: false, servicios: () => errorApi(503, 'x') });
    await page.goto(PASO2);
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await sinViolaciones(page);
  });

  test('catálogo vacío', async ({ page }) => {
    await montar(page, { sesion: false, servicios: () => json(200, []) });
    await page.goto(PASO2);
    await expect(page.getByText('Ahora no hay servicios disponibles para reservar. Vuelve pronto.')).toBeVisible();
    await sinViolaciones(page);
  });

  for (const tm of tamanos) {
    test(`axe en servicio a ${tm.nombre}`, async ({ page }) => {
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { sesion: false });
      await page.goto(`${PASO2}&servicio=s1`);
      await expect(total(page)).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-02-servicio-${tm.nombre}.png`, fullPage: true });
    });
  }
});

test.describe('04 Confirmar y 05 Listo', () => {
  test('confirma, envía el cuerpo del contrato y muestra el folio', async ({ page }) => {
    const consola = vigilarConsola(page);
    const envios = await montar(page);
    await page.goto(`${PASO4}&esp=e2`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Confirma tu reserva');
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    await expect(page.getByRole('link', { name: /Cambiar horario/ })).toHaveAttribute('href', /^\/reservar\/\?/);
    await expect(total(page)).toBeVisible();
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/reservar-04-confirmar-1440.png', fullPage: true });
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    await expect(page).toHaveURL(new RegExp(`/reservar/listo/\\?id=${R1}`));
    expect(envios.crear).toEqual([{ id_sala: 'sala-1', id_servicio: 's1', inicio: INI, fin: t('19', '12:00'), especialistas: ['e2'], detalle: 'Voz y guitarra' }]);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Reserva registrada');
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
    await expect(page.getByText('RSV-0013').first()).toBeVisible();
    await expect(page.getByText('PRE-RESERVADA')).toBeVisible();
    await expect(page.getByText(/Paga el anticipo de S\/ 145,00 antes del/)).toBeVisible();
    await expect(page.getByText('Te enviamos estos datos a ana@correo.com.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver mi reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${R1}`);
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/reservar-05-listo-1440.png', fullPage: true });
    expect(consola).toEqual([]);
  });

  test('sin sesión, confirmar lleva al acceso con volver', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto(PASO4);
    await expect(page).toHaveURL(/\/acceso\/?\?volver=/);
  });

  test('doble envío: una sola petición mientras confirma', async ({ page }) => {
    const envios = await montar(page, { crear: async (r) => { await new Promise((x) => setTimeout(x, 400)); await r.fulfill(json(201, RESERVA)); } });
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar reserva' }).dblclick();
    await expect(page).toHaveURL(/listo/);
    expect(envios.crear).toHaveLength(1);
  });

  for (const [nombre, respuesta, texto, enlace, destino] of [
    ['409 tramo_no_disponible', () => errorApi(409, 'tramo_no_disponible'), 'Alguien reservó ese horario hace un momento. Elige otro; lo demás se conserva.', 'Elegir otro horario', /^\/reservar\/\?.*servicio=s1/],
    ['403 ensayo_no_disponible', () => errorApi(403, 'ensayo_no_disponible'), 'El ensayo es para quien ya tiene una sesión confirmada con nosotros. Elige grabación o live session.', 'Cambiar servicio', /^\/reservar\/servicio\//],
    ['422 fuera_de_franja', () => errorApi(422, 'fuera_de_franja'), 'Ese horario ya no está publicado.', 'Elegir otro horario', /^\/reservar\/\?/],
    ['422 anticipacion_insuficiente', () => errorApi(422, 'anticipacion_insuficiente'), 'Ese horario empieza demasiado pronto para reservarlo.', 'Elegir otro horario', /^\/reservar\/\?/],
    ['422 anticipacion_excesiva', () => errorApi(422, 'anticipacion_excesiva'), 'Ese horario aún no se puede reservar: está demasiado lejos.', 'Elegir otro horario', /^\/reservar\/\?/],
    ['422 duracion_invalida', () => errorApi(422, 'duracion_invalida'), 'La duración va de 30 min a 8 h, en bloques de 30 min.', 'Elegir otro horario', /^\/reservar\/\?/],
    ['422 servicio_no_reservable', () => errorApi(422, 'servicio_no_reservable'), 'Ese servicio no se reserva en sala. Elige otro.', 'Cambiar servicio', /^\/reservar\/servicio\//],
    ['422 datos_invalidos', () => errorApi(422, 'datos_invalidos'), 'Algo en tu reserva no es válido. Revisa los pasos.'],
    ['422 datos_invalidos detalle', () => json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'detalle' } } }), 'El detalle no es válido. Máximo 500 caracteres.'],
    ['401', () => errorApi(401, 'no_autenticado'), 'Tu sesión caducó. Inicia sesión para confirmar; tu elección se conserva.', 'Iniciar sesión', /^\/acceso\/?\?volver=/],
    ['503', () => errorApi(503, 'x'), 'El servicio no responde. Tu reserva no se guardó; inténtalo en unos minutos.'],
    ['no JSON', () => ({ status: 200, contentType: 'text/html', body: '<html>' }), 'Algo salió mal. Revisa en Mis reservas si se guardó antes de repetir.'],
  ]) {
    test(`error al confirmar: ${nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page, { crear: (r) => r.fulfill(respuesta()) });
      await page.goto(PASO4);
      await expect(total(page)).toBeVisible();
      await page.getByRole('button', { name: 'Confirmar reserva' }).click();
      await expect(aviso(page)).toContainText(texto);
      if (nombre.endsWith('detalle')) await expect(page.getByLabel('Qué necesitas (opcional)')).toBeFocused();
      else await expect(aviso(page)).toBeFocused();
      await expect(page.getByRole('button', { name: 'Confirmar reserva' })).toBeEnabled();
      if (enlace) await expect(aviso(page).getByRole('link', { name: enlace })).toHaveAttribute('href', destino);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('error 409 marca el paso Horario para revisar', async ({ page }) => {
    await montar(page, { crear: (r) => r.fulfill(errorApi(409, 'tramo_no_disponible')) });
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    await expect(page.getByRole('navigation', { name: 'Progreso de la reserva' })).toContainText('REVISAR');
    await page.screenshot({ path: 'pruebas/capturas/reservar-04-error-409-1440.png', fullPage: true });
  });

  test('red caída al confirmar', async ({ page }) => {
    await montar(page, { crear: (r) => r.abort() });
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    await expect(aviso(page)).toContainText('Sin conexión. Tu reserva no se guardó; revisa tu red.');
  });

  test('sin precio no se puede confirmar', async ({ page }) => {
    await montar(page, { sim: (r) => r.fulfill(errorApi(503, 'x')) });
    await page.goto(PASO4);
    await expect(page.getByRole('button', { name: 'Confirmar reserva' })).toBeDisabled();
    await expect(page.getByText('Necesitamos mostrarte el precio antes de confirmar.')).toBeVisible();
    await sinViolaciones(page);
  });

  test('listo sin datos: aviso de éxito y enlace a mis reservas', async ({ page }) => {
    await montar(page);
    await page.route(`${API}/reservas/${R1}`, (r) => r.fulfill(errorApi(503, 'x')));
    await page.goto(`/reservar/listo/?id=${R1}`);
    await expect(page.getByText('Reserva registrada.', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver mis reservas' })).toHaveAttribute('href', '/app/reservas');
    await sinViolaciones(page);
  });

  for (const tm of tamanos) {
    test(`axe en confirmar y listo a ${tm.nombre}`, async ({ page }) => {
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page);
      await page.goto(PASO4);
      await expect(total(page)).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-04-confirmar-${tm.nombre}.png`, fullPage: true });
      await page.goto(`/reservar/listo/?id=${R1}`);
      await expect(page.getByText('RSV-0013').first()).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-05-listo-${tm.nombre}.png`, fullPage: true });
    });
  }
});

test('sinToken: una consulta pública con sesión caducada se repite sin token', async ({ page }) => {
  await conSesion(page);
  await silenciarApi(page);
  const cabeceras = [];
  await page.route(`${API}/servicios`, (r) => {
    const auth = r.request().headers().authorization;
    cabeceras.push(Boolean(auth));
    return r.fulfill(auth ? errorApi(401, 'no_autenticado') : json(200, SERV));
  });
  await page.route(`${API}/especialistas`, (r) => r.fulfill(json(200, ESP)));
  await page.goto(PASO2);
  await expect(page.getByRole('group', { name: 'Servicio' }).getByRole('radio')).toHaveCount(2);
  expect(cabeceras).toEqual([true, false]);
});

// --- TAREA-RF04-7: correcciones de la revisión visual (B3, B4, N2 a N8) ---
const SIM_LARGA = { ...SIM, lineas: [{ concepto: 'Grabación', cantidad: '2.5', unidad: 'hora', monto: '300.00' }, { concepto: 'Productor', cantidad: '5', unidad: 'lapso_30', monto: '75.00' }, SIM.lineas[1]] };
const pasos = (page) => page.getByRole('navigation', { name: 'Progreso de la reserva' });
const token = (page, v) => page.evaluate((x) => { const s = document.createElement('i'); s.style.color = `var(${x})`; document.body.append(s); const c = getComputedStyle(s).color; s.remove(); return c; }, v);

test.describe('B3 partidas', () => {
  test('cantidad como duración de reserva, recargo con su nombre, pie en tfoot y cifras a la derecha', async ({ page }) => {
    await montar(page, { sim: (r) => r.fulfill(json(200, SIM_LARGA)) });
    await page.goto(`${PASO2}&servicio=s1`);
    const tabla = page.getByRole('table', { name: 'Partidas' });
    await expect(tabla.getByRole('row', { name: /^Grabación/ })).toContainText('2 h 30 min');
    await expect(tabla.getByRole('row', { name: /^Productor/ })).toContainText('5 × 30 min');
    await expect(tabla.getByRole('row', { name: /monto fijo/ }).getByRole('cell').first()).toHaveText('1');
    const recargo = tabla.getByRole('row', { name: /^Recargo de noche/ });
    await expect(recargo.getByRole('rowheader')).toHaveText('Recargo de noche');
    await expect(recargo).toContainText('2 × 30 min');
    await expect(tabla.locator('tfoot tr')).toHaveCount(2);
    await expect(tabla.locator('tfoot')).toContainText('Total');
    await expect(tabla.locator('tfoot')).toContainText('Anticipo 50 %');
    await expect(tabla.locator('tbody tr', { hasText: 'Total' })).toHaveCount(0);
    const estilo = (loc) => loc.evaluate((e) => { const c = getComputedStyle(e); return { a: c.textAlign, n: c.fontVariantNumeric, p: c.fontWeight }; });
    const importe = await estilo(tabla.locator('tbody tr').first().locator('td').last());
    expect(['right', 'end']).toContain(importe.a);
    expect(importe.n).toContain('tabular-nums');
    expect(['right', 'end']).toContain((await estilo(tabla.locator('thead th').last())).a);
    expect(Number((await estilo(tabla.locator('tfoot th').first())).p)).toBeGreaterThanOrEqual(700);
  });

  test('a 390 sigue siendo tabla, sin tarjetas', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await montar(page);
    await page.goto(`${PASO2}&servicio=s1`);
    const tabla = page.getByRole('table', { name: 'Partidas' });
    await expect(tabla.locator('tbody tr').first()).toBeVisible();
    expect(await tabla.locator('tbody tr').first().evaluate((e) => getComputedStyle(e).display)).toBe('table-row');
    await expect(tabla.locator('thead th').first()).toBeVisible();
    expect(await tabla.evaluate((e) => e.scrollWidth <= e.clientWidth)).toBe(true);
  });
});

test.describe('B4 pasos', () => {
  test('1440: HECHO enlaza al paso con la consulta, CUENTA es texto, actual y pendiente', async ({ page }) => {
    await montar(page);
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    const nav = pasos(page);
    await expect(nav.getByRole('listitem')).toHaveCount(5);
    const horario = nav.getByRole('link', { name: /Horario/ });
    await expect(horario).toHaveAttribute('href', `/reservar/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`);
    await expect(horario).toContainText('HECHO');
    await expect(horario.locator('svg')).toHaveCount(1);
    await expect(nav.getByRole('link', { name: /Servicio/ })).toHaveAttribute('href', /^\/reservar\/servicio\/\?.*servicio=s1/);
    await expect(nav.getByRole('link')).toHaveCount(2);
    await expect(nav.getByRole('listitem').filter({ hasText: 'Cuenta' })).toContainText('HECHO');
    await expect(nav.locator('[aria-current="step"]')).toContainText('Confirmar');
    const listo = nav.getByRole('listitem').filter({ hasText: 'Listo' });
    await expect(listo).toContainText('PENDIENTE');
    expect(await listo.locator('.pasos-paso').evaluate((e) => getComputedStyle(e).color)).toBe(await token(page, '--color-texto-secundario'));
  });

  test('REVISAR va en color de alerta y el paso sigue siendo enlace', async ({ page }) => {
    await montar(page, { crear: (r) => r.fulfill(errorApi(409, 'tramo_no_disponible')) });
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    const item = pasos(page).getByRole('listitem').filter({ hasText: 'REVISAR' });
    await expect(item).toHaveCount(1);
    await expect(item.getByRole('link', { name: /Horario/ })).toBeVisible();
    expect(await item.locator('[data-lectura]').evaluate((e) => getComputedStyle(e).color)).toBe(await token(page, '--color-texto-alerta'));
  });

  test('390: Compacta con "PASO 4 DE 5" y barra de progreso; la lista horizontal se oculta', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await montar(page);
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    const nav = pasos(page);
    await expect(nav).toContainText('PASO 4 DE 5 · Confirmar');
    await expect(nav.getByRole('progressbar')).toHaveAttribute('value', '4');
    await expect(nav.getByRole('listitem')).toHaveCount(0); // display: none en móvil
  });

  test('en Listo los pasos no llevan enlaces', async ({ page }) => {
    await montar(page);
    await page.goto(`/reservar/listo/?id=${R1}`);
    await expect(page.getByText('RSV-0013').first()).toBeVisible();
    await expect(pasos(page).getByRole('link')).toHaveCount(0);
  });
});

test.describe('N2 a N8', () => {
  test('N3: L1 conserva su código y no hay fila FOLIO', async ({ page }) => {
    await montar(page);
    await page.goto(`/reservar/listo/?id=${R1}`);
    const panel = page.getByRole('region', { name: /Reserva RSV-0013/ });
    await expect(panel.locator('.panel-codigo')).toHaveText('L1');
    await expect(panel.locator('.panel-titulo')).toContainText('Reserva RSV-0013');
    await expect(panel.locator('dt', { hasText: 'Folio' })).toHaveCount(0);
  });

  test('N2: hueco entre los bloques de Listo y entre la etiqueta y SALA', async ({ page }) => {
    await montar(page);
    await page.goto(`/reservar/listo/?id=${R1}`);
    await expect(page.getByText('RSV-0013').first()).toBeVisible();
    const g = await page.locator('[data-listo]').evaluate((e) => ({ d: getComputedStyle(e).display, g: getComputedStyle(e).rowGap }));
    expect(g).toEqual({ d: 'grid', g: '20px' });
    await page.goto(PASO2);
    const lateral = page.getByRole('region', { name: 'Tu reserva' });
    await expect(lateral).toBeVisible();
    const [etiqueta, sala] = await Promise.all([lateral.locator('.etiqueta').boundingBox(), lateral.locator('dt', { hasText: 'Sala' }).boundingBox()]);
    expect(sala.y - (etiqueta.y + etiqueta.height)).toBeGreaterThanOrEqual(12);
  });

  test('N2: el aviso no toca la rejilla', async ({ page }) => {
    await montar(page, { crear: (r) => r.fulfill(errorApi(503, 'x')) });
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    const [a, r] = await Promise.all([aviso(page).boundingBox(), page.locator('.res-rejilla').boundingBox()]);
    expect(r.y - (a.y + a.height)).toBeGreaterThanOrEqual(20);
  });

  test('N4: el panel de tiempo de sala no lleva código', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto('/reservar/?fecha=2026-11-16');
    await expect(page.locator('bugalu-reserva .panel-titulo', { hasText: 'Tiempo de sala' })).toBeAttached();
    await expect(page.locator('bugalu-reserva .panel-codigo')).toHaveCount(0);
  });

  test('N5: en 04 no hay resumen lateral y R1 no repite importes', async ({ page }) => {
    await montar(page);
    await page.goto(PASO4);
    await expect(total(page)).toBeVisible();
    await expect(page.locator('bugalu-reserva aside')).toHaveCount(0);
    const r1 = page.getByRole('region', { name: 'Tu reserva' });
    await expect(r1).toBeVisible();
    await expect(r1).not.toContainText('Anticipo');
    await expect(r1).not.toContainText('Total');
  });

  test('N6: a 390 el aviso de "Elige una hora" mueve el foco a un control visible del calendario', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await montar(page, { sesion: false });
    await page.goto('/reservar/?fecha=2026-11-16');
    await expect(page.locator('bugalu-calendario summary').first()).toBeVisible();
    await page.getByRole('button', { name: 'Continuar' }).click();
    await expect(aviso(page)).toContainText('Elige una hora de inicio en el calendario.');
    const foco = await page.evaluate(() => { const e = document.activeElement; return { dentro: !!e.closest('bugalu-calendario'), visible: e.offsetParent !== null, tag: e.tagName }; });
    expect(foco.dentro && foco.visible && ['BUTTON', 'SUMMARY'].includes(foco.tag)).toBe(true);
  });

  test('N8: tras registrarse, el paso 04 da la bienvenida y quita el parámetro', async ({ page }) => {
    await montar(page);
    await page.goto(`${PASO4}&aviso=cuenta-creada`);
    await expect(total(page)).toBeVisible();
    await expect(page.locator('bugalu-reserva [data-avisos] [role="status"]')).toContainText('Cuenta creada. Revisa tu reserva y confírmala.');
    expect(new URL(page.url()).searchParams.has('aviso')).toBe(false);
    await sinViolaciones(page);
  });

  test.describe('N7 sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('en el horario solo se pinta el aviso del calendario', async ({ page }) => {
      await page.goto('/reservar/');
      const html = await page.content();
      expect(html).toContain('El calendario necesita JavaScript');
      expect(html).not.toContain('Para reservar necesitas JavaScript');
      await page.goto('/reservar/servicio/');
      expect(await page.content()).toContain('Para reservar necesitas JavaScript');
    });
  });
});
