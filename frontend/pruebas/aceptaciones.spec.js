// RF-17 etapa A (CA-03, CA-04, CA-05, CA-07, CA-08, CA-13): aceptaciones en /acceso/textos, requisitos al reservar y resumen del pago. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { t, TEXTOS, P, PERFIL, perfilApi } from './ayudas-rf17.js';

async function montar(page, { sesion = true, perfilR = perfilApi(), textos = json(200, TEXTOS) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  if (sesion) await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfilR));
  const vistas = { aceptar: await simular(page, 'POST', '/aceptaciones', json(201, [])) };
  await page.route(`${API}/textos-legales`, (r) => r.fulfill(textos));
  await page.route(`${API}/contacto-estudio`, (r) => r.fulfill(json(200, { texto: 'Escríbenos a hola@bugalu.studio' })));
  return vistas;
}
const PENDIENTES = perfilApi({ pendientes: [P('terminos_uso', '1.0.0'), P('politica_privacidad', '1.2.3')] });
const casilla = (page) => page.getByRole('checkbox', { name: /Acepto los Términos de uso \(versión 1\.0\.0\)/ });

test.describe('/acceso/textos', () => {
  for (const tm of tamanos) {
    test(`resumen, casilla sin marcar y enlaces a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { perfilR: PENDIENTES });
      await page.goto('/acceso/textos/?volver=%2Fapp%2Freservas');
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Antes de empezar');
      await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
      await expect(page.getByText('Reglas de uso del estudio.')).toBeVisible();
      await expect(page.getByText('Cómo tratamos tus datos.')).toBeVisible();
      await expect(casilla(page)).not.toBeChecked();
      await expect(page.getByRole('link', { name: /Leer los Términos de uso \(versión 1\.0\.0\)/ })).toHaveAttribute('href', '/legal/terminos-de-uso/?version=1.0.0');
      await expect(page.getByRole('link', { name: /Leer la Política de privacidad/ })).toHaveAttribute('target', '_blank');
      const aceptar = page.getByRole('button', { name: 'Aceptar y continuar' });
      const ahoraNo = page.getByRole('button', { name: 'Ahora no' });
      expect((await aceptar.boundingBox()).width).toBeCloseTo((await ahoraNo.boundingBox()).width, 0);
      expect((await aceptar.boundingBox()).height).toBeCloseTo((await ahoraNo.boundingBox()).height, 0);
      await expect(page.getByRole('navigation', { name: 'Legal' }).getByRole('link')).toHaveCount(5);
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/acceso-textos-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }

  test('acepta: envía los textos, y vuelve con el aviso de éxito', async ({ page }) => {
    const vistas = await montar(page, { perfilR: PENDIENTES });
    await page.goto('/acceso/textos/?volver=%2Fapp%2Freservas');
    await page.getByRole('button', { name: 'Aceptar y continuar' }).click();
    await expect(page.getByText('Marca la casilla para aceptar los términos; sin ella no podemos activar tus reservas.')).toBeVisible();
    expect(vistas.aceptar).toHaveLength(0);
    await casilla(page).check();
    await page.getByRole('button', { name: 'Aceptar y continuar' }).click();
    await expect(page).toHaveURL(/\/app\/reservas\/?\?aviso=textos-aceptados/);
    expect(vistas.aceptar[0].cuerpo).toEqual({ contexto: 'registro', textos: [{ tipo: 'terminos_uso', version: '1.0.0' }, { tipo: 'politica_privacidad', version: '1.2.3' }] });
  });

  test('"Ahora no" sigue sin registrar nada', async ({ page }) => {
    const vistas = await montar(page, { perfilR: PENDIENTES });
    await page.goto('/acceso/textos/?volver=%2Fapp%2Freservas');
    await page.getByRole('button', { name: 'Ahora no' }).click();
    await expect(page).toHaveURL(/\/app\/reservas\/?$/);
    expect(vistas.aceptar).toHaveLength(0);
  });

  test('reaceptación: título y texto de actualización', async ({ page }) => {
    await montar(page, { perfilR: perfilApi({ pendientes: [P('terminos_uso', '1.0.0', 'actualizado')] }) });
    await page.goto('/acceso/textos/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Términos actualizados');
    await expect(page.getByText('Tus reservas actuales siguen con las condiciones que aceptaste.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'Acepto los Términos de uso (versión 1.0.0).' })).not.toBeChecked();
  });

  test('agrupación: la declaración lleva su casilla aparte', async ({ page }) => {
    const vistas = await montar(page, { perfilR: perfilApi({ pendientes: [P('terminos_uso', '1.0.0'), P('declaracion_agrupacion', '1.0.0')] }) });
    await page.goto('/acceso/textos/');
    await page.getByRole('checkbox', { name: /Acepto los Términos de uso/ }).check();
    await page.getByRole('button', { name: 'Aceptar y continuar' }).click();
    await expect(page.getByText('Marca la casilla para registrar la agrupación.')).toBeVisible();
    await page.getByRole('checkbox', { name: /Declaro que represento a la agrupación/ }).check();
    await page.getByRole('button', { name: 'Aceptar y continuar' }).click();
    await expect(page).toHaveURL(/\/app\/\?aviso=textos-aceptados/);
    expect(vistas.aceptar[0].cuerpo.textos.map((x) => x.tipo)).toEqual(['terminos_uso', 'declaracion_agrupacion']);
  });

  test('sin pendientes vuelve directo', async ({ page }) => {
    await montar(page);
    await page.goto('/acceso/textos/?volver=%2Fapp%2Freservas');
    await expect(page).toHaveURL(/\/app\/reservas\/?$/);
  });

  test('sin sesión va al acceso y conserva el destino', async ({ page }) => {
    await montar(page, { sesion: false });
    await page.goto('/acceso/textos/?volver=%2Fapp%2Freservas');
    await expect(page).toHaveURL(/\/acceso\/?\?volver=%2Facceso%2Ftextos%2F%3Fvolver%3D%252Fapp%252Freservas/);
  });

  test('volver ajeno se ignora', async ({ page }) => {
    await montar(page);
    await page.goto('/acceso/textos/?volver=https%3A%2F%2Fmal.com');
    await expect(page).toHaveURL(/\/app\/$/);
  });

  test('409 texto_desactualizado repinta con la versión nueva y desmarca', async ({ page }) => {
    const vistas = await montar(page, { perfilR: PENDIENTES });
    let primera = true;
    await page.unroute(`${API}/textos-legales`);
    await page.route(`${API}/textos-legales`, (r) => r.fulfill(json(200, primera ? TEXTOS : [t('terminos_uso', '1.1.0', { registro: 'Reglas nuevas.' }), TEXTOS[1]])));
    await page.unroute(`${API}/aceptaciones`);
    await page.route(`${API}/aceptaciones`, (r) => { primera = false; return r.fulfill(json(409, { error: { codigo: 'texto_desactualizado', mensaje: 'x', detalles: { vigente: { tipo: 'terminos_uso', version: '1.1.0' } } } })); });
    await page.goto('/acceso/textos/');
    await casilla(page).check();
    await page.getByRole('button', { name: 'Aceptar y continuar' }).click();
    await expect(page.getByText('Reglas nuevas.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /versión 1\.1\.0/ })).not.toBeChecked();
    await expect(page.getByText('Las condiciones cambiaron. Lee la versión 1.1.0 y vuelve a marcar la casilla.')).toBeVisible();
    expect(vistas.aceptar).toHaveLength(0);
  });

  for (const [nombre, resp, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'x')), 'No pudimos cargar los textos.'],
    ['red', (r) => r.abort(), 'No pudimos cargar los textos.'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>x</p>' }), 'No pudimos cargar los textos.'],
  ]) {
    test(`los textos no cargan (${nombre}): reintentar y acción deshabilitada`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page, { perfilR: PENDIENTES });
      await page.unroute(`${API}/textos-legales`);
      await page.route(`${API}/textos-legales`, resp);
      await page.goto('/acceso/textos/');
      await expect(page.getByText(texto)).toBeVisible();
      await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Aceptar y continuar' })).toBeDisabled();
      await expect(page.getByText('Necesitamos mostrarte las condiciones antes de continuar.')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Ahora no' })).toBeEnabled();
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('el perfil falla con 503: aviso con reintentar', async ({ page }) => {
    await montar(page, { perfilR: errorApi(503, 'x') });
    await page.goto('/acceso/textos/');
    await expect(page.getByText('No pudimos cargar tus datos.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  });

  test.describe('foco', () => {
    const enFoco = (page) => page.evaluate(() => { const a = document.activeElement; return { etiqueta: a.tagName, texto: a.textContent.trim().slice(0, 40) }; });
    test('Reintentar con éxito deja el foco en el título', async ({ page }) => {
      await montar(page, { perfilR: PENDIENTES });
      let fallar = true;
      await page.unroute(`${API}/textos-legales`);
      await page.route(`${API}/textos-legales`, (r) => (fallar ? r.fulfill(errorApi(503, 'x')) : r.fulfill(json(200, TEXTOS))));
      await page.goto('/acceso/textos/');
      await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
      fallar = false;
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(casilla(page)).toBeVisible();
      expect(await enFoco(page)).toMatchObject({ etiqueta: 'H1' });
    });
    test('el error de textos lleva el foco al aviso, también tras Reintentar', async ({ page }) => {
      await montar(page, { perfilR: PENDIENTES, textos: errorApi(503, 'x') });
      await page.goto('/acceso/textos/');
      await expect(page.getByText('No pudimos cargar los textos.')).toBeVisible();
      expect(await enFoco(page)).toMatchObject({ texto: expect.stringContaining('No pudimos cargar los textos.') });
      await page.screenshot({ path: 'pruebas/capturas/acceso-textos-error-foco-1440.png', fullPage: true });
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByText('No pudimos cargar los textos.')).toBeVisible();
      expect(await enFoco(page)).toMatchObject({ texto: expect.stringContaining('No pudimos cargar los textos.') });
    });
    test('el error de perfil lleva el foco al aviso, también tras Reintentar', async ({ page }) => {
      await montar(page, { perfilR: errorApi(503, 'x') });
      await page.goto('/acceso/textos/');
      await expect(page.getByText('No pudimos cargar tus datos.')).toBeVisible();
      expect(await enFoco(page)).toMatchObject({ texto: expect.stringContaining('No pudimos cargar tus datos.') });
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByText('No pudimos cargar tus datos.')).toBeVisible();
      expect(await enFoco(page)).toMatchObject({ texto: expect.stringContaining('No pudimos cargar tus datos.') });
    });
  });

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('explica qué falta y no deja la carga indefinida', async ({ page }) => {
      await page.goto('/acceso/textos/');
      expect(await page.content()).toContain('Esta página necesita JavaScript');
      await expect(page.locator('bugalu-aceptacion [data-salida]')).toBeHidden();
      await expect(page.locator('bugalu-aceptacion noscript .aviso-titulo')).toBeVisible();
    });
  });
});

// --- Reserva ---
const R1 = '11111111-1111-4111-8111-111111111111';
const INI = '2026-11-19T10:00:00-05:00';
const ELECCION = `inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`;
const PASO4 = `/reservar/confirmar/?${ELECCION}`;
const PASO3 = `/reservar/cuenta/?${ELECCION}`;
const SIM = { lineas: [{ concepto: 'Grabación', cantidad: '2.0', unidad: 'hora', monto: '240.00' }], recargos: [], total: '240.00', anticipo: '120.00', porcentaje_adelanto: 50 };
const RESERVA = { id: R1, folio: 'R-2026-00013', estado: 'pre_reservada', inicio: INI, fin: '2026-11-19T12:00:00-05:00', sala: 'La Molina', servicio: 'Grabación', especialistas: [], precio: SIM, cuotas: [], vence_pago: '2026-11-17T10:00:00-05:00' };

async function montarReserva(page, { crear = (r) => r.fulfill(json(201, RESERVA)), ...opciones } = {}) {
  const vistas = await montar(page, opciones);
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [{ id: 'sala-1', nombre: 'La Molina' }])));
  await page.route(`${API}/impuestos`, (r) => r.fulfill(json(200, { porcentaje_igv: '18.00', precios_incluyen_igv: true })));
  await page.route(`${API}/servicios`, (r) => r.fulfill(json(200, [{ id: 's1', nombre: 'Grabación', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '0.00', especialistas_por_defecto: [], activo: true }])));
  await page.route(`${API}/especialistas`, (r) => r.fulfill(json(200, [])));
  await page.route(`${API}/simulaciones`, (r) => r.fulfill(json(200, SIM)));
  await page.route(`${API}/reservas/${R1}`, (r) => r.fulfill(json(200, RESERVA)));
  vistas.crear = await simular(page, 'POST', '/reservas', crear);
  vistas.parches = await simular(page, 'PATCH', '/perfil', (r) => r.fulfill(perfilApi()));
  return vistas;
}
const reservar = (page) => page.getByRole('button', { name: 'Confirmar reserva' });
const condiciones = (page) => page.getByRole('checkbox', { name: /Acepto las Condiciones de contratación \(versión 2\.0\.0\)/ });
const avisoRes = (page) => page.locator('bugalu-reserva [data-avisos] .aviso');

test.describe('04 Confirmar con condiciones', () => {
  test('envía version_condiciones y muestra el resumen con su enlace', async ({ page }) => {
    const consola = vigilarConsola(page);
    const vistas = await montarReserva(page);
    await page.goto(PASO4);
    await expect(page.getByText('Pagas el adelanto para confirmar.')).toBeVisible();
    await expect(page.getByRole('link', { name: /Leer el texto completo \(versión 2\.0\.0\)/ })).toHaveAttribute('href', '/legal/condiciones-de-contratacion/?version=2.0.0');
    await expect(condiciones(page)).not.toBeChecked();
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/reservar-04-condiciones-1440.png', fullPage: true });
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page).toHaveURL(new RegExp(`/reservar/listo/\\?id=${R1}`));
    expect(vistas.crear[0].cuerpo).toMatchObject({ id_servicio: 's1', version_condiciones: '2.0.0' });
    expect(consola).toEqual([]);
  });

  test('sin marcar la casilla no se envía', async ({ page }) => {
    const vistas = await montarReserva(page);
    await page.goto(PASO4);
    await reservar(page).click();
    await expect(page.getByText('Marca la casilla para aceptar las condiciones; sin ella no podemos registrar tu reserva.')).toBeVisible();
    await expect(condiciones(page)).toHaveAttribute('aria-invalid', 'true');
    expect(vistas.crear).toHaveLength(0);
  });

  test('las condiciones no cargan: la acción queda deshabilitada con su motivo', async ({ page }) => {
    await montarReserva(page, { textos: errorApi(503, 'x') });
    await page.goto(PASO4);
    await expect(reservar(page)).toBeDisabled();
    await expect(page.getByText('Necesitamos mostrarte las condiciones antes de continuar.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
  });

  for (const [nombre, perfilR] of [
    ['datos incompletos', perfilApi({ datos_para_reservar: false })],
    ['textos pendientes', PENDIENTES],
    ['menor', perfilApi({ es_menor: true })],
  ]) {
    test(`con ${nombre} va al paso 03 con la misma elección`, async ({ page }) => {
      await montarReserva(page, { perfilR });
      await page.goto(PASO4);
      await expect(page).toHaveURL(new RegExp(`/reservar/cuenta/\\?${ELECCION.replace(/[?.]/g, '\\$&')}`));
    });
  }

  for (const [codigo, detalles, destino, texto] of [
    ['reaceptacion_requerida', { textos: [{ tipo: 'terminos_uso', version: '1.0.0' }] }, /\/reservar\/cuenta\/\?.*aviso=textos-pendientes/, 'Antes de confirmar necesitamos que aceptes los términos actualizados.'],
    ['perfil_incompleto', { campos: ['documento'] }, /\/reservar\/cuenta\/\?.*aviso=faltan-datos/, 'Antes de confirmar necesitamos tus datos.'],
  ]) {
    test(`409 ${codigo} lleva a donde se resuelve`, async ({ page }) => {
      let falto = false;
      await montarReserva(page, { crear: (r) => { falto = true; return r.fulfill(json(409, { error: { codigo, mensaje: 'x', detalles } })); } });
      await page.unroute(`${API}/perfil`);
      await page.route(`${API}/perfil`, (r) => r.fulfill(falto ? perfilApi({ datos_para_reservar: false, telefono: null }) : perfilApi()));
      await page.goto(PASO4);
      await condiciones(page).check();
      await reservar(page).click();
      await expect(page).toHaveURL(destino);
      if (texto) await expect(page.getByText(texto)).toBeVisible();
    });
  }

  for (const [codigo, detalles] of [
    ['reaceptacion_requerida', { textos: [{ tipo: 'terminos_uso', version: '1.0.0' }] }],
    ['perfil_incompleto', { campos: ['documento'] }],
    ['autorizacion_menor_pendiente', {}],
  ]) {
    test(`409 ${codigo}: el detalle escrito sobrevive y vuelve al paso 04`, async ({ page }) => {
      let falto = false;
      const vistas = await montarReserva(page, { crear: (r) => { falto = true; return r.fulfill(json(409, { error: { codigo, mensaje: 'x', detalles } })); } });
      // Tras el 409 el perfil falta algo: el paso 03 se queda quieto en vez de saltar solo al 04.
      await page.unroute(`${API}/perfil`);
      await page.route(`${API}/perfil`, (r) => r.fulfill(falto ? perfilApi({ datos_para_reservar: false, telefono: null }) : perfilApi()));
      await page.goto(PASO4);
      await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
      await condiciones(page).check();
      await reservar(page).click();
      await expect(page).toHaveURL(/\/reservar\/cuenta\//);
      if (codigo === 'reaceptacion_requerida') await page.screenshot({ path: 'pruebas/capturas/reservar-03-textos-pendientes-1440.png', fullPage: true });
      await expect(page.locator('bugalu-reserva [data-formulario-cuenta]:not([hidden]), bugalu-reserva [data-cuenta-estado] .aviso').first()).toBeVisible();
      falto = false;
      await page.goto(PASO4);
      await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('Voz y guitarra');
      expect(vistas.crear).toHaveLength(1);
    });
  }

  test('el detalle se borra al reservar con éxito', async ({ page }) => {
    await montarReserva(page);
    await page.goto(PASO4);
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page).toHaveURL(/\/reservar\/listo\//);
    await page.goto(PASO4);
    await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('');
  });

  test('otra elección (duración) no hereda el detalle', async ({ page }) => {
    await montarReserva(page);
    await page.goto(PASO4);
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    await page.goto(PASO4.replace('duracion=120', 'duracion=60'));
    await expect(condiciones(page)).toBeVisible(); // el detalle se restaura al cargar el paso
    await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('');
    await page.goto(PASO4);
    await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('Voz y guitarra');
  });

  test('cerrar sesión borra el detalle guardado', async ({ page }) => {
    await montarReserva(page);
    await page.goto(PASO4);
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    expect(await page.evaluate(() => Object.keys(sessionStorage).length)).toBeGreaterThan(0);
    await page.goto('/app/perfil');
    await page.locator('.cabecera-menu > summary').click();
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await page.waitForURL('**/acceso?aviso=sesion-cerrada');
    expect(await page.evaluate(() => Object.keys(sessionStorage).filter((k) => k.startsWith('bugalu:reserva-detalle')))).toEqual([]);
  });

  test('camino real de reaceptacion_requerida: 409, acepta en el 03, vuelve al 04 con el detalle y reserva con él', async ({ page }) => {
    let falto = false;
    const vistas = await montarReserva(page, { crear: (r) => { if (falto) return r.fulfill(json(201, RESERVA)); falto = true; return r.fulfill(json(409, { error: { codigo: 'reaceptacion_requerida', mensaje: 'x', detalles: { textos: [{ tipo: 'terminos_uso', version: '1.0.0' }] } } })); } });
    await page.unroute(`${API}/perfil`);
    await page.route(`${API}/perfil`, (r) => r.fulfill(falto && !vistas.aceptar.length ? perfilApi({ datos_para_reservar: false, pendientes: [P('terminos_uso', '1.0.0', 'actualizado')] }) : perfilApi()));
    await page.goto(PASO4);
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page).toHaveURL(/\/reservar\/cuenta\/\?.*aviso=textos-pendientes/);
    await expect(page.getByText('Antes de confirmar necesitamos que aceptes los términos actualizados.')).toBeVisible();
    await page.getByRole('checkbox', { name: /Acepto los Términos de uso/ }).check();
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page).toHaveURL(/\/reservar\/confirmar\//);
    await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('Voz y guitarra');
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page).toHaveURL(/\/reservar\/listo\//);
    expect(vistas.crear).toHaveLength(2);
    expect(vistas.crear[1].cuerpo.detalle).toBe('Voz y guitarra');
  });

  test('409 autorizacion_menor_pendiente muestra el mensaje de la spec', async ({ page }) => {
    await montarReserva(page, { crear: (r) => r.fulfill(errorApi(409, 'autorizacion_menor_pendiente')) });
    await page.goto(PASO4);
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page).toHaveURL(/\/reservar\/cuenta\//);
    await expect(page.getByText('Aún no puedes reservar en línea')).toBeVisible();
  });

  test('409 texto_desactualizado recarga la versión, desmarca y conserva la elección', async ({ page }) => {
    let nueva = false;
    const vistas = await montarReserva(page, { crear: (r) => { nueva = true; return r.fulfill(json(409, { error: { codigo: 'texto_desactualizado', mensaje: 'x', detalles: { vigente: { tipo: 'condiciones_contratacion', version: '2.1.0' } } } })); } });
    await page.unroute(`${API}/textos-legales`);
    await page.route(`${API}/textos-legales`, (r) => r.fulfill(json(200, nueva ? [t('condiciones_contratacion', '2.1.0', { reserva: 'Condiciones nuevas.' })] : TEXTOS)));
    await page.goto(PASO4);
    await page.getByLabel('Qué necesitas (opcional)').fill('Voz y guitarra');
    await condiciones(page).check();
    await reservar(page).click();
    await expect(page.getByText('Condiciones nuevas.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /versión 2\.1\.0/ })).not.toBeChecked();
    await expect(page.getByText('Las condiciones cambiaron. Lee la versión 2.1.0 y vuelve a marcar la casilla.')).toBeVisible();
    await expect(page.getByLabel('Qué necesitas (opcional)')).toHaveValue('Voz y guitarra');
    expect(vistas.crear).toHaveLength(1);
    await page.getByRole('checkbox', { name: /versión 2\.1\.0/ }).check();
    await reservar(page).click();
    expect(vistas.crear).toHaveLength(2);
    expect(vistas.crear[1].cuerpo.version_condiciones).toBe('2.1.0');
  });
});

test.describe('03 Completa tus datos', () => {
  const FALTAN = perfilApi({ datos_para_reservar: false, documento: null, telefono: null, pendientes: [P('terminos_uso', '1.0.0'), P('politica_privacidad', '1.2.3')] });

  for (const tm of tamanos) {
    test(`muestra solo lo que falta a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montarReserva(page, { perfilR: FALTAN });
      await page.goto(`${PASO3}&aviso=faltan-datos`);
      await expect(page).toHaveTitle(/^Completa tus datos · Paso 3 de 5 · Reservar sala/);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Completa tus datos');
      await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
      await expect(page.getByText('PASO 03 / 05')).toBeVisible();
      await expect(page.getByText('Antes de confirmar necesitamos tus datos.')).toBeVisible();
      await expect(page.getByLabel('Nombre')).toHaveCount(0); // ya lo tiene
      await expect(page.getByLabel('Tipo de documento')).toBeVisible();
      await expect(page.getByLabel('Número')).toBeVisible();
      await expect(page.getByLabel(/Teléfono/)).toBeVisible();
      await expect(page.getByRole('checkbox', { name: 'Soy menor de 18 años' })).not.toBeChecked();
      await expect(page.getByRole('checkbox', { name: /Acepto los Términos de uso/ })).not.toBeChecked();
      await expect(page.getByRole('link', { name: 'Anterior' })).toHaveAttribute('href', new RegExp('^/reservar/servicio/\\?'));
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/reservar-03-cuenta-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }

  test('guarda datos y aceptación y sigue al paso 04', async ({ page }) => {
    const vistas = await montarReserva(page, { perfilR: FALTAN });
    await page.goto(PASO3);
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page.getByText('Elige el tipo de documento.')).toBeVisible();
    await page.getByLabel('Tipo de documento').selectOption('dni');
    await page.getByLabel('Número').fill('123');
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page.getByText('Escribe los 8 dígitos de tu DNI.')).toBeVisible();
    await expect(page.getByText('Escribe tu teléfono; lo necesitas para reservar.')).toBeVisible();
    await page.getByLabel('Número').fill('12345678');
    await page.getByLabel(/Teléfono/).fill('987654321');
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page.getByText('Marca la casilla para aceptar los términos; sin ella no podemos activar tus reservas.')).toBeVisible();
    expect(vistas.parches).toHaveLength(0);
    await page.getByRole('checkbox', { name: /Acepto los Términos de uso/ }).check();
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page).toHaveURL(new RegExp('/reservar/confirmar/\\?'));
    expect(vistas.parches[0].cuerpo).toEqual({ documento: { tipo: 'dni', numero: '12345678' }, telefono: '987654321' });
    expect(vistas.aceptar[0].cuerpo).toEqual({ contexto: 'registro', textos: [{ tipo: 'terminos_uso', version: '1.0.0' }, { tipo: 'politica_privacidad', version: '1.2.3' }] });
    expect(new URL(page.url()).searchParams.get('servicio')).toBe('s1');
  });

  test('con todo en regla se salta al paso 04', async ({ page }) => {
    await montarReserva(page);
    await page.goto(PASO3);
    await expect(page).toHaveURL(new RegExp('/reservar/confirmar/\\?'));
  });

  test('sin sesión va al acceso', async ({ page }) => {
    await montarReserva(page, { sesion: false });
    await page.goto(PASO3);
    await expect(page).toHaveURL(/\/acceso\/?\?volver=/);
  });

  test('menor: aviso crítico con el contacto y sin formulario', async ({ page }) => {
    await montarReserva(page, { perfilR: perfilApi({ es_menor: true }) });
    await page.goto(PASO3);
    await expect(page.getByText('Aún no puedes reservar en línea')).toBeVisible();
    await expect(page.getByText('Escríbenos a hola@bugalu.studio')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Volver al inicio' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Guardar y continuar' })).toHaveCount(0);
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/reservar-03-menor-1440.png', fullPage: true });
  });

  test('marcar menor y guardar muestra el aviso crítico', async ({ page }) => {
    const vistas = await montarReserva(page, { perfilR: FALTAN });
    await page.unroute(`${API}/perfil`);
    await page.route(`${API}/perfil`, (r) => r.request().method() === 'PATCH' ? r.fulfill(perfilApi({ es_menor: true })) : r.fulfill(FALTAN));
    await page.goto(PASO3);
    await page.getByRole('checkbox', { name: 'Soy menor de 18 años' }).check();
    await page.getByRole('button', { name: 'Guardar y continuar' }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'Aún no puedes reservar en línea' })).toBeVisible();
    expect(vistas.aceptar).toHaveLength(0);
  });

  for (const [nombre, resp, texto] of [
    ['401', (r) => r.fulfill(errorApi(401, 'x')), 'Tu sesión caducó. Inicia sesión para continuar; tus datos se conservan.'],
    ['503', (r) => r.fulfill(errorApi(503, 'x')), 'El servicio no responde. No se guardó nada; inténtalo en unos minutos.'],
    ['red', (r) => r.abort(), 'Sin conexión. No se guardó nada; revisa tu red.'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>x</p>' }), 'Algo salió mal. Inténtalo de nuevo.'],
  ]) {
    test(`falla al guardar (${nombre}) y conserva lo escrito`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montarReserva(page, { perfilR: FALTAN });
      await page.unroute(`${API}/perfil`);
      await page.route(`${API}/perfil`, (r) => r.request().method() === 'PATCH' ? resp(r) : r.fulfill(FALTAN));
      await page.goto(PASO3);
      await page.getByLabel('Número').fill('12345678');
      await page.getByLabel('Tipo de documento').selectOption('dni');
      await page.getByLabel(/Teléfono/).fill('987654321');
      await page.getByRole('checkbox', { name: /Acepto los Términos de uso/ }).check();
      await page.getByRole('button', { name: 'Guardar y continuar' }).click();
      await expect(avisoRes(page)).toContainText(texto);
      await expect(page.getByLabel('Número')).toHaveValue('12345678');
      await expect(page.getByRole('checkbox', { name: /Acepto los Términos de uso/ })).toBeChecked();
      expect(consola).toEqual([]);
    });
  }
});

