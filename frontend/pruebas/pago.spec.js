// RF-05 (CA-01..CA-04, CA-09 lado cliente): registrar el pago de una cuota. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';

const ID = '11111111-1111-4111-8111-111111111111';
const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const C2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const AHORA = new Date('2026-11-15T15:00:00Z');
const dentroDe = (min) => new Date(AHORA.getTime() + min * 60e3).toISOString();
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const SIMULACION = { lineas: [{ concepto: 'Sala de grabación', cantidad: '2.50', unidad: 'hora', monto: '415.00' }], recargos: [], total: '415.00', anticipo: '207.50' };
const reserva = (extra = {}) => ({
  id: ID, folio: 'R-2026-00001', estado: 'pre_reservada', motivo_cancelacion: null, nota_cancelacion: null, pago_por_validar: false,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:30:00-05:00', sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [],
  precio: SIMULACION, vence_pago: dentroDe(2 * 1440 + 3 * 60 + 30),
  cuotas: [
    { id: C1, hito: 'al_reservar', monto: '207.50', estado: 'pendiente', pagable: true, pagos: [] },
    { id: C2, hito: 'al_terminar', monto: '207.50', estado: 'pendiente', pagable: false, pagos: [] },
  ],
  ...extra,
});
const METODOS = [
  { metodo: 'transferencia', texto: 'Banco Bugalú\nCuenta 193-0000000-0-00', activo: true },
  { metodo: 'yape', texto: 'Yape al 999 888 777', activo: true },
  { metodo: 'plin', texto: 'Plin al 999 888 777', activo: true },
  { metodo: 'tarjeta', texto: 'Con POS', activo: true },
];
const URL = `/app/reservas/pagar?id=${ID}&cuota=${C1}`;

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
});

const preparar = async (page, { r = reserva(), metodos = METODOS, contacto = { texto: 'WhatsApp 999 000 111' } } = {}) => {
  await simular(page, 'GET', `/reservas/${ID}`, json(200, r));
  await simular(page, 'GET', '/instrucciones-pago', json(200, metodos));
  await simular(page, 'GET', '/contacto-estudio', json(200, contacto));
};
const archivo = (nombre = 'voucher.png', tipo = 'image/png', buffer = PNG) => ({ name: nombre, mimeType: tipo, buffer });
const llenar = async (page, { metodo = 'Yape', monto, operacion = 'op-12345', captura = archivo() } = {}) => {
  if (metodo) await page.getByRole('radio', { name: metodo }).check();
  if (monto !== undefined) await page.getByLabel(/Monto pagado/).fill(monto);
  await page.getByLabel(/Número de operación/).fill(operacion);
  if (captura) await page.getByLabel(/Captura del comprobante/).setInputFiles(captura);
};
const registrar = (page) => page.getByRole('button', { name: 'Registrar pago' });
const aviso = (page) => page.locator('[data-avisos] .aviso');

for (const t of tamanos) {
  test(`formulario: cuota, métodos, datos para pagar y monto prellenado, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await preparar(page);
    await page.goto(URL);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/registrar pago/i);
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reservas', 'R-2026-00001', 'Pagar']);
    const lateral = page.locator('aside');
    await expect(lateral).toContainText('R-2026-00001');
    await expect(lateral).toContainText('Grabación de voces');
    await expect(lateral).toContainText('Al reservar · 50 %');
    await expect(lateral).toContainText('S/ 207,50');
    await expect(lateral).toContainText('Paga antes de');
    await expect(lateral).toContainText('faltan 2 d 3 h');
    await expect(page.locator('input[type=radio]')).toHaveCount(4);
    expect(await page.locator('[data-metodos] .casilla-etiqueta').allTextContents()).toEqual(['Transferencia bancaria', 'Yape', 'Plin', 'Tarjeta']);
    await expect(page.getByText('En el POS del estudio o con el enlace del banco')).toBeVisible();
    await expect(page.getByText('Elige un método para ver los datos.')).toBeVisible();
    await page.getByRole('radio', { name: 'Transferencia bancaria' }).check();
    await expect(page.getByRole('heading', { level: 3 })).toHaveText(/datos para pagar con transferencia bancaria/i);
    await expect(page.locator('[data-datos-pago]')).toContainText('Cuenta 193-0000000-0-00');
    expect(await page.locator('[data-datos-pago] p').last().evaluate((e) => getComputedStyle(e).whiteSpace)).toBe('pre-line');
    await expect(page.locator('[data-datos-pago]')).toHaveAttribute('aria-live', 'polite');
    await expect(page.getByLabel(/Monto pagado/)).toHaveValue('207,50');
    await expect(page.getByLabel(/Número de operación/)).toHaveAttribute('autocomplete', 'off');
    await expect(page.getByLabel(/Número de operación/)).toHaveAttribute('spellcheck', 'false');
    await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/pago-formulario-${t.nombre}.png`, fullPage: true });
  });
}

