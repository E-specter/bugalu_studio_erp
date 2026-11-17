// RF-16 (CA-01 a CA-06, CA-10, CA-12, CA-13): formulario publico del Libro de Reclamaciones, confirmacion, constancia e impresion. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, conSesion, silenciarApi, simularAuth, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { HOY, archivo, hoja, perfilCliente, simularMultipart } from './ayudas-rf16.js';

const simularEnvio = (page, resp = json(201, hoja())) => simularMultipart(page, '/reclamaciones', resp);

async function montar(page, { sesion = false, perfil, envio } = {}) {
  await page.clock.setFixedTime(HOY);
  await silenciarApi(page);
  if (sesion) {
    await conSesion(page);
    await page.route(`${API}/perfil`, (r) => r.fulfill(perfil ?? perfilCliente()));
  }
  await page.addInitScript(() => { window.__impreso = 0; window.print = () => window.__impreso++; });
  return simularEnvio(page, envio);
}

const llenar = async (page, extra = {}) => {
  await page.locator('#rc-nombre').fill('Ana Pérez');
  await page.locator('#rc-tipo-documento').selectOption('dni');
  await page.locator('#rc-documento').fill('12345678');
  await page.locator('#rc-domicilio').fill('Av. Siempre Viva 123, Lima');
  await page.locator('#rc-correo').fill('ana@correo.com');
  await page.locator('#rc-monto').fill('1250,5');
  await page.locator('#rc-descripcion').fill('Mezcla de mi EP, reserva R-2026-00014.');
  await page.locator('#rc-tipo-reclamo').check();
  await page.locator('#rc-detalle').fill('Entregaron la mezcla con tres días de retraso.');
  await page.locator('#rc-pedido').fill('Que me devuelvan la mitad del importe.');
  if (extra.adjuntos) await page.locator('#rc-adjuntos').setInputFiles(extra.adjuntos);
};
const revisar = (page) => page.getByRole('button', { name: 'Revisar la hoja' });
const enviar = (page) => page.getByRole('button', { name: /^(Enviar reclamación|Enviando…)$/ });
const avisos = (page) => page.locator('[data-avisos] .aviso');
const aConfirmar = async (page, extra) => {
  await page.goto('/libro-de-reclamaciones/');
  await llenar(page, extra);
  await revisar(page).click();
  await expect(page.getByRole('heading', { level: 2, name: 'REVISA TU HOJA' })).toBeFocused();
};

// --- 1. Acceso desde el pie (CA-01) ---
test('el pie de toda pagina publica lleva "Libro de Reclamaciones" y la razon social unificada', async ({ page }) => {
  for (const ruta of ['/', '/legal/', '/legal/privacidad/', '/reservar/']) {
    await page.goto(ruta);
    const pie = page.getByRole('contentinfo');
    await expect(pie.getByRole('link', { name: 'Libro de Reclamaciones', exact: true })).toHaveAttribute('href', '/libro-de-reclamaciones/');
    await expect(pie).toContainText('Aural Perú E.I.R.L.');
    await expect(pie).not.toContainText(/EIRL/i);
  }
  await page.goto('/');
  await page.getByRole('contentinfo').getByRole('link', { name: 'Libro de Reclamaciones' }).click();
  await expect(page).toHaveURL('/libro-de-reclamaciones/');
  await expect(page.getByRole('heading', { level: 1, name: 'LIBRO DE RECLAMACIONES' })).toBeVisible();
});

test('en el acceso el pie tambien lleva el enlace', async ({ page }) => {
  await page.goto('/acceso/');
  await expect(page.getByRole('contentinfo').getByRole('link', { name: 'Libro de Reclamaciones' })).toHaveAttribute('href', '/libro-de-reclamaciones/');
});