// --- Pago ---
test('pago: resumen de registro de un pago con enlace a las condiciones, sin casilla', async ({ page }) => {
  const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  await montar(page);
  await simular(page, 'GET', `/reservas/${R1}`, json(200, { ...RESERVA, cuotas: [{ id: C1, hito: 'al_reservar', monto: '120.00', estado: 'pendiente', pagable: true, pagos: [] }] }));
  await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }]));
  await page.goto(`/app/reservas/pagar?id=${R1}&cuota=${C1}`);
  const bloque = page.locator('.resumen-legal-lectura');
  await expect(bloque.getByRole('heading', { name: 'Registro de un pago' })).toBeVisible();
  await expect(bloque.getByText('Revisamos tu pago a mano.')).toBeVisible();
  await expect(bloque.getByRole('link', { name: /Condiciones de contratación/ })).toHaveAttribute('href', '/legal/condiciones-de-contratacion/?version=2.0.0');
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pago-resumen-legal-1440.png', fullPage: true });
});

// --- Aviso en LayoutApp y destino tras el ingreso ---
test('app: aviso de textos pendientes con enlace a revisar, sin rol vivo ni botón de cierre', async ({ page }) => {
  await montar(page, { perfilR: PENDIENTES });
  await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, [])));
  await page.goto('/app/reservas/');
  const aviso = page.locator('main .aviso').filter({ hasText: 'Tienes textos por aceptar' });
  await expect(aviso).toBeVisible();
  await expect(aviso).toContainText('Mientras tanto no puedes hacer reservas nuevas. Puedes ver, pagar y cancelar las que ya tienes.');
  await expect(aviso).not.toHaveAttribute('role', /.+/);
  await expect(aviso.getByRole('button')).toHaveCount(0);
  await expect(aviso.getByRole('link', { name: 'Revisar y aceptar' })).toHaveAttribute('href', '/acceso/textos?volver=%2Fapp%2Freservas%2F');
  await page.screenshot({ path: 'pruebas/capturas/app-textos-pendientes-1440.png' });
});