test('un solo método activo viene marcado; los inactivos no se ofrecen', async ({ page }) => {
  await preparar(page, { metodos: [METODOS[1], { ...METODOS[2], activo: false }] });
  await page.goto(URL);
  await expect(page.locator('input[type=radio]')).toHaveCount(1);
  await expect(page.getByRole('radio', { name: 'Yape' })).toBeChecked();
  await expect(page.locator('[data-datos-pago]')).toContainText('Yape al 999 888 777');
});

test('el lateral muestra el último rechazo con su motivo', async ({ page }) => {
  const r = reserva();
  r.cuotas[0].pagos = [{ id: 'p1', estado: 'rechazado', metodo: 'yape', monto: '207.50', numero_operacion: 'X1', motivo_rechazo: 'La captura no se lee', registrado_en: '2026-11-16T15:20:00Z' }];
  await preparar(page, { r });
  await page.goto(URL);
  await expect(page.locator('aside')).toContainText('Rechazamos tu pago del 16 nov, 10:20: «La captura no se lee». Corrígelo y regístralo de nuevo.');
  await sinViolaciones(page);
});

test('monto distinto de la cuota: la ayuda lo dice y no es error', async ({ page }) => {
  await preparar(page);
  await page.goto(URL);
  const monto = page.getByLabel(/Monto pagado/);
  await expect(page.getByText('El que pagaste de verdad, con céntimos (225,00).')).toBeVisible();
  await monto.fill('100,00');
  await page.getByLabel(/Número de operación/).focus();
  await expect(page.getByText('No coincide con la cuota (S/ 207,50). Puedes registrarlo igual: el estudio lo revisará.')).toBeVisible();
  await expect(monto).not.toHaveAttribute('aria-invalid', 'true');
  await monto.fill('207,50');
  await page.getByLabel(/Número de operación/).focus();
  await expect(page.getByText('No coincide con la cuota')).toHaveCount(0);
});

test('validación local: resumen con enlaces, errores bajo cada campo y foco al aviso', async ({ page }) => {
  const posts = await simular(page, 'POST', '/pagos', json(201, {}));
  await preparar(page);
  await page.goto(URL);
  await page.getByLabel(/Monto pagado/).fill('0');
  await registrar(page).click();
  await expect(aviso(page)).toContainText('Revisa 4 campos');
  await expect(aviso(page)).toBeFocused();
  for (const t of ['Elige cómo pagaste.', 'Escribe el monto que pagaste, mayor que 0 (por ejemplo, 225,00).', 'Escribe el número de operación.', 'Adjunta la captura del comprobante.'])
    await expect(page.getByText(t, { exact: true }).first()).toBeVisible();
  await expect(aviso(page).getByRole('link')).toHaveCount(4);
  await expect(page.getByLabel(/Monto pagado/)).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByLabel(/Captura del comprobante/)).toHaveAttribute('aria-invalid', 'true');
  expect(posts).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pago-validacion.png', fullPage: true });
});