// --- 2. Formulario vacio ---
for (const t of tamanos) {
  test(`formulario: hoja del Anexo I en su orden, proveedor fijo y campo trampa, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await montar(page);
    await page.goto('/libro-de-reclamaciones/');
    await expect(page).toHaveTitle('Paso 1 de 2 · Libro de Reclamaciones · Bugalú Studio');
    await expect(page.getByText('PASO 1 DE 2 · COMPLETA LA HOJA')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('LIBRO DE RECLAMACIONES');
    await expect(page.getByText('Presenta un reclamo o una queja sobre nuestros servicios. No necesitas cuenta.')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'HOJA DE RECLAMACIÓN' })).toBeVisible();
    await expect(page.getByText('N.º Se asigna al enviar')).toBeVisible();
    await expect(page.locator('time[data-fecha-hoy]')).toHaveText('17 nov 2026');
    const proveedor = page.locator('.hoja-proveedor');
    await expect(proveedor).toContainText('Aural Perú E.I.R.L.');
    await expect(proveedor).toContainText('20615656128');
    await expect(proveedor).toContainText('Av. Javier Prado Este 5920, La Molina, Lima');
    expect(await page.locator('form h2').allTextContents()).toEqual(['1 IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE', '2 IDENTIFICACIÓN DEL BIEN CONTRATADO', '3 DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR']);
    await expect(page.getByText('Todos los datos son obligatorios salvo los marcados como opcionales.')).toBeVisible();
    // Definiciones literales del Anexo I y leyendas.
    await expect(page.getByText('RECLAMO: Disconformidad relacionada a los productos o servicios.').first()).toBeVisible();
    await expect(page.getByText('QUEJA: Disconformidad no relacionada a los productos o servicios; o, malestar o descontento respecto a la atención al público.').first()).toBeVisible();
    await expect(page.getByText('La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es requisito previo para interponer una denuncia ante el INDECOPI.')).toBeVisible();
    await expect(page.getByText('El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días hábiles improrrogables.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Política de privacidad' }).first()).toHaveAttribute('href', '/legal/privacidad/');
    // Valores por defecto: servicio, correo; tipo sin marcar; menor sin marcar y su grupo oculto.
    await expect(page.locator('#rc-bien-servicio')).toBeChecked();
    await expect(page.locator('#rc-medio-correo')).toBeChecked();
    await expect(page.locator('#rc-tipo-reclamo')).not.toBeChecked();
    await expect(page.locator('#rc-tipo-queja')).not.toBeChecked();
    await expect(page.locator('#rc-tutor')).toBeHidden();
    await expect(page.locator('#rc-menor')).toHaveAttribute('aria-controls', 'rc-tutor');
    // Sin sesion: sin aviso de prellenado.
    await expect(page.getByText('Usamos los datos de tu cuenta')).toBeHidden();
    // Un unico boton primario; sin barra.
    await expect(page.locator('main .boton-primario:visible')).toHaveCount(1);
    // Campo trampa: fuera de la vista y del arbol de accesibilidad, fuera del teclado, pero no display:none.
    const trampa = page.locator('input[name="sitio_web"]');
    await expect(trampa).toHaveAttribute('tabindex', '-1');
    await expect(trampa).toHaveAttribute('autocomplete', 'off');
    expect(await trampa.evaluate((e) => getComputedStyle(e.closest('[aria-hidden="true"]')).display)).not.toBe('none');
    await expect(page.getByRole('textbox', { name: 'No completes este campo' })).toHaveCount(0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamacion-formulario-${t.nombre}.png`, fullPage: true });
  });
}

test('sin JavaScript: canales para reclamar y las leyendas; el formulario no aparece', async ({ browser }) => {
  const contexto = await browser.newContext({ javaScriptEnabled: false });
  const page = await contexto.newPage();
  await page.goto('/libro-de-reclamaciones/');
  await expect(page.getByRole('heading', { level: 1, name: 'LIBRO DE RECLAMACIONES' })).toBeVisible();
  // Playwright no lee el texto de <noscript> con getByText: se usan selectores CSS.
  await expect(page.locator('noscript .aviso-titulo')).toContainText('Para llenar la hoja aquí necesitas JavaScript.');
  await expect(page.locator('noscript a[href^="mailto:somos.bugalu.studio@gmail.com"]')).toBeVisible();
  await expect(page.locator('noscript a[href="https://wa.me/51925530800"]')).toBeVisible();
  await expect(page.locator('noscript .contacto')).toContainText('En persona, con un profesional autorizado');
  await expect(page.locator('noscript .reclamacion-sin-js .aviso-cuerpo > p').last()).toContainText('Te respondemos en un máximo de 15 días hábiles.');
  await expect(page.locator('noscript .reclamacion-leyenda').first()).toContainText('La formulación del reclamo no impide acudir');
  await expect(page.locator('form')).toBeHidden();
  await page.screenshot({ path: 'pruebas/capturas/reclamacion-sin-js.png', fullPage: true });
  await contexto.close();
});

// --- 3. Validacion local (CA-03) ---
test('validacion: resumen con el numero de errores, enlaces y foco al primer campo con error', async ({ page }) => {
  const vistas = await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  await revisar(page).click();
  const aviso = avisos(page);
  await expect(aviso).toContainText('Revisa 8 datos antes de seguir');
  await expect(aviso).not.toHaveAttribute('role', /.+/);
  await expect(page.locator('#rc-nombre')).toBeFocused();
  await expect(page.locator('#rc-nombre')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText('Escribe el nombre completo.')).toBeVisible();
  await expect(page.getByText('Elige el tipo de documento.')).toBeVisible();
  await expect(page.getByText('Escribe el número de documento.')).toBeVisible();
  await expect(page.getByText('Escribe el domicilio.')).toBeVisible();
  await expect(page.getByText('Escribe el correo.')).toBeVisible();
  await expect(page.getByText('Elige si es un reclamo o una queja.')).toBeVisible();
  await expect(page.getByText('Cuenta qué pasó con al menos 10 caracteres.')).toBeVisible();
  await expect(page.getByText('Escribe qué pides con al menos 10 caracteres.')).toBeVisible();
  await expect(aviso.getByRole('link')).toHaveCount(8);
  // Cada error se lee por aria-describedby del campo.
  await expect(page.locator('#rc-nombre')).toHaveAttribute('aria-describedby', 'rc-nombre-error');
  expect(vistas).toHaveLength(0);
  await sinViolaciones(page);
  // El enlace del resumen lleva al campo.
  await aviso.getByRole('link', { name: 'Domicilio' }).click();
  await expect(page.locator('#rc-domicilio')).toBeFocused();
  await page.screenshot({ path: 'pruebas/capturas/reclamacion-validacion.png', fullPage: true });
});