test('app: sin pendientes no hay aviso', async ({ page }) => {
  await montar(page);
  await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, [])));
  await page.goto('/app/reservas/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.getByText('Tienes textos por aceptar')).toHaveCount(0);
});

// --- Cobertura permanente (auditoria B, ronda 1): axe en ambos anchos, textos hostiles y fallos del resumen del pago ---
const HOSTIL = '<img src=x onerror="window.__xss = 1"><b>negrita</b> <script>window.__xss = 2</script>';
const sinHtml = async (page, ambito) => {
  await expect(ambito.locator('img, b, script')).toHaveCount(0);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
};

for (const tm of tamanos) {
  test(`04 Confirmar: sin violaciones de axe a ${tm.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montarReserva(page);
    await page.goto(PASO4);
    await expect(page.getByText('Pagas el adelanto para confirmar.')).toBeVisible();
    await sinViolaciones(page);
  });
  test(`pago: resumen legal sin violaciones de axe a ${tm.nombre}`, async ({ page }) => {
    const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montar(page);
    await simular(page, 'GET', `/reservas/${R1}`, json(200, { ...RESERVA, cuotas: [{ id: C1, hito: 'al_reservar', monto: '120.00', estado: 'pendiente', pagable: true, pagos: [] }] }));
    await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }]));
    await page.goto(`/app/reservas/pagar?id=${R1}&cuota=${C1}`);
    await expect(page.getByText('Revisamos tu pago a mano.')).toBeVisible();
    await sinViolaciones(page);
  });
  test(`app: aviso de textos pendientes sin violaciones de axe a ${tm.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montar(page, { perfilR: PENDIENTES });
    await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, [])));
    await page.goto('/app/reservas/');
    await expect(page.getByText('Tienes textos por aceptar')).toBeVisible();
    await sinViolaciones(page);
  });
  test(`libro de reclamaciones sin violaciones de axe a ${tm.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await page.goto('/libro-de-reclamaciones/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await sinViolaciones(page);
  });
}

test.describe('resúmenes con HTML hostil se pintan como texto', () => {
  const textosHostiles = TEXTOS.map((x) => ({ ...x, resumenes: Object.fromEntries(Object.entries(x.resumenes).map(([k]) => [k, `${HOSTIL} resumen ${k}`])) }));
  test('/acceso/textos', async ({ page }) => {
    await montar(page, { perfilR: PENDIENTES, textos: json(200, textosHostiles) });
    await page.goto('/acceso/textos/');
    await expect(page.getByText('<img src=x', { exact: false }).first()).toBeVisible();
    await sinHtml(page, page.locator('bugalu-aceptacion'));
  });
  test('04 Confirmar', async ({ page }) => {
    await montarReserva(page, { textos: json(200, textosHostiles) });
    await page.goto(PASO4);
    await expect(page.getByText('<img src=x', { exact: false }).first()).toBeVisible();
    await sinHtml(page, page.locator('bugalu-reserva'));
  });
  test('pago', async ({ page }) => {
    const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    await montar(page, { textos: json(200, textosHostiles) });
    await simular(page, 'GET', `/reservas/${R1}`, json(200, { ...RESERVA, cuotas: [{ id: C1, hito: 'al_reservar', monto: '120.00', estado: 'pendiente', pagable: true, pagos: [] }] }));
    await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }]));
    await page.goto(`/app/reservas/pagar?id=${R1}&cuota=${C1}`);
    await expect(page.locator('.resumen-legal-lectura').getByText('<img src=x', { exact: false })).toBeVisible();
    await sinHtml(page, page.locator('.resumen-legal-lectura'));
  });
});

// El resumen del pago es un extra: si no carga, se puede pagar igual y no hay error de consola.
for (const [nombre, resp] of [
  ['401', (r) => r.fulfill(errorApi(401, 'no_autenticado'))],
  ['403', (r) => r.fulfill(errorApi(403, 'sin_permiso'))],
  ['503', (r) => r.fulfill(errorApi(503, 'x'))],
  ['red', (r) => r.abort()],
  ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>x</p>' })],
]) {
  test(`pago: el resumen legal falla (${nombre}) y el pago sigue disponible`, async ({ page }) => {
    const consola = vigilarConsola(page);
    const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    await montar(page);
    await page.unroute(`${API}/textos-legales`);
    await page.route(`${API}/textos-legales`, resp);
    await simular(page, 'GET', `/reservas/${R1}`, json(200, { ...RESERVA, cuotas: [{ id: C1, hito: 'al_reservar', monto: '120.00', estado: 'pendiente', pagable: true, pagos: [] }] }));
    await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }]));
    await page.goto(`/app/reservas/pagar?id=${R1}&cuota=${C1}`);
    await expect(page.getByText('Yape al 999 888 777').first()).toBeVisible();
    await expect(page.locator('.resumen-legal-lectura')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}
