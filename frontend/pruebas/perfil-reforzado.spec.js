// RF-17 (CA-06, CA-07, CA-12, CA-13, CA-14): perfil reforzado, consentimientos e historial de aceptaciones. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { t, TEXTOS, perfilApi } from './ayudas-rf17.js';

const ACEPTACIONES = [
  { id: 'a1', tipo: 'terminos_uso', version: '1.0.0', contexto: 'registro', id_operacion: 'o1', aceptada_en: '2026-11-10T15:00:00Z', retirada_en: null },
  { id: 'a2', tipo: 'politica_privacidad', version: '1.2.3', contexto: 'promociones', id_operacion: 'o2', aceptada_en: '2026-11-12T15:00:00Z', retirada_en: '2026-12-03T15:00:00Z' },
];

async function montar(page, { perfilR = perfilApi(), mias = json(200, []) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  await conSesion(page);
  await silenciarApi(page);
  const vistas = {};
  await page.route(`${API}/perfil`, (r) => (r.request().method() === 'GET' ? r.fulfill(perfilR) : r.fallback()));
  vistas.parches = await simular(page, 'PATCH', '/perfil', (r) => r.fulfill(perfilApi()));
  vistas.aceptar = await simular(page, 'POST', '/aceptaciones', json(201, []));
  vistas.consentimientos = await simular(page, 'PUT', '/perfil/consentimientos', (r) => r.fulfill(json(200, { promociones_correo: true, promociones_whatsapp: false, fotos_videos: false, excluir_material: false })));
  await page.route(`${API}/textos-legales`, (r) => r.fulfill(json(200, TEXTOS)));
  await page.route(`${API}/aceptaciones/mias`, (r) => r.fulfill(mias));
  return vistas;
}
const guardar = (page) => page.getByRole('button', { name: 'Guardar cambios' });

test.describe('/app/perfil reforzado', () => {
  for (const tm of tamanos) {
    test(`muestra modalidad, documento, domicilio y redes a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { perfilR: perfilApi({ redes: [{ red: 'instagram', valor: '@ana' }], domicilio: 'Av. Lima 123', datos_para_reservar: false, telefono: null }) });
      await page.goto('/app/perfil');
      await expect(page.getByRole('heading', { level: 2, name: /Identidad/ })).toBeVisible();
      await expect(page.getByRole('radio', { name: /Individual/ })).toBeChecked();
      await expect(page.getByRole('radio', { name: /Agrupación/ })).not.toBeChecked();
      await expect(page.getByLabel('Tipo de documento')).toHaveValue('dni');
      await expect(page.getByLabel('Número')).toHaveValue('12345678');
      await expect(page.getByRole('textbox', { name: 'Domicilio' })).toHaveValue('Av. Lima 123');
      await expect(page.getByLabel('Red', { exact: true })).toHaveValue('instagram');
      await expect(page.getByLabel(/Usuario o enlace/)).toHaveValue('@ana');
      await expect(page.getByRole('heading', { name: /Integrantes/ })).toHaveCount(0);
      await expect(page.locator('.aviso-titulo', { hasText: 'Para reservar te falta: teléfono.' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Privacidad y textos aceptados' })).toHaveAttribute('href', '/app/perfil/privacidad/');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/perfil-reforzado-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }

  test('guarda documento, domicilio y redes con el contrato', async ({ page }) => {
    const vistas = await montar(page, { perfilR: perfilApi({ documento: null }) });
    await page.goto('/app/perfil');
    await page.getByLabel('Número').fill('1234');
    await guardar(page).click();
    await expect(page.getByText('Elige el tipo de documento.')).toBeVisible();
    await page.getByLabel('Tipo de documento').selectOption('dni');
    await guardar(page).click();
    await expect(page.getByText('Escribe los 8 dígitos de tu DNI.')).toBeVisible();
    await page.getByLabel('Tipo de documento').selectOption('pasaporte');
    await page.getByLabel('Número').fill('ab 12345');
    await page.getByRole('textbox', { name: 'Domicilio' }).fill('Av. Lima 123');
    await page.getByRole('button', { name: 'Añadir red' }).click();
    await guardar(page).click();
    await expect(page.getByText('Escribe tu usuario o el enlace.')).toBeVisible();
    await page.getByLabel(/Usuario o enlace/).fill('@ana');
    await guardar(page).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'Cambios guardados.' })).toBeVisible();
    expect(vistas.parches[0].cuerpo).toMatchObject({ nombre: 'Ana Pérez', documento: { tipo: 'pasaporte', numero: 'AB12345' }, domicilio: 'Av. Lima 123', redes: [{ red: 'instagram', valor: '@ana' }] });
    expect(vistas.parches[0].cuerpo).not.toHaveProperty('modalidad');
  });

  test('redes: máximo 5 y se pueden quitar', async ({ page }) => {
    await montar(page);
    await page.goto('/app/perfil');
    for (let i = 0; i < 5; i++) await page.getByRole('button', { name: 'Añadir red' }).click();
    await expect(page.getByRole('button', { name: 'Añadir red' })).toBeHidden();
    await expect(page.getByText('Máximo 5 redes.')).toBeVisible();
    await page.getByRole('button', { name: 'Quitar red' }).first().click();
    await expect(page.getByRole('button', { name: 'Añadir red' })).toBeVisible();
    await expect(page.getByLabel('Red', { exact: true })).toHaveCount(4);
  });

  test('agrupación: aparecen integrantes y la declaración; se acepta antes de guardar', async ({ page }) => {
    const orden = [];
    const vistas = await montar(page);
    await page.unroute(`${API}/aceptaciones`);
    await page.route(`${API}/aceptaciones`, (r) => { orden.push('aceptar'); vistas.aceptar.push({ cuerpo: r.request().postDataJSON() }); return r.fulfill(json(201, [])); });
    await page.unroute(`${API}/perfil`);
    await page.route(`${API}/perfil`, (r) => { if (r.request().method() === 'PATCH') { orden.push('perfil'); vistas.parches.push({ cuerpo: r.request().postDataJSON() }); return r.fulfill(perfilApi({ modalidad: 'agrupacion' })); } return r.fulfill(perfilApi()); });
    await page.goto('/app/perfil');
    await page.getByRole('radio', { name: /Agrupación/ }).check();
    await expect(page.getByRole('status').filter({ hasText: 'Añade a los integrantes de la agrupación' })).toBeAttached();
    await expect(page.getByRole('heading', { level: 2, name: /Integrantes/ })).toBeVisible();
    await expect(page.getByText('Representas a tu agrupación.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /Declaro que represento a la agrupación/ })).not.toBeChecked();
    await guardar(page).click();
    await expect(page.getByText('Añade al menos un integrante.')).toBeVisible();
    await page.getByRole('button', { name: 'Añadir integrante' }).click();
    await guardar(page).click();
    await expect(page.getByText('Escribe el nombre del integrante.')).toBeVisible();
    await expect(page.getByText('Escribe qué hace en la agrupación, por ejemplo, voz.')).toBeVisible();
    await page.getByLabel('Nombre del integrante').fill('Luis');
    await page.getByLabel(/Rol/).fill('Voz');
    await guardar(page).click();
    await expect(page.getByText('Marca la casilla para registrar la agrupación.')).toBeVisible();
    expect(orden).toEqual([]);
    await page.getByRole('checkbox', { name: /Declaro que represento a la agrupación/ }).check();
    await guardar(page).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'Cambios guardados.' })).toBeVisible();
    expect(orden).toEqual(['aceptar', 'perfil']);
    expect(vistas.aceptar[0].cuerpo).toEqual({ contexto: 'registro', textos: [{ tipo: 'declaracion_agrupacion', version: '1.0.0' }] });
    expect(vistas.parches[0].cuerpo).toMatchObject({ modalidad: 'agrupacion', integrantes: [{ nombre: 'Luis', rol: 'Voz' }] });
    await page.screenshot({ path: 'pruebas/capturas/perfil-agrupacion-1440.png', fullPage: true });
  });

  test('agrupación con la declaración ya aceptada no la vuelve a pedir; volver a individual conserva las filas hasta guardar', async ({ page }) => {
    await montar(page, {
      perfilR: perfilApi({ modalidad: 'agrupacion', integrantes: [{ nombre: 'Luis', rol: 'Voz' }] }),
      mias: json(200, [{ id: 'a9', tipo: 'declaracion_agrupacion', version: '1.0.0', contexto: 'registro', id_operacion: 'o', aceptada_en: '2026-11-10T15:00:00Z', retirada_en: null }]),
    });
    await page.goto('/app/perfil');
    await expect(page.getByLabel('Nombre del integrante')).toHaveValue('Luis');
    await expect(page.getByRole('checkbox', { name: /Declaro que represento/ })).toHaveCount(0);
    await page.getByRole('radio', { name: /Individual/ }).check();
    await expect(page.getByRole('heading', { level: 2, name: /Integrantes/ })).toBeHidden();
    await page.getByRole('radio', { name: /Agrupación/ }).check();
    await expect(page.getByLabel('Nombre del integrante')).toHaveValue('Luis');
  });

  test('409 declaracion_requerida lleva a aceptar la declaración', async ({ page }) => {
    await montar(page, { perfilR: perfilApi({ modalidad: 'agrupacion', integrantes: [{ nombre: 'Luis', rol: 'Voz' }] }) });
    await page.unroute(`${API}/aceptaciones/mias`);
    await page.route(`${API}/aceptaciones/mias`, (r) => r.fulfill(json(503, { error: { codigo: 'x', mensaje: 'x' } }))); // no se supo si estaba aceptada
    await page.route(`${API}/perfil`, (r) => (r.request().method() === 'PATCH' ? r.fulfill(errorApi(409, 'declaracion_requerida')) : r.fallback()));
    await page.goto('/app/perfil');
    await guardar(page).click();
    await expect(page.getByText('Marca la casilla para registrar la agrupación.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /Declaro que represento/ })).toBeFocused();
  });

  test('menor guardado: aviso con el contacto', async ({ page }) => {
    await montar(page);
    await page.route(`${API}/contacto-estudio`, (r) => r.fulfill(json(200, { texto: 'Escríbenos a hola@bugalu.studio' })));
    await page.route(`${API}/perfil`, (r) => (r.request().method() === 'PATCH' ? r.fulfill(perfilApi({ es_menor: true })) : r.fallback()));
    await page.goto('/app/perfil');
    await page.getByRole('checkbox', { name: 'Soy menor de 18 años' }).check();
    await guardar(page).click();
    await expect(page.getByText('Aún no puedes reservar en línea')).toBeVisible();
    await expect(page.getByText('Escríbenos a hola@bugalu.studio')).toBeVisible();
  });

  test('el personal no ve identidad, integrantes ni redes', async ({ page }) => {
    await montar(page, { perfilR: perfil({ rol: 'personal' }) });
    await page.goto('/app/perfil');
    await expect(page.locator('#campo-nombre')).toBeVisible();
    await expect(page.getByRole('heading', { name: /Identidad/ })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Privacidad y textos aceptados' })).toHaveCount(0);
  });

  for (const [nombre, resp, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'x')), 'Algo salió mal'],
    ['red', (r) => r.abort(), 'Sin conexión'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>x</p>' }), 'No pudimos cargar tu perfil'],
  ]) {
    test(`falla al guardar (${nombre}) y conserva lo escrito`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page);
      await page.route(`${API}/perfil`, (r) => (r.request().method() === 'PATCH' ? resp(r) : r.fallback()));
      await page.goto('/app/perfil');
      await page.getByRole('textbox', { name: 'Domicilio' }).fill('Av. Lima 123');
      await guardar(page).click();
      await expect(page.locator('[data-avisos] .aviso')).toContainText(texto);
      await expect(page.getByRole('textbox', { name: 'Domicilio' })).toHaveValue('Av. Lima 123');
      expect(consola).toEqual([]);
    });
  }
});

test.describe('/app/perfil/privacidad', () => {
  for (const tm of tamanos) {
    test(`consentimientos sin marcar e historial a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { mias: json(200, ACEPTACIONES) });
      await page.goto('/app/perfil/privacidad/');
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Privacidad');
      await expect(page.getByText('Es opcional.')).toBeVisible();
      await expect(page.getByText('Fragmentos de 30 segundos.')).toBeVisible();
      for (const nombre of [/promociones por correo/, /promociones por WhatsApp/, /fotos y videos/, /No quiero que el estudio use mi material/]) await expect(page.getByRole('checkbox', { name: nombre })).not.toBeChecked();
      await expect(page.getByRole('link', { name: /Leer la Política de privacidad|Leer el texto completo \(versión 1\.2\.3\)/ })).toHaveAttribute('href', '/legal/privacidad/?version=1.2.3');
      const tabla = page.getByRole('table', { name: 'Textos que aceptaste' });
      const filas = tabla.locator('tbody tr');
      await expect(filas).toHaveCount(2);
      await expect(filas.first()).toContainText('Política de privacidad');
      await expect(filas.first()).toContainText('Promociones');
      await expect(filas.first()).toContainText('Retirado el 3 dic 2026');
      await expect(filas.nth(1)).toContainText('Registro');
      await expect(filas.nth(1)).toContainText('—');
      await expect(filas.first().getByRole('link', { name: /1\.2\.3/ })).toHaveAttribute('href', '/legal/privacidad/?version=1.2.3');
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/perfil-privacidad-${tm.nombre}.png`, fullPage: true });
      expect(consola).toEqual([]);
    });
  }

  test('da un consentimiento y recarga el historial', async ({ page }) => {
    const vistas = await montar(page);
    let recarga = 0;
    await page.unroute(`${API}/aceptaciones/mias`);
    await page.route(`${API}/aceptaciones/mias`, (r) => r.fulfill(json(200, recarga++ ? ACEPTACIONES : [])));
    await page.goto('/app/perfil/privacidad/');
    await expect(page.getByText('Aún no has aceptado ningún texto.')).toBeVisible();
    await page.getByRole('checkbox', { name: /promociones por correo/ }).check();
    await page.getByRole('button', { name: 'Guardar preferencias' }).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'Preferencias guardadas.' })).toBeVisible();
    expect(vistas.consentimientos[0].cuerpo).toEqual({ promociones_correo: true, promociones_whatsapp: false, fotos_videos: false, excluir_material: false });
    await expect(page.getByRole('table', { name: 'Textos que aceptaste' })).toBeVisible();
  });

  test('retirar es desmarcar y guardar', async ({ page }) => {
    const vistas = await montar(page, { perfilR: perfilApi({ consentimientos: { promociones_correo: true, promociones_whatsapp: false, fotos_videos: false, excluir_material: false } }) });
    await page.goto('/app/perfil/privacidad/');
    await page.getByRole('checkbox', { name: /promociones por correo/ }).uncheck();
    await page.getByRole('button', { name: 'Guardar preferencias' }).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'Preferencias guardadas.' })).toBeVisible();
    expect(vistas.consentimientos[0].cuerpo.promociones_correo).toBe(false);
  });

  test('sin teléfono, WhatsApp queda deshabilitado pero enfocable, con el enlace', async ({ page }) => {
    const vistas = await montar(page, { perfilR: perfilApi({ telefono: null }) });
    await page.goto('/app/perfil/privacidad/');
    const whatsapp = page.getByRole('checkbox', { name: /promociones por WhatsApp/ });
    await expect(whatsapp).toHaveAttribute('aria-disabled', 'true');
    await whatsapp.focus();
    await expect(whatsapp).toBeFocused();
    await whatsapp.click({ force: true });
    await expect(whatsapp).not.toBeChecked();
    await expect(page.getByText('Añade tu teléfono en Tus datos para elegir WhatsApp.')).toBeVisible();
    await expect(page.getByRole('link', { name: /Tus datos/ })).toHaveAttribute('href', '/app/perfil/');
    expect(vistas.consentimientos).toHaveLength(0);
  });

  test('422 telefono_requerido se muestra en la casilla de WhatsApp', async ({ page }) => {
    await montar(page);
    await page.route(`${API}/perfil/consentimientos`, (r) => r.fulfill(errorApi(422, 'telefono_requerido')));
    await page.goto('/app/perfil/privacidad/');
    await page.getByRole('checkbox', { name: /promociones por WhatsApp/ }).check();
    await page.getByRole('button', { name: 'Guardar preferencias' }).click();
    await expect(page.getByText('Añade tu teléfono en Tus datos para elegir WhatsApp.').first()).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /promociones por WhatsApp/ })).toBeChecked();
  });

  test('409 texto_desactualizado repinta con la versión nueva y conserva la elección', async ({ page }) => {
    await montar(page);
    let nueva = false;
    await page.unroute(`${API}/textos-legales`);
    await page.route(`${API}/textos-legales`, (r) => r.fulfill(json(200, nueva ? [t('politica_privacidad', '1.3.0', { promociones: 'Texto nuevo.' }), TEXTOS[2]] : TEXTOS)));
    await page.route(`${API}/perfil/consentimientos`, (r) => { nueva = true; return r.fulfill(json(409, { error: { codigo: 'texto_desactualizado', mensaje: 'x', detalles: { vigente: { tipo: 'politica_privacidad', version: '1.3.0' } } } })); });
    await page.goto('/app/perfil/privacidad/');
    await page.getByRole('checkbox', { name: /promociones por correo/ }).check();
    await page.getByRole('button', { name: 'Guardar preferencias' }).click();
    await expect(page.getByText('Texto nuevo.')).toBeVisible();
    await expect(page.getByText('Actualizamos el texto a la versión 1.3.0. Revísalo y vuelve a guardar.')).toBeVisible();
    await expect(page.getByRole('checkbox', { name: /promociones por correo/ })).toBeChecked();
  });

  test('historial con error: aviso y reintentar, el formulario sigue usable', async ({ page }) => {
    await montar(page, { mias: errorApi(503, 'x') });
    await page.goto('/app/perfil/privacidad/');
    await expect(page.getByText('No pudimos cargar tus textos aceptados.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Guardar preferencias' })).toBeEnabled();
  });

  test('el personal ve el 403 de la vista', async ({ page }) => {
    await montar(page, { perfilR: perfil({ rol: 'personal' }) });
    await page.goto('/app/perfil/privacidad/');
    await expect(page.locator('.aviso-titulo', { hasText: 'Esta sección es para artistas.' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Volver a mi perfil' })).toHaveAttribute('href', '/app/perfil/');
  });

  for (const [nombre, resp, texto] of [
    ['401', (r) => r.fulfill(errorApi(401, 'x')), 'Tu sesión no es válida'],
    ['503', (r) => r.fulfill(errorApi(503, 'x')), 'No pudimos cargar tu perfil'],
    ['red', (r) => r.abort(), 'Sin conexión'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>x</p>' }), 'No pudimos cargar tu perfil'],
  ]) {
    test(`falla la carga (${nombre})`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page);
      await page.unroute(`${API}/perfil`);
      await page.route(`${API}/perfil`, resp);
      await page.goto('/app/perfil/privacidad/');
      await expect(page.locator('bugalu-privacidad .aviso')).toContainText(texto);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('avisa de que necesita JavaScript', async ({ page }) => {
      await page.goto('/app/perfil/privacidad/');
      expect(await page.content()).toContain('Esta página necesita JavaScript');
      await expect(page.locator('bugalu-privacidad [data-salida]')).toBeHidden();
    });
  });
});