test('validacion: formatos de documento, correo, monto y largos', async ({ page }) => {
  await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  await llenar(page);
  await page.locator('#rc-documento').fill('123');
  await page.locator('#rc-correo').fill('ana@');
  await page.locator('#rc-monto').fill('0');
  await page.locator('#rc-detalle').fill('corto');
  await page.locator('#rc-nombre').evaluate((e) => (e.value = 'x'.repeat(201))); // el maxlength frena al teclado, no a un autocompletado
  await revisar(page).click();
  await expect(avisos(page)).toContainText('Revisa 5 datos antes de seguir');
  await expect(page.getByText('Escribe los 8 dígitos de tu DNI.')).toBeVisible();
  await expect(page.getByText('Escribe un correo válido, como nombre@correo.com.')).toBeVisible();
  await expect(page.getByText('Escribe un monto entre S/ 0,01 y S/ 999 999,99, o déjalo vacío.')).toBeVisible();
  await expect(page.getByText('Cuenta qué pasó con al menos 10 caracteres.')).toBeVisible();
  await expect(page.getByText('El nombre admite hasta 200 caracteres.')).toBeVisible();
  await page.locator('#rc-tipo-documento').selectOption('ce');
  await page.locator('#rc-documento').fill('AB 12');
  await page.locator('#rc-monto').fill('1000000');
  await revisar(page).click();
  await expect(page.getByText('Escribe de 6 a 12 letras o cifras, sin espacios ni guiones.')).toBeVisible();
  await expect(page.getByText('Escribe un monto entre S/ 0,01 y S/ 999 999,99, o déjalo vacío.')).toBeVisible();
  await page.locator('#rc-monto').fill('');
  await page.locator('#rc-documento').fill('X1234567');
  await page.locator('#rc-nombre').fill('Ana');
  await page.locator('#rc-correo').fill('ana@correo.com');
  await page.locator('#rc-detalle').evaluate((e) => (e.value = 'd'.repeat(3001)));
  await revisar(page).click();
  await expect(page.getByText('Admite hasta 3000 caracteres.')).toBeVisible();
  await expect(avisos(page)).toContainText('Revisa 1 dato antes de seguir');
});

test('menor de edad: aparece el grupo del tutor, que se exige y se envia', async ({ page }) => {
  const vistas = await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  await llenar(page);
  await page.getByRole('checkbox', { name: /Soy menor de edad/ }).check();
  await expect(page.locator('#rc-tutor')).toBeVisible();
  await expect(page.getByRole('group', { name: 'Datos de tu madre, padre o tutor' })).toBeVisible();
  await expect(page.locator('#rc-menor')).toBeFocused();
  await revisar(page).click();
  await expect(avisos(page)).toContainText('Revisa 3 datos antes de seguir');
  await expect(page.locator('#rc-rep-nombre')).toBeFocused();
  await page.locator('#rc-rep-nombre').fill('Rosa Pérez');
  await page.locator('#rc-rep-domicilio').fill('Av. Siempre Viva 123, Lima');
  await page.locator('#rc-rep-correo').fill('rosa@correo.com');
  await revisar(page).click();
  await expect(page.locator('article.hoja').getByText('Menor de edad', { exact: true })).toBeVisible();
  await expect(page.locator('article.hoja').getByText('Rosa Pérez')).toBeVisible();
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  expect(vistas[0].datos.es_menor).toBe(true);
  expect(vistas[0].datos.representante).toEqual({ nombre: 'Rosa Pérez', domicilio: 'Av. Siempre Viva 123, Lima', correo: 'rosa@correo.com' });
});