test('número de operación: de 4 a 40 letras, cifras o guiones', async ({ page }) => {
  const posts = await simular(page, 'POST', '/pagos', json(201, {}));
  await preparar(page);
  await page.goto(URL);
  await llenar(page, { operacion: 'ab c' });
  await registrar(page).click();
  await expect(page.getByText('Escribe de 4 a 40 letras, cifras o guiones.')).toBeVisible();
  expect(posts).toHaveLength(0);
});

test('captura: más de 5 MB y tipos no admitidos se avisan antes de enviar', async ({ page }) => {
  await preparar(page);
  await page.goto(URL);
  const entrada = page.getByLabel(/Captura del comprobante/);
  await entrada.setInputFiles(archivo('grande.png', 'image/png', Buffer.alloc(6 * 1024 * 1024)));
  await expect(page.getByText('La captura pesa 6 MB. Sube una de hasta 5 MB.').last()).toBeVisible();
  await entrada.setInputFiles(archivo('nota.txt', 'text/plain', Buffer.from('hola')));
  await expect(page.getByText('Sube la captura en JPG, PNG o PDF.').last()).toBeVisible();
  await entrada.setInputFiles(archivo());
  await expect(page.getByText('Sube la captura en JPG')).toHaveCount(0);
  await expect(page.locator('.archivo')).toContainText('voucher.png');
});

test('captura: miniatura de imagen, nombre de PDF y quitar devuelve el foco', async ({ page }) => {
  await preparar(page);
  await page.goto(URL);
  const entrada = page.getByLabel(/Captura del comprobante/);
  await entrada.setInputFiles(archivo());
  await expect(page.locator('.archivo-miniatura')).toHaveAttribute('alt', 'Vista previa de la captura voucher.png');
  await expect(page.locator('.archivo')).toContainText('PNG');
  await page.getByRole('button', { name: 'Quitar voucher.png' }).click();
  await expect(page.locator('.archivo')).toHaveCount(0);
  await expect(entrada).toBeFocused();
  await expect(page.locator('bugalu-carga-archivos [role="status"]')).toHaveText('Quitaste voucher.png. Elige otro archivo.');
  await entrada.setInputFiles(archivo('voucher.pdf', 'application/pdf', Buffer.from('%PDF-1.4')));
  await expect(page.locator('.archivo-miniatura')).toHaveCount(0);
  await expect(page.locator('.archivo')).toContainText('voucher.pdf');
  await expect(page.locator('.archivo')).toContainText('PDF');
  await sinViolaciones(page);
});

test('envío: multipart con los cinco campos, aviso y vuelta al detalle', async ({ page }) => {
  const consola = vigilarConsola(page);
  let peticion;
  await preparar(page);
  await page.route(`${API}/pagos`, (r) => { peticion = r.request(); return r.fulfill(json(201, { id: 'p1', estado: 'pendiente_validacion' })); });
  await page.goto(URL);
  await llenar(page, { monto: '207,5' });
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva({ pago_por_validar: true, cuotas: reserva().cuotas.map((c) => (c.id === C1 ? { ...c, estado: 'en_validacion', pagable: false, pagos: [{ id: 'p1', estado: 'pendiente_validacion', metodo: 'yape', monto: '207.50', numero_operacion: 'op-12345', motivo_rechazo: null, registrado_en: '2026-11-15T15:00:00Z' }] } : c)) })));
  await registrar(page).click();
  await page.waitForURL(`**/app/reservas/detalle?id=${ID}`);
  const cuerpo = peticion.postDataBuffer().toString('latin1');
  expect(peticion.headers()['content-type']).toMatch(/^multipart\/form-data; boundary=/);
  for (const [n, v] of [['id_cuota', C1], ['metodo', 'yape'], ['monto', '207.50'], ['numero_operacion', 'op-12345']]) expect(cuerpo).toMatch(new RegExp(`name="${n}"\\r\\n\\r\\n${v}\\r\\n`));
  expect(cuerpo).toContain('name="captura"; filename="voucher.png"');
  await expect(aviso(page)).toContainText('Pago registrado. Queda pendiente de validación.');
  await expect(aviso(page)).toContainText('Te avisaremos por correo cuando el estudio lo revise.');
  await expect(aviso(page)).toBeFocused();
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/pago-exito-detalle.png', fullPage: true });
});