// --- 4. Confirmacion (CA-04) ---
for (const t of tamanos) {
  test(`confirmacion: la hoja completa en lectura, sin enviar nada, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await montar(page);
    await aConfirmar(page, { adjuntos: [archivo('voucher.png'), archivo('constancia.pdf', 'application/pdf', Buffer.from('%PDF-1.4'))] });
    await expect(page).toHaveTitle('Paso 2 de 2: confirma · Libro de Reclamaciones · Bugalú Studio');
    await expect(page.getByText('PASO 2 DE 2 · CONFIRMA')).toBeVisible();
    await expect(page.getByText('Así quedará registrada. Si algo no está bien, corrígelo ahora: una vez enviada no se puede cambiar.')).toBeVisible();
    const hojaEl = page.locator('article.hoja');
    await expect(hojaEl.getByRole('heading', { level: 2 })).toHaveText('HOJA DE RECLAMACIÓN');
    await expect(hojaEl).toContainText('N.º Se asigna al enviar');
    await expect(hojaEl).toContainText('17 nov 2026 · la hora se fija al enviar');
    await expect(hojaEl).toContainText('Ana Pérez');
    await expect(hojaEl).toContainText('DNI 12345678');
    await expect(hojaEl).toContainText('S/ 1 250,50');
    await expect(hojaEl).toContainText('Servicio');
    await expect(hojaEl).toContainText('Reclamo');
    await expect(hojaEl).toContainText('Correo electrónico');
    await expect(hojaEl).toContainText('—'); // teléfono opcional sin dato
    await expect(hojaEl).toContainText('voucher.png');
    await expect(hojaEl).toContainText('PNG · 1 KB');
    await expect(hojaEl).toContainText('constancia.pdf');
    await expect(hojaEl).toContainText('PDF · 1 KB');
    expect(await hojaEl.locator('h3').allTextContents()).toEqual(['1. IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE', '2. IDENTIFICACIÓN DEL BIEN CONTRATADO', '3. DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR']);
    await expect(hojaEl.getByRole('link')).toHaveCount(0); // los adjuntos no se abren antes de enviar
    // Botones del mismo tamano: corregir es tan facil como enviar.
    const [a, b] = await Promise.all([page.getByRole('button', { name: 'Corregir datos' }).boundingBox(), enviar(page).boundingBox()]);
    expect(a.height).toBe(b.height);
    expect(vistas).toHaveLength(0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamacion-confirmacion-${t.nombre}.png`, fullPage: true });
  });
}

test('corregir datos: vuelve al formulario con todo lo escrito y los adjuntos; el foco va al titulo', async ({ page }) => {
  await montar(page);
  await aConfirmar(page, { adjuntos: archivo() });
  await page.getByRole('button', { name: 'Corregir datos' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
  await expect(page.locator('#rc-nombre')).toHaveValue('Ana Pérez');
  await expect(page.locator('#rc-monto')).toHaveValue('1250,5');
  await expect(page.locator('#rc-tipo-reclamo')).toBeChecked();
  await expect(page.getByRole('button', { name: 'Quitar voucher.png' })).toBeVisible();
  await expect(page).toHaveTitle('Paso 1 de 2 · Libro de Reclamaciones · Bugalú Studio');
});

// --- 5. Envio y constancia (CA-04, CA-05) ---
for (const t of tamanos) {
  test(`envio: multipart con confirmado, constancia con numero, fecha y plazo, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const vistas = await montar(page, { envio: json(201, hoja({ adjuntos: [{ n: 1, nombre: 'voucher.png', tipo: 'image/png', tamano: 70 }] })) });
    await aConfirmar(page, { adjuntos: archivo() });
    await enviar(page).click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
    await expect(page).toHaveTitle('Hoja N.º 000000001-2026 registrada · Libro de Reclamaciones · Bugalú Studio');
    expect(vistas).toHaveLength(1);
    expect(vistas[0].tipo).toMatch(/^multipart\/form-data; boundary=/);
    expect(vistas[0].auth).toBeUndefined();
    expect(vistas[0].adjuntos).toEqual(['voucher.png']);
    expect(vistas[0].datos).toEqual({
      confirmado: true,
      consumidor: { nombre: 'Ana Pérez', tipo_documento: 'dni', documento: '12345678', domicilio: 'Av. Siempre Viva 123, Lima', correo: 'ana@correo.com' },
      es_menor: false,
      bien: { tipo: 'servicio', monto: '1250.50', descripcion: 'Mezcla de mi EP, reserva R-2026-00014.' },
      tipo: 'reclamo', detalle: 'Entregaron la mezcla con tres días de retraso.', pedido: 'Que me devuelvan la mitad del importe.', medio_respuesta: 'correo',
    });
    const exito = avisos(page);
    await expect(exito).toBeFocused();
    await expect(exito).toContainText('Registramos tu hoja N.º 000000001-2026');
    await expect(exito).toContainText('Te enviamos una copia a ana@correo.com. Te responderemos por correo electrónico a más tardar el 8 dic 2026.');
    await expect(exito).toContainText('Guarda o imprime esta constancia antes de salir.');
    await expect(exito).not.toContainText('Mis reclamos');
    const hojaEl = page.locator('article.hoja');
    await expect(hojaEl.getByRole('heading', { level: 2 })).toContainText('HOJA DE RECLAMACIÓN N.º 000000001-2026');
    await expect(hojaEl.locator('time[data-fecha]')).toHaveText('17 nov 2026, 14:30');
    await expect(hojaEl.locator('time[data-fecha]')).toHaveAttribute('datetime', '2026-11-17T19:30:00Z');
    await expect(hojaEl).not.toContainText('SIN RESPUESTA'); // la hoja acaba de nacer: sin seccion 4
    await expect(hojaEl).toContainText('voucher.png');
    await expect(page.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/');
    await expect(page.getByRole('link', { name: 'Ver mis reclamos' })).toBeHidden();
    await expect(page.locator('main .boton-primario:visible')).toHaveCount(1);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamacion-constancia-${t.nombre}.png`, fullPage: true });
  });
}