test('enviando: un solo envío, botón en carga, campos bloqueados y aviso a los 10 s', async ({ page }) => {
  await page.clock.install({ time: AHORA });
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  let n = 0;
  await preparar(page);
  await page.route(`${API}/pagos`, async (r) => { n++; await espera; await r.fulfill(errorApi(503, 'x')); });
  await page.goto(URL);
  await llenar(page);
  await registrar(page).click();
  const boton = page.getByRole('button', { name: 'Registrando pago…' });
  await expect(boton).toHaveAttribute('aria-busy', 'true');
  await expect(boton).toBeDisabled();
  await expect(page.getByLabel(/Número de operación/)).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('aria-disabled', 'true');
  await expect(page.getByText('Subiendo la captura.')).toBeHidden();
  await page.clock.runFor(10500);
  await expect(page.getByText('Subiendo la captura. Con conexión lenta puede tardar un poco.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pago-enviando.png', fullPage: true });
  soltar();
  await expect(aviso(page)).toBeVisible();
  expect(n).toBe(1);
  await expect(page.getByText('Subiendo la captura.')).toBeHidden();
});

const errores = [
  ['409 operacion_duplicada', 409, 'operacion_duplicada', null, 'Revisa 1 campo'],
  ['413 archivo_muy_grande', 413, 'archivo_muy_grande', null, 'Revisa 1 campo'],
  ['422 formato_no_admitido', 422, 'formato_no_admitido', null, 'Revisa 1 campo'],
  ['422 datos_invalidos con campo', 422, 'datos_invalidos', { campo: 'monto' }, 'Revisa 1 campo'],
  ['422 datos_invalidos sin campo', 422, 'datos_invalidos', null, 'Monto fuera de rango.'],
  ['422 metodo_no_disponible', 422, 'metodo_no_disponible', null, 'Yape ya no está disponible. Elige otro método.'],
  ['503', 503, 'servicio_no_disponible', null, 'No pudimos registrar el pago: el servicio no responde. Tus datos siguen aquí; inténtalo en unos minutos.'],
];
for (const [nombre, estado, codigo, detalles, texto] of errores) {
  test(`envío: ${nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await preparar(page);
    await simular(page, 'POST', '/pagos', json(estado, { error: { codigo, mensaje: 'Monto fuera de rango.', detalles } }));
    await page.goto(URL);
    await llenar(page);
    await registrar(page).click();
    await expect(aviso(page)).toContainText(texto);
    await expect(aviso(page)).toBeFocused();
    await expect(page.getByLabel(/Número de operación/)).toHaveValue('op-12345');
    await expect(registrar(page)).toBeEnabled();
    await expect(page.getByLabel(/Captura del comprobante/)).toBeEnabled();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    if (codigo === 'operacion_duplicada') {
      await expect(page.locator('#pago-operacion-error')).toContainText('Ese número ya está registrado con Yape. Revisa el número del voucher.');
      await expect(page.getByLabel(/Número de operación/)).toHaveAttribute('aria-invalid', 'true');
      await page.screenshot({ path: 'pruebas/capturas/pago-error-duplicada.png', fullPage: true });
    }
    if (codigo === 'archivo_muy_grande') await expect(page.locator('#pago-captura-error')).toContainText('La captura es demasiado pesada para subirla. Sube una más ligera, de hasta 5 MB.');
    if (codigo === 'formato_no_admitido') await expect(page.locator('#pago-captura-error')).toContainText('Sube la captura en JPG, PNG o PDF.');
    if (codigo === 'datos_invalidos' && detalles) await expect(page.getByLabel(/Monto pagado/)).toHaveAttribute('aria-invalid', 'true');
  });
}

test('envío: red caída y respuesta que no es JSON avisan sin perder los datos', async ({ page }) => {
  await preparar(page);
  let modo = 'red';
  await page.route(`${API}/pagos`, (r) => (modo === 'red' ? r.abort('connectionrefused') : r.fulfill({ status: 201, contentType: 'text/html', body: '<h1>x</h1>' })));
  await page.goto(URL);
  await llenar(page);
  await registrar(page).click();
  await expect(aviso(page)).toContainText('Sin conexión. Tus datos siguen aquí; revisa tu red y vuelve a intentarlo.');
  modo = 'html';
  await registrar(page).click();
  await expect(aviso(page)).toContainText('Algo salió mal. Tus datos siguen aquí; inténtalo de nuevo.');
  await expect(aviso(page).getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
});

test('envío: 422 metodo_no_disponible recarga los métodos y conserva el resto', async ({ page }) => {
  let n = 0;
  await simular(page, 'GET', `/reservas/${ID}`, json(200, reserva()));
  await simular(page, 'GET', '/instrucciones-pago', (r) => r.fulfill(json(200, n++ ? [METODOS[0], METODOS[2]] : METODOS)));
  await simular(page, 'POST', '/pagos', json(422, { error: { codigo: 'metodo_no_disponible', mensaje: 'x' } }));
  await page.goto(URL);
  await llenar(page);
  await registrar(page).click();
  await expect(aviso(page)).toContainText('Yape ya no está disponible. Elige otro método.');
  await expect(page.locator('input[type=radio]')).toHaveCount(2);
  await expect(page.getByRole('radio', { name: 'Yape' })).toHaveCount(0);
  await expect(page.getByLabel(/Número de operación/)).toHaveValue('op-12345');
  await expect(page.locator('.archivo')).toContainText('voucher.png');
});

for (const [codigo, texto] of [['cuota_pagada', 'Esta cuota ya está pagada.'], ['pago_en_validacion', 'Ya registraste un pago para esta cuota. Te avisaremos por correo cuando el estudio lo revise.'], ['cuota_no_pagable', 'Esta cuota ya no admite pagos.']]) {
  test(`envío: 409 ${codigo} sustituye el formulario`, async ({ page }) => {
    await preparar(page);
    await simular(page, 'POST', '/pagos', json(409, { error: { codigo, mensaje: 'x' } }));
    await page.goto(URL);
    await llenar(page);
    await registrar(page).click();
    await expect(page.locator('[data-salida]')).toContainText(texto);
    await expect(page.locator('form')).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    await sinViolaciones(page);
  });
}

test('envío: 401 sustituye la vista con el enlace al acceso', async ({ page }) => {
  await preparar(page);
  const post = await simular(page, 'POST', '/pagos', (r) => r.fulfill(errorApi(401, 'no_autenticado')));
  await page.goto(URL);
  await llenar(page);
  await registrar(page).click();
  await expect(page.locator('[data-salida]').getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', `/acceso?volver=${encodeURIComponent(URL)}`);
  expect(post).toHaveLength(1);
});

// --- Cuotas que no se pueden pagar al cargar ---
const noPagables = [
  ['pagada', reserva({ cuotas: [{ id: C1, hito: 'al_reservar', monto: '207.50', estado: 'pagada', pagable: false, pagos: [] }] }), 'Esta cuota ya está pagada.'],
  ['en validación', reserva({ cuotas: [{ id: C1, hito: 'al_reservar', monto: '207.50', estado: 'en_validacion', pagable: false, pagos: [] }] }), 'Ya registraste un pago para esta cuota. Te avisaremos por correo cuando el estudio lo revise.'],
  ['reserva cancelada', reserva({ estado: 'cancelada', cuotas: [{ id: C1, hito: 'al_reservar', monto: '207.50', estado: 'pendiente', pagable: false, pagos: [] }] }), 'Esta reserva está cancelada: ya no admite pagos.'],
  ['al terminar sin confirmar', reserva({ cuotas: [{ id: C2, hito: 'al_terminar', monto: '207.50', estado: 'pendiente', pagable: false, pagos: [] }] }), 'El resto se paga cuando tu reserva esté confirmada.'],
];
for (const [nombre, r, texto] of noPagables) {
  test(`no pagable: ${nombre}`, async ({ page }) => {
    await preparar(page, { r });
    await page.goto(`/app/reservas/pagar?id=${ID}&cuota=${r.cuotas[0].id}`);
    await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
    await expect(page.locator('form')).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    for (const t of tamanos) {
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await sinViolaciones(page);
    }
    if (nombre === 'pagada') await page.screenshot({ path: 'pruebas/capturas/pago-no-pagable.png', fullPage: true });
  });
}

test('sin métodos activos: vacío con el contacto del estudio y sin formulario', async ({ page }) => {
  await preparar(page, { metodos: [] });
  await page.goto(URL);
  await expect(page.locator('[data-salida]')).toContainText('Por ahora no hay métodos de pago disponibles');
  await expect(page.locator('[data-salida]')).toContainText('Escríbele al estudio para pagar esta cuota.');
  await expect(page.locator('[data-salida]')).toContainText('WhatsApp 999 000 111');
  await expect(page.locator('form')).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/pago-sin-metodos.png', fullPage: true });
});

// --- URL y fallos de carga ---
test('id o cuota que no son UUID, o que faltan, no consultan la API', async ({ page }) => {
  const vistas = await simular(page, 'GET', '/reservas/abc', json(200, reserva()));
  for (const url of [`/app/reservas/pagar?id=abc&cuota=${C1}`, `/app/reservas/pagar?id=${ID}&cuota=1`, `/app/reservas/pagar?id=${ID}`, '/app/reservas/pagar']) {
    await page.goto(url);
    await expect(page.getByRole('heading', { name: /\[404\] Cuota no encontrada/i })).toBeVisible();
    await expect(page.locator('[data-salida]')).toContainText('No encontramos esta cuota en tu reserva.');
    await expect(page.getByRole('link', { name: 'Volver a mis reservas' })).toHaveAttribute('href', '/app/reservas/');
  }
  expect(vistas).toHaveLength(0);
  for (const t of tamanos) { await page.setViewportSize({ width: t.ancho, height: t.alto }); await sinViolaciones(page); }
  await page.screenshot({ path: 'pruebas/capturas/pago-cuota-no-encontrada.png', fullPage: true });
});

test('una cuota que no está en la reserva es "no encontrada"', async ({ page }) => {
  await preparar(page);
  await page.goto(`/app/reservas/pagar?id=${ID}&cuota=cccccccc-cccc-4ccc-8ccc-cccccccccccc`);
  await expect(page.locator('[data-salida]')).toContainText('No encontramos esta cuota en tu reserva.');
});

const fallos = [
  ['401', (r) => r.fulfill(errorApi(401, 'no_autenticado')), 'Tu sesión no es válida. Inicia sesión para ver tus reservas.', ['Ir al acceso', `/acceso?volver=${encodeURIComponent(URL)}`]],
  ['403', (r) => r.fulfill(errorApi(403, 'sin_permiso')), 'Esta reserva no es tuya.', ['Volver a mis reservas', '/app/reservas/']],
  ['404', (r) => r.fulfill(errorApi(404, 'reserva_no_encontrada')), 'No encontramos esta cuota en tu reserva.', ['Volver a mis reservas', '/app/reservas/']],
  ['503', (r) => r.fulfill(errorApi(503, 'x')), 'El servicio no responde. Inténtalo de nuevo en unos minutos.', null],
  ['red', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.', null],
  ['no-json', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>x</h1>' }), 'Algo salió mal. Inténtalo de nuevo.', null],
];
for (const [n, resp, texto, enlace] of fallos) {
  test(`carga: ${n} muestra su estado`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await preparar(page);
    await simular(page, 'GET', `/reservas/${ID}`, resp);
    await page.goto(URL);
    const a = page.locator('[data-salida] .aviso');
    await expect(a).toContainText(texto);
    if (enlace) await expect(a.getByRole('link', { name: enlace[0] })).toHaveAttribute('href', enlace[1]);
    else await expect(a.getByRole('button', { name: 'Reintentar' })).toBeVisible();
    for (const t of tamanos) { await page.setViewportSize({ width: t.ancho, height: t.alto }); await sinViolaciones(page); }
    expect(consola).toEqual([]);
  });
}

test('carga: el estado de carga usa aria-busy y Reintentar vuelve a pedir', async ({ page }) => {
  let soltar, intento = 0;
  const espera = new Promise((r) => (soltar = r));
  await preparar(page);
  await simular(page, 'GET', `/reservas/${ID}`, async (r) => { if (intento++) return r.fulfill(json(200, reserva())); await espera; await r.fulfill(errorApi(503, 'x')); });
  await page.goto(URL);
  await expect(page.getByText('Cargando…')).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(1);
  await sinViolaciones(page);
  soltar();
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.getByRole('radio', { name: 'Yape' })).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('avisa y no queda cargando', async ({ page }) => {
    await page.goto(URL);
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
    await expect(page.locator('bugalu-pago [data-salida]')).toBeHidden();
    await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
    await page.screenshot({ path: 'pruebas/capturas/pago-sin-js.png', fullPage: true });
  });
});

test('teclado: métodos con flechas, orden de foco y envío con Enter', async ({ page }) => {
  let n = 0;
  await preparar(page);
  await simular(page, 'POST', '/pagos', (r) => { n++; return r.fulfill(json(201, {})); });
  await page.goto(URL);
  await page.getByRole('radio', { name: 'Transferencia bancaria' }).focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('radio', { name: 'Yape' })).toBeChecked();
  await expect(page.locator('[data-datos-pago]')).toContainText('Yape al 999');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel(/Monto pagado/)).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel(/Número de operación/)).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel(/Captura del comprobante/)).toBeFocused();
  await page.getByLabel(/Número de operación/).fill('OP-9999');
  await page.getByLabel(/Captura del comprobante/).setInputFiles(archivo());
  await page.getByLabel(/Número de operación/).press('Enter');
  await expect.poll(() => n).toBe(1);
});

test('zoom 200 % y letra grande: nada se desborda', async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 600 }); // 1440 px a 200 %
  await preparar(page);
  await page.goto(URL);
  await page.getByRole('radio', { name: 'Transferencia bancaria' }).check();
  await page.addStyleTag({ content: 'html { font-size: 20px !important; }' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test('captura: al elegir, el foco pasa a Quitar y una region de estado anuncia el adjunto o el error', async ({ page }) => {
  await preparar(page);
  await page.goto(URL);
  const estado = page.locator('bugalu-carga-archivos [role="status"]');
  const entrada = page.getByLabel(/Captura del comprobante/);
  await entrada.focus(); // elegir con el selector del sistema deja el foco en el input
  await entrada.setInputFiles(archivo());
  await expect(page.getByRole('button', { name: 'Quitar voucher.png' })).toBeFocused();
  await expect(estado).toHaveText(/Adjuntaste voucher\.png \(PNG · \d+ KB\)/);
  await page.getByRole('button', { name: 'Quitar voucher.png' }).click();
  await entrada.setInputFiles(archivo('grande.png', 'image/png', Buffer.alloc(6 * 1024 * 1024)));
  await expect(estado).toHaveText('La captura pesa 6 MB. Sube una de hasta 5 MB.');
  await entrada.setInputFiles(archivo('nota.txt', 'text/plain', Buffer.from('hola')));
  await expect(estado).toHaveText('Sube la captura en JPG, PNG o PDF.');
});