test('el campo trampa lleno no pierde el reclamo: viaja en datos.sitio_web y se muestra la constancia', async ({ page }) => {
  const vistas = await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  await llenar(page);
  await page.locator('input[name="sitio_web"]').evaluate((e) => (e.value = 'http://spam.example'));
  await revisar(page).click();
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  expect(vistas[0].datos.sitio_web).toBe('http://spam.example');
});

test('201 sin numero (envio aparente): solo el aviso, sin hoja ni imprimir', async ({ page }) => {
  await montar(page, { envio: json(201, {}) });
  await aConfirmar(page);
  await enviar(page).click();
  await expect(avisos(page)).toContainText('Registramos tu hoja');
  await expect(avisos(page)).not.toContainText('N.º');
  await expect(page.locator('article.hoja')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Imprimir o guardar en PDF' })).toBeHidden();
});

test('enviando: boton en carga, "Corregir datos" deshabilitado y aviso a los 10 s', async ({ page }) => {
  await page.clock.install({ time: HOY });
  await silenciarApi(page);
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await simularEnvio(page, async (r) => { await espera; await r.fulfill(json(201, hoja())); });
  await aConfirmar(page, { adjuntos: archivo() });
  await enviar(page).click();
  await expect(page.getByRole('button', { name: 'Enviando…' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Enviando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Corregir datos' })).toBeDisabled();
  await page.clock.runFor(10_000);
  await expect(page.locator('[data-progreso]')).toHaveText('Subiendo los adjuntos, puede tardar un minuto.');
  soltar();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
});

test('enviando sin adjuntos: el aviso lento es otro', async ({ page }) => {
  await page.clock.install({ time: HOY });
  await silenciarApi(page);
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await simularEnvio(page, async (r) => { await espera; await r.fulfill(json(201, hoja())); });
  await aConfirmar(page);
  await enviar(page).click();
  await page.clock.runFor(10_000);
  await expect(page.locator('[data-progreso]')).toHaveText('Seguimos registrando tu hoja…');
  soltar();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
});

// --- 6. Errores del envio ---
const canales = ['somos.bugalu.studio@gmail.com', '+51 925 530 800'];
const falla = [
  { n: '409', r: (r) => r.fulfill(errorApi(409, 'confirmacion_requerida')), titulo: 'No pudimos registrar la hoja', texto: 'Vuelve a pulsar «Enviar reclamación».' },
  { n: '429', r: (r) => r.fulfill(errorApi(429, 'demasiadas_solicitudes')), titulo: 'Demasiados envíos desde tu conexión', texto: 'Recibimos muchas hojas desde tu conexión en la última hora. Tus datos siguen aquí: inténtalo más tarde o preséntala por estos canales:', canales: true },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), titulo: 'El Libro de Reclamaciones no responde', texto: 'No pudimos registrar tu hoja. Tus datos siguen aquí: inténtalo en unos minutos o preséntala por estos canales:', canales: true },
  { n: 'red caída', r: (r) => r.abort('connectionrefused'), titulo: 'Sin conexión', texto: 'No sabemos si tu hoja llegó. Si en unos minutos no recibes la constancia en tu correo, vuelve a enviarla: tus datos siguen aquí.' },
  { n: 'no JSON', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), titulo: 'Algo salió mal', texto: 'No pudimos registrar tu hoja. Tus datos siguen aquí: inténtalo de nuevo o preséntala por estos canales:', canales: true },
  { n: '500', r: (r) => r.fulfill(errorApi(500, 'error_interno')), titulo: 'Algo salió mal', texto: 'No pudimos registrar tu hoja. Tus datos siguen aquí: inténtalo de nuevo o preséntala por estos canales:', canales: true },
];
for (const f of falla) {
  test(`error de envio ${f.n}: aviso en la confirmacion, datos intactos y sin reintento automatico`, async ({ page }) => {
    const consola = vigilarConsola(page);
    const vistas = await montar(page, { envio: f.r });
    await aConfirmar(page);
    await enviar(page).click();
    const aviso = avisos(page);
    await expect(aviso).toBeFocused();
    await expect(aviso).toContainText(f.titulo);
    await expect(aviso).toContainText(f.texto);
    if (f.canales) for (const c of canales) await expect(aviso.getByRole('link', { name: c })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'REVISA TU HOJA' })).toBeVisible();
    await expect(enviar(page)).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Corregir datos' })).toBeEnabled();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await page.waitForTimeout(300);
    expect(vistas).toHaveLength(1); // nunca se reintenta solo (evita hojas repetidas)
    await sinViolaciones(page);
    await page.getByRole('button', { name: 'Corregir datos' }).click();
    await expect(page.locator('#rc-nombre')).toHaveValue('Ana Pérez');
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/reclamacion-error-${f.n.replace(/\W/g, '')}.png`, fullPage: true });
  });
}

test('un error y un reenvio posterior: la hoja se registra una vez cuando el servidor responde', async ({ page }) => {
  const vistas = await montar(page, { envio: (r, n) => r.fulfill(n === 1 ? errorApi(503, 'servicio_no_disponible') : json(201, hoja())) });
  await aConfirmar(page);
  await enviar(page).click();
  await expect(avisos(page)).toContainText('El Libro de Reclamaciones no responde');
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  expect(vistas).toHaveLength(2);
  expect(vistas[1].datos).toEqual(vistas[0].datos);
});

test('413 con detalles.adjunto: el archivo señalado toma el estado Error y el foco va a su "Quitar"', async ({ page }) => {
  await montar(page, { envio: (r) => r.fulfill({ ...errorApi(413, 'adjunto_muy_grande'), body: JSON.stringify({ error: { codigo: 'adjunto_muy_grande', mensaje: 'x', detalles: { adjunto: 2 } } }) }) });
  await aConfirmar(page, { adjuntos: [archivo('uno.png'), archivo('dos.png')] });
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('[data-vista="formulario"]')).toBeVisible();
  await expect(avisos(page)).toContainText('Revisa 1 dato antes de seguir');
  await expect(page.getByText('dos.png pesa más de 5 MB. Quítalo o elige uno más liviano.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Quitar dos.png' })).toBeFocused();
  await expect(page.getByRole('button', { name: 'Quitar dos.png' })).toHaveAttribute('aria-describedby', /rechazo-2/);
  await expect(page.getByText('uno.png pesa')).toHaveCount(0);
  expect(await page.locator('.archivo[data-error]').count()).toBe(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reclamacion-adjunto-rechazado.png', fullPage: true });
  // Quitarlo permite registrar la hoja sin el adjunto (CA-06).
  await page.getByRole('button', { name: 'Quitar dos.png' }).click();
  await expect(page.locator('.archivo[data-error]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Quitar uno.png' })).toBeFocused();
});

test('422 adjunto_no_permitido y sin detalles: el error va al grupo ADJUNTOS', async ({ page }) => {
  await montar(page, { envio: (r) => r.fulfill(errorApi(422, 'adjunto_no_permitido')) });
  await aConfirmar(page, { adjuntos: archivo('raro.png') });
  await enviar(page).click();
  await expect(page.getByText('Uno de los adjuntos no se aceptó (más de 5 MB o no es PDF, JPG ni PNG). Quítalo o cámbialo.')).toBeVisible();
  await expect(page.locator('#rc-adjuntos')).toBeFocused();
});

test('422 adjunto_no_permitido con detalles: texto del archivo y 422 demasiados_adjuntos', async ({ page }) => {
  const cuerpo = (codigo, detalles) => ({ status: 422, contentType: 'application/json', body: JSON.stringify({ error: { codigo, mensaje: 'x', detalles } }) });
  await montar(page, { envio: (r, n) => r.fulfill(n === 1 ? cuerpo('adjunto_no_permitido', { adjunto: 1 }) : cuerpo('demasiados_adjuntos')) });
  await aConfirmar(page, { adjuntos: archivo('raro.png') });
  await enviar(page).click();
  await expect(page.getByText('raro.png no es un PDF, JPG o PNG válido. Quítalo para enviar la hoja sin él.')).toBeVisible();
  await page.getByRole('button', { name: 'Revisar la hoja' }).click();
  await enviar(page).click();
  await expect(page.getByText('Puedes adjuntar hasta 3 archivos. Quita los que sobran.')).toBeVisible();
});

test('422 datos_invalidos con detalles.campo: error bajo el campo y foco ahi; sin campo, aviso con el mensaje', async ({ page }) => {
  const cuerpo = (detalles, mensaje) => ({ status: 422, contentType: 'application/json', body: JSON.stringify({ error: { codigo: 'datos_invalidos', mensaje, detalles } }) });
  await montar(page, { envio: (r, n) => r.fulfill(n === 1 ? cuerpo({ campo: 'consumidor.correo' }, 'Correo no válido') : cuerpo(undefined, 'La hoja tiene datos que no se pudieron validar.')) });
  await aConfirmar(page);
  await enviar(page).click();
  await expect(page.locator('#rc-correo')).toBeFocused();
  await expect(page.locator('#rc-correo')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#rc-correo-error')).toContainText('Correo no válido');
  await revisar(page).click();
  await enviar(page).click();
  await expect(avisos(page)).toContainText('La hoja tiene datos que no se pudieron validar.');
  await expect(page.locator('[data-vista="formulario"]')).toBeVisible();
});

// --- 7. Adjuntos del lado del navegador (CA-06) ---
test('adjuntos: se suman hasta 3, el control se oculta y quitar mueve el foco', async ({ page }) => {
  await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  const entrada = page.locator('#rc-adjuntos');
  await expect(entrada).toHaveJSProperty('multiple', true);
  await expect(entrada).toHaveAttribute('accept', 'image/jpeg,image/png,application/pdf');
  await expect(page.getByText('Comprobantes, capturas o fotos. Hasta 3 archivos PDF, JPG o PNG de 5 MB cada uno.')).toBeVisible();
  await entrada.setInputFiles(archivo('uno.png'));
  await entrada.setInputFiles(archivo('dos.png'));
  await expect(page.getByRole('button', { name: /^Quitar / })).toHaveText(['', '']);
  await expect(page.getByRole('img', { name: 'Vista previa de uno.png' })).toBeVisible();
  await entrada.setInputFiles([archivo('tres.png'), archivo('cuatro.png')]);
  await expect(page.getByRole('button', { name: /^Quitar / })).toHaveCount(3);
  await expect(page.getByText('Máximo 3 archivos.')).toBeVisible();
  await expect(page.locator('.carga-boton')).toBeHidden();
  await expect(page.locator('#rc-adjuntos-error')).toContainText('Puedes adjuntar hasta 3 archivos. Quita uno para añadir cuatro.png.');
  await sinViolaciones(page);
  await page.getByRole('button', { name: 'Quitar dos.png' }).click();
  await expect(page.getByRole('button', { name: 'Quitar tres.png' })).toBeFocused(); // el siguiente
  await expect(page.locator('.carga-boton')).toBeVisible();
  await page.getByRole('button', { name: 'Quitar tres.png' }).click();
  await page.getByRole('button', { name: 'Quitar uno.png' }).click();
  await expect(entrada).toBeFocused(); // no queda ninguno: el control
});

test('adjuntos: tipo y peso se rechazan antes de entrar a la lista, nombrando el archivo', async ({ page }) => {
  await montar(page);
  await page.goto('/libro-de-reclamaciones/');
  const entrada = page.locator('#rc-adjuntos');
  await entrada.setInputFiles(archivo('nota.txt', 'text/plain', Buffer.from('hola')));
  await expect(page.locator('#rc-adjuntos-error')).toContainText('nota.txt no es PDF, JPG ni PNG. Elige otro archivo.');
  await expect(entrada).toHaveAttribute('aria-invalid', 'true');
  await entrada.setInputFiles(archivo('grande.png', 'image/png', Buffer.alloc(6 * 1024 * 1024)));
  await expect(page.locator('#rc-adjuntos-error')).toContainText('grande.png pesa más de 5 MB. Elige uno más liviano.');
  await expect(page.getByRole('button', { name: /^Quitar / })).toHaveCount(0);
  await entrada.setInputFiles(archivo('bien.png'));
  await expect(page.locator('#rc-adjuntos-error')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Quitar bien.png' })).toBeVisible();
});

// --- 8. Con sesion (CA-10) y sesion vencida ---
test('con sesion de cliente: datos del perfil prellenados y editables, aviso y token en el envio', async ({ page }) => {
  const consola = vigilarConsola(page);
  const vistas = await montar(page, { sesion: true, perfil: perfilCliente({ es_menor: true, menor: { tutor: { nombre: 'Rosa Pérez', telefono: '999111222', correo: 'rosa@correo.com' } } }) });
  await page.goto('/libro-de-reclamaciones/');
  await expect(page.locator('#rc-nombre')).toHaveValue('Ana Pérez');
  await expect(page.locator('#rc-tipo-documento')).toHaveValue('dni');
  await expect(page.locator('#rc-documento')).toHaveValue('12345678');
  await expect(page.locator('#rc-domicilio')).toHaveValue('Av. Siempre Viva 123, Lima');
  await expect(page.locator('#rc-telefono')).toHaveValue('987654321');
  await expect(page.locator('#rc-correo')).toHaveValue('ana@correo.com');
  await expect(page.locator('#rc-menor')).toBeChecked();
  await expect(page.locator('#rc-rep-nombre')).toHaveValue('Rosa Pérez');
  await expect(page.locator('#rc-rep-correo')).toHaveValue('rosa@correo.com');
  await expect(page.getByText('Usamos los datos de tu cuenta')).toBeVisible();
  await expect(page.getByText('La hoja quedará en Mis reclamos.')).toBeVisible();
  await page.locator('#rc-nombre').fill('Ana M. Pérez');
  await page.locator('#rc-rep-domicilio').fill('Av. Siempre Viva 123, Lima');
  await page.locator('#rc-tipo-queja').check();
  await page.locator('#rc-detalle').fill('Me atendieron con mala cara en recepción.');
  await page.locator('#rc-pedido').fill('Que me pidan disculpas por escrito.');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/reclamacion-prellenado.png', fullPage: true });
  await revisar(page).click();
  await enviar(page).click();
  expect(vistas[0].auth).toBe('Bearer token-de-prueba');
  expect(vistas[0].datos.consumidor.nombre).toBe('Ana M. Pérez');
  await expect(avisos(page)).toContainText('También la encuentras en Mis reclamos.');
  await expect(page.getByRole('link', { name: 'Ver mis reclamos' })).toHaveAttribute('href', '/app/reclamos/');
  await expect(page.getByRole('link', { name: 'Volver al inicio' })).toBeHidden();
  expect(consola).toEqual([]);
});

test('el perfil no se pisa lo que ya escribio el consumidor, y si /perfil falla la hoja queda vacia sin error', async ({ page }) => {
  await montar(page, { sesion: true });
  await page.route(`${API}/perfil`, (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')));
  await page.goto('/libro-de-reclamaciones/');
  await expect(page.locator('#rc-nombre')).toBeVisible();
  await expect(page.locator('#rc-nombre')).toHaveValue('');
  await expect(page.getByText('Usamos los datos de tu cuenta')).toBeHidden();
  await expect(avisos(page)).toHaveCount(0);
});

test('con otro rol (personal) no se prellena', async ({ page }) => {
  await montar(page, { sesion: true, perfil: perfilCliente({ rol: 'personal' }) });
  await page.goto('/libro-de-reclamaciones/');
  await expect(page.locator('#rc-nombre')).toHaveValue('');
  await expect(page.getByText('Usamos los datos de tu cuenta')).toBeHidden();
});

test('sesion vencida (el servidor responde 401 al token): se reenvia una vez sin token y la hoja se registra', async ({ page }) => {
  const vistas = await montar(page, { sesion: true, envio: (r, n) => r.fulfill(n === 1 ? errorApi(401, 'no_autenticado') : json(201, hoja())) });
  await page.goto('/libro-de-reclamaciones/');
  await expect(page.locator('#rc-nombre')).toHaveValue('Ana Pérez');
  await page.locator('#rc-tipo-queja').check();
  await page.locator('#rc-detalle').fill('Me atendieron con mala cara en recepción.');
  await page.locator('#rc-pedido').fill('Que me pidan disculpas por escrito.');
  await revisar(page).click();
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  expect(vistas.map((v) => v.auth)).toEqual(['Bearer token-de-prueba', undefined]);
});

test('sesion vencida que no se puede renovar: el envio sale sin token', async ({ page }) => {
  await page.clock.setFixedTime(HOY);
  await silenciarApi(page);
  await page.addInitScript(() => {
    if (sessionStorage.getItem('__s')) return;
    sessionStorage.setItem('__s', '1');
    localStorage.setItem('bugalu-sesion', JSON.stringify({ access_token: 'caducado', token_type: 'bearer', expires_in: 3600, expires_at: 1000, refresh_token: 'refresco', user: { id: 'u1', aud: 'authenticated', email: 'ana@correo.com', app_metadata: {}, user_metadata: {}, created_at: '2026-01-01T00:00:00Z' } }));
  });
  await simularAuth(page, { '/token': json(400, { code: 400, error_code: 'refresh_token_not_found', msg: 'x' }) });
  const vistas = await simularEnvio(page);
  await aConfirmar(page);
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  expect(vistas).toHaveLength(1);
  expect(vistas[0].auth).toBeUndefined();
  await expect(page.getByRole('link', { name: 'Volver al inicio' })).toBeVisible();
});

// --- 9. Impresion de la constancia (CA-05) ---
test('imprimir: boton Imprimir llama a window.print y el estilo de impresion deja solo la hoja', async ({ page }) => {
  await montar(page, { envio: json(201, hoja({ adjuntos: [{ n: 1, nombre: 'voucher.png', tipo: 'image/png', tamano: 70 }] })) });
  await aConfirmar(page);
  await enviar(page).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('HOJA REGISTRADA');
  await page.getByRole('button', { name: 'Imprimir o guardar en PDF' }).click();
  expect(await page.evaluate(() => window.__impreso)).toBe(1);
  await page.emulateMedia({ media: 'print' });
  // Fuera: cabecera, enlace de salto, titulo y linea tecnica, aviso, botones y pie.
  for (const sel of ['header.publico-cabecera', '.saltar', 'footer.pie', '[data-encabezado]', '.aviso', '.boton', '[data-no-imprimir]']) {
    for (const el of await page.locator(sel).all()) await expect(el).toBeHidden();
  }
  // Dentro: la hoja con su numero, fecha, proveedor, secciones, adjuntos, definiciones, leyendas y la copia impresa.
  const hojaEl = page.locator('article.hoja');
  await expect(hojaEl).toBeVisible();
  await expect(hojaEl.getByRole('heading', { level: 2 })).toContainText('N.º 000000001-2026');
  await expect(hojaEl).toContainText('Aural Perú E.I.R.L.');
  await expect(hojaEl).toContainText('voucher.png');
  await expect(hojaEl).toContainText('RECLAMO: Disconformidad relacionada a los productos o servicios.');
  await expect(hojaEl).toContainText('quince (15) días hábiles improrrogables');
  await expect(hojaEl.locator('.hoja-copia')).toBeVisible();
  await expect(hojaEl.locator('.hoja-copia')).toHaveText(/^Copia impresa desde localhost:\d+ el 17 nov 2026, 12:00$/);
  const estilo = await hojaEl.evaluate((e) => { const c = getComputedStyle(e); return [c.backgroundColor, c.borderTopWidth, c.boxShadow]; });
  expect(estilo).toEqual(['rgba(0, 0, 0, 0)', '0px', 'none']);
  await page.screenshot({ path: 'pruebas/capturas/reclamacion-constancia-impresion.png', fullPage: true });
  await page.emulateMedia({ media: 'screen' });
  await expect(page.locator('footer.pie')).toBeVisible();
});
