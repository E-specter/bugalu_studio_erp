// RF-18 (CA-01..CA-03, CA-11 y CA-16, lado cliente): cancelar por niveles y lo que el detalle y la lista dicen despues.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { ID, C1, C2, AHORA, POLITICA, reserva, vista, cancelada, cuotasPagadas, cuotasSinPagos, pago } from './ayudas-rf18.js';

const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
const ver = (page, query = '') => page.goto(`/app/reservas/detalle?id=${ID}${query}`);
const con = (page, r) => simular(page, 'GET', `/reservas/${ID}`, json(200, r));
const previa = (page, v) => simular(page, 'GET', `/reservas/${ID}/cancelacion`, typeof v === 'function' ? v : json(200, v));
const barra = (page) => page.locator('[data-estado-reserva]');
const panel = (page) => page.getByRole('region', { name: /Cancelar reserva R-2026-00001/ });
const abrir = (page) => page.getByRole('button', { name: 'Solicitar cancelación' });
const confirmar = (page) => page.getByRole('button', { name: 'Confirmar cancelación' });
const aviso = (page) => page.locator('[data-avisos] .aviso');

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'cliente');
});

// --- Vista previa por nivel (CA-02) ---
const EJEMPLOS = [
  [1, ['Nivel 1: avisas con más de 48 h.', 'Faltan 2 d 6 h para tu sesión.', 'S/ 100,00', 'S/ 0,00', 'Todo lo que pagaste pasa a crédito para otra reserva tuya. Si prefieres el dinero, puedes pedir la devolución desde Mis créditos.']],
  [2, ['Nivel 2: avisas entre 24 y 48 h antes.', 'Faltan 1 d 6 h para tu sesión.', 'S/ 50,00', 'Se retiene una penalización del 25 % del total. El resto pasa a crédito para otra reserva tuya, sin devolución.']],
  [3, ['Nivel 3: avisas con 24 h o menos.', 'Faltan 10 h para tu sesión.', 'S/ 100,00', 'Se retiene todo lo que pagaste y no hay crédito.']],
];
for (const [nivel, textos] of EJEMPLOS) {
  for (const t of tamanos) {
    test(`cancelar: vista previa del nivel ${nivel}, a ${t.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await con(page, reserva());
      const vistas = await previa(page, vista(nivel));
      await ver(page);
      await abrir(page).click();
      await expect(panel(page)).toBeVisible();
      await expect(page.getByRole('heading', { name: /Cancelar reserva R-2026-00001/ })).toBeFocused();
      expect(vistas).toHaveLength(1);
      for (const texto of textos) await expect(panel(page)).toContainText(texto);
      const dl = panel(page).locator('dl');
      await expect(dl).toContainText('Pagado');
      await expect(dl).toContainText('Se retiene');
      await expect(dl).toContainText('Pasa a crédito');
      await expect(dl).toContainText('S/ 100,00');
      await expect(panel(page).getByRole('link', { name: 'Leer las condiciones de cancelación' })).toHaveAttribute('href', '/legal/condiciones-de-contratacion/');
      // Volver y Confirmar igual de visibles: mismo alto.
      const [v, c] = await Promise.all([page.getByRole('button', { name: 'Volver a la reserva' }).boundingBox(), confirmar(page).boundingBox()]);
      expect(Math.abs(v.height - c.height)).toBeLessThan(1);
      if (nivel === 3) await expect(dl).not.toContainText('El crédito vence');
      else await expect(dl).toContainText('El crédito vence');
      if (nivel !== 3) await expect(dl).toContainText('15 dic 2026');
      await expect(page.getByRole('link', { name: /Reprogramar/ })).toHaveCount(0);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      if (nivel === 2) await page.screenshot({ path: `pruebas/capturas/rf18-cancelar-nivel2-${t.nombre}.png`, fullPage: true });
    });
  }
}

test('cancelar: el pago en validacion se explica segun el nivel', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2, { en_validacion: '30.00' }));
  await ver(page);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Tienes S/ 30,00 en validación. Si el estudio lo aprueba, se sumará a tu crédito.');
  await expect(panel(page).locator('dl')).toContainText('En validación');
  await previa(page, vista(3, { en_validacion: '30.00' }));
  await page.getByRole('button', { name: 'Volver a la reserva' }).click();
  await abrir(page).click();
  await expect(panel(page)).toContainText('Si el estudio lo aprueba, también se retendrá.');
});

test('cancelar: abrir pide la vista previa y deja el panel en carga, sin botones, hasta que llega', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await con(page, reserva());
  await previa(page, async (r) => { await espera; await r.fulfill(json(200, vista(2))); });
  await ver(page);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Calculando qué pasa con tu pago…');
  await expect(panel(page).locator('[aria-busy="true"]')).toHaveCount(1);
  await expect(confirmar(page)).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeVisible();
  soltar();
  await expect(confirmar(page)).toBeVisible();
  await expect(page.locator('[data-anuncio]')).toContainText('Vista previa lista: nivel 2, se retienen S/ 50,00.');
});

// --- Confirmar ---
test('cancelar: confirmar nivel 2 manda nivel_esperado y deja el bloque de cancelacion', async ({ page }) => {
  const consola = vigilarConsola(page);
  await con(page, reserva());
  await previa(page, vista(2));
  const cancelar = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, cancelada(2)));
  page.on('dialog', (d) => { throw new Error(`diálogo nativo: ${d.message()}`); });
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  expect(cancelar).toHaveLength(1);
  expect(cancelar[0].cuerpo).toEqual({ nivel_esperado: 2 });
  await expect(aviso(page)).toContainText('Reserva cancelada. S/ 50,00 pasaron a crédito hasta el 15 dic 2026. Te enviamos el detalle por correo.');
  await expect(aviso(page)).toBeFocused();
  await expect(panel(page)).toBeHidden();
  await expect(barra(page)).toContainText('Cancelada');
  await expect(barra(page)).toContainText('S/ 50,00 pasaron a crédito. Úsalo en otra reserva.');
  const d4 = page.getByRole('region', { name: /D4 Cancelación/i });
  await expect(d4).toContainText('Aviso');
  await expect(d4).toContainText('Tuyo');
  await expect(d4).toContainText('Nivel 2: avisas entre 24 y 48 h antes.');
  await expect(d4).toContainText('Retenido');
  await expect(d4).toContainText('S/ 50,00');
  await expect(d4.getByRole('link', { name: 'Ver mis créditos' })).toHaveAttribute('href', '/app/reservas/creditos');
  await expect(page.getByRole('row', { name: /Al terminar/ })).toContainText('Anulada');
  await expect(page.getByRole('row', { name: /Al terminar/ })).toContainText('Se anuló al cancelar.');
  await expect(page.getByRole('button', { name: /Solicitar cancelación/ })).toHaveCount(0);
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/rf18-cancelar-exito-1440.png', fullPage: true });
});

test('cancelar: nivel 3 deja el texto de lo retenido y no promete credito', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(3));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, cancelada(3)));
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(aviso(page)).toContainText('Reserva cancelada. Se retuvo lo pagado (S/ 100,00). Te enviamos el detalle por correo.');
  await expect(barra(page)).toContainText('Se retuvo lo pagado (S/ 100,00), como indican las condiciones.');
  await expect(page.getByRole('region', { name: /D4 Cancelación/i }).getByRole('link', { name: 'Ver mis créditos' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toContainText('Nada');
  await sinViolaciones(page);
});

test('cancelar: sin pagos sigue siendo gratis, sin nivel_esperado ni cuerpo', async ({ page }) => {
  await con(page, reserva({ estado: 'pre_reservada', cuotas: cuotasSinPagos(), pagado: '0.00', vence_pago: new Date(AHORA.getTime() + 2 * 864e5).toISOString() }));
  await previa(page, vista(null));
  const cancelar = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, reserva({ estado: 'cancelada', motivo_cancelacion: 'cliente', cuotas: cuotasSinPagos(), pagado: '0.00' })));
  await ver(page);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Sin pagos: cancelas gratis.');
  await expect(panel(page)).toContainText('El horario se libera al momento y no se te cobra nada. No se puede deshacer');
  await expect(panel(page).locator('dl')).toBeHidden();
  await confirmar(page).click();
  expect(cancelar[0].cuerpo).toBeNull();
  await expect(aviso(page)).toContainText('Reserva cancelada. El horario quedó libre y no se te cobró nada.');
  await expect(barra(page)).toContainText('La cancelaste.');
  await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toHaveCount(0);
});

test('cancelar: nivel_cambiado repinta la vista previa, avisa y exige confirmar otra vez', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(1));
  let intento = 0;
  const cancelar = await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => (intento++ ? r.fulfill(json(200, cancelada(2))) : r.fulfill(json(409, { error: { codigo: 'nivel_cambiado', mensaje: 'x', detalles: vista(2) } }))));
  await ver(page);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Nivel 1: avisas con más de 48 h.');
  await confirmar(page).click();
  const nota = panel(page).locator('.aviso');
  await expect(nota).toContainText('Mientras lo revisabas pasó un plazo: ahora es nivel 2. Revisa qué pasa con tu pago y confirma de nuevo.');
  await expect(nota).toBeFocused();
  await expect(panel(page)).toContainText('Nivel 2: avisas entre 24 y 48 h antes.');
  await expect(panel(page)).toContainText('Se retiene una penalización del 25 %');
  await expect(confirmar(page)).toBeEnabled();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-cancelar-nivel-cambiado-1440.png', fullPage: true });
  expect(cancelar).toHaveLength(1);
  await confirmar(page).click();
  expect(cancelar).toHaveLength(2);
  expect(cancelar[1].cuerpo).toEqual({ nivel_esperado: 2 });
  await expect(aviso(page)).toContainText('Reserva cancelada.');
});

test('cancelar: enviando muestra "Cancelando…" y bloquea Volver', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await con(page, reserva());
  await previa(page, vista(2));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, async (r) => { await espera; await r.fulfill(json(200, cancelada(2))); });
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(page.getByRole('button', { name: 'Cancelando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeDisabled();
  soltar();
  await expect(aviso(page)).toContainText('Reserva cancelada');
});

// --- Teclado y foco ---
test('cancelar: teclado, Escape y Volver devuelven el foco al botón', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2));
  const cancelar = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, cancelada(2)));
  await ver(page);
  await abrir(page).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: /Cancelar reserva R-2026-00001/ })).toBeFocused();
  await expect(confirmar(page)).toBeVisible();
  // Orden de foco: condiciones, Volver, Confirmar.
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Leer las condiciones de cancelación' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(confirmar(page)).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(panel(page)).toBeHidden();
  await expect(abrir(page)).toBeFocused();
  await abrir(page).click();
  await page.getByRole('button', { name: 'Volver a la reserva' }).click();
  await expect(abrir(page)).toBeFocused();
  expect(cancelar).toHaveLength(0);
});

// --- Errores ---
const FALLOS_PREVIA = [
  ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde. Inténtalo de nuevo en unos minutos.'],
  ['red', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.'],
  ['no-json', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), 'Algo salió mal. Inténtalo de nuevo.'],
];
for (const [n, respuesta, texto] of FALLOS_PREVIA) {
  test(`cancelar: error al pedir la vista previa (${n}) no ofrece confirmar y permite reintentar`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await con(page, reserva());
    let falla = true;
    await previa(page, (r) => (falla ? respuesta(r) : r.fulfill(json(200, vista(2)))));
    await ver(page);
    await abrir(page).click();
    await expect(panel(page).locator('.aviso-error')).toContainText(texto);
    await expect(confirmar(page)).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-cancelar-error-${n}.png`, fullPage: true });
    falla = false;
    await panel(page).getByRole('button', { name: 'Reintentar' }).click();
    await expect(confirmar(page)).toBeVisible();
    if (n !== 'no-json') expect(consola).toEqual([]);
  });
}

test('cancelar: 409 no_cancelable al abrir cierra el panel y explica el estado', async ({ page }) => {
  let lecturas = 0;
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, lecturas++ ? reserva({ estado: 'en_curso' }) : reserva())));
  await previa(page, (r) => r.fulfill(errorApi(409, 'no_cancelable')));
  await ver(page);
  await abrir(page).click();
  await expect(aviso(page)).toContainText('Esta reserva ya no se puede cancelar: está en curso.');
  await expect(aviso(page)).toHaveClass(/aviso-informacion/);
  await expect(aviso(page)).toBeFocused();
  await expect(panel(page)).toBeHidden();
  await expect(abrir(page)).toHaveCount(0);
  await sinViolaciones(page);
});

test('cancelar: 409 no_cancelable al confirmar cierra el panel y explica el estado', async ({ page }) => {
  let lecturas = 0;
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, lecturas++ ? reserva({ estado: 'en_curso' }) : reserva())));
  await previa(page, vista(2));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(409, 'no_cancelable')));
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(aviso(page)).toContainText('Esta reserva ya no se puede cancelar: está en curso.');
  await expect(panel(page)).toBeHidden();
});

test('cancelar: error al confirmar (503) conserva la vista previa y no ofrece Reintentar', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(503, 'x')));
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(aviso(page)).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await expect(panel(page)).toContainText('Nivel 2: avisas entre 24 y 48 h antes.');
  await expect(confirmar(page)).toBeEnabled();
});

test('cancelar: 401 al confirmar muestra la sesión no válida', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(401, 'no_autenticado')));
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(page.locator('[data-salida]')).toContainText('Tu sesión no es válida. Inicia sesión para ver tus reservas.');
});

test('cancelar: 404 al confirmar muestra "no encontrada"', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(404, 'no_encontrada')));
  await ver(page);
  await abrir(page).click();
  await confirmar(page).click();
  await expect(page.locator('[data-salida]')).toContainText('No encontramos esta reserva.');
});

test('cancelar: 403 de la vista previa sustituye la pantalla', async ({ page }) => {
  await con(page, reserva());
  await previa(page, (r) => r.fulfill(errorApi(403, 'sin_permiso')));
  await ver(page);
  await abrir(page).click();
  await expect(page.locator('[data-salida]')).toContainText('Esta reserva no es tuya.');
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('cancelar: la pantalla avisa en vez de quedarse cargando', async ({ page }) => {
    await page.goto(`/app/reservas/detalle?id=${ID}`);
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
    await expect(page.getByRole('button', { name: /Solicitar cancelación/ })).toHaveCount(0);
  });
});

// --- Detalle: estados nuevos (CA-11, CA-16) ---
test('detalle: No asistió dice qué se retuvo y no ofrece cancelar', async ({ page }) => {
  await con(page, reserva({ estado: 'no_asistio', cuotas: cuotasPagadas({}, { estado: 'anulada' }), inicio: '2026-11-14T10:00:00-05:00', fin: '2026-11-14T12:00:00-05:00' }));
  await ver(page);
  await expect(barra(page)).toContainText('No asistió');
  await expect(barra(page)).toContainText('No llegaste en los primeros 15 minutos. Se retuvo lo pagado (S/ 100,00); no hay crédito ni cobro adicional.');
  await expect(page.getByRole('region', { name: /D1 Reserva/ })).toContainText('No asistió');
  await expect(page.getByRole('row', { name: /Al terminar/ })).toContainText('Se anuló por la inasistencia.');
  await expect(abrir(page)).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-detalle-no-asistio-1440.png', fullPage: true });
});

test('detalle: cuota con pagado parcial dice cuánto falta, en texto', async ({ page }) => {
  await con(page, reserva({ cuotas: cuotasPagadas({ estado: 'pendiente', pagable: true, pagado: '50.00', pagos: [] }) }));
  await ver(page);
  const fila = page.getByRole('row', { name: /Al reservar/ });
  await expect(fila).toContainText('Pendiente');
  await expect(fila).toContainText('Pagado S/ 50,00 · falta S/ 50,00');
  await sinViolaciones(page);
});

test('detalle: cancelada con excepción y con reprogramaciones muestra D4 y D5', async ({ page }) => {
  const base = cancelada(2);
  await con(page, { ...base, cancelacion: { ...base.cancelacion, nota: 'Nos escribió por WhatsApp', excepcion: { motivo: 'Duelo familiar', por: 'Ana', en: '2026-11-20T15:00:00-05:00' } },
    reprogramaciones: [
      { anterior_inicio: '2026-12-10T10:00:00-05:00', nuevo_inicio: '2026-12-12T10:00:00-05:00', nivel: 1, penalizacion: '0.00', total_anterior: '200.00', total_nuevo: '200.00', por: 'cliente', en: '2026-11-01T10:00:00-05:00' },
      { anterior_inicio: '2026-12-12T10:00:00-05:00', nuevo_inicio: '2026-12-18T15:00:00-05:00', nivel: 2, penalizacion: '50.00', total_anterior: '200.00', total_nuevo: '240.00', por: 'cliente', en: '2026-11-05T10:00:00-05:00' },
      { anterior_inicio: '2026-12-18T15:00:00-05:00', nuevo_inicio: '2026-12-19T15:00:00-05:00', nivel: null, penalizacion: '0.00', total_anterior: '240.00', total_nuevo: '240.00', por: 'estudio', en: '2026-11-08T10:00:00-05:00' },
    ] });
  await ver(page);
  const d4 = page.getByRole('region', { name: /D4 Cancelación/i });
  await expect(d4).toContainText('Nos escribió por WhatsApp');
  await expect(d4).toContainText('Tratada como nivel 1 el 20 nov: Duelo familiar');
  const d5 = page.getByRole('region', { name: /D5 Reprogramaciones/i });
  const filas = d5.getByRole('row');
  await expect(filas).toHaveCount(4);
  await expect(filas.nth(1)).toContainText('Sin costo');
  await expect(filas.nth(2)).toContainText('Nivel 2');
  await expect(filas.nth(2)).toContainText('S/ 200,00 → S/ 240,00');
  await expect(filas.nth(3)).toContainText('Nivel 1');
  await expect(d5.locator('caption')).toHaveCount(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-detalle-d4-d5-1440.png', fullPage: true });
});

test('detalle: el personal ve D4 sin acciones de cancelar ni "Ver mis créditos"', async ({ page }) => {
  await comoRol(page, 'personal');
  await con(page, { ...cancelada(2), cliente: 'Ana Pérez' });
  await ver(page);
  const d4 = page.getByRole('region', { name: /D4 Cancelación/i });
  await expect(d4).toContainText('Del cliente');
  await expect(d4.getByRole('link', { name: 'Ver mis créditos' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /cancel/i })).toHaveCount(0);
});

test('detalle: el cliente no ve las acciones del Administrador', async ({ page }) => {
  await con(page, reserva({ estado: 'no_asistio', cuotas: cuotasPagadas({}, { estado: 'anulada' }), inicio: '2026-11-14T10:00:00-05:00', fin: '2026-11-14T12:00:00-05:00' }));
  await ver(page);
  await expect(page.getByRole('button', { name: /Marcar no asistió|Tratar como nivel 1|Cancelar reserva/ })).toHaveCount(0);
});

test('detalle: no ofrece reprogramar (es de otra tarea)', async ({ page }) => {
  await con(page, reserva());
  await ver(page);
  await expect(page.getByRole('link', { name: /Reprogramar/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Reprogramar/ })).toHaveCount(0);
});

test('detalle: pre-reservada con pagos en validación se cancela con vista previa (ya no "pídelo al estudio")', async ({ page }) => {
  await con(page, reserva({ estado: 'pre_reservada', pago_por_validar: true, cuotas: cuotasPagadas({ estado: 'en_validacion', pagado: '0.00', pagos: [pago({ estado: 'pendiente_validacion' })] }), pagado: '0.00' }));
  await previa(page, vista(2, { pagado: '0.00', en_validacion: '100.00', retenido: '0.00', credito: '0.00', credito_vence: null }));
  await ver(page);
  await expect(page.getByText('Ya registraste un pago, así que la cancelación la gestiona el estudio.')).toHaveCount(0);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Tienes S/ 100,00 en validación.');
});

test('detalle: una reserva que ya empezó no ofrece cancelar', async ({ page }) => {
  await con(page, reserva({ inicio: '2026-11-15T09:00:00-05:00', fin: '2026-11-15T12:00:00-05:00' }));
  await ver(page);
  await expect(abrir(page)).toHaveCount(0);
});

// --- Lista ---
test('lista: No asistió va al historial con PAGO "—" y su etiqueta en texto', async ({ page }) => {
  const lista = [
    reserva({ id: 'a', folio: 'A-1', estado: 'no_asistio', cuotas: cuotasPagadas({}, { estado: 'anulada' }), inicio: '2026-11-10T10:00:00-05:00', fin: '2026-11-10T12:00:00-05:00' }),
    reserva({ id: 'b', folio: 'B-2' }),
  ];
  await simular(page, 'GET', '/reservas/mias', json(200, lista));
  await page.goto('/app/reservas/?ver=historial');
  const fila = page.getByRole('row', { name: /A-1/ });
  await expect(fila).toContainText('No asistió');
  await expect(fila.getByRole('cell').nth(3)).toHaveText('—');
  await expect(page.getByRole('row', { name: /B-2/ })).toHaveCount(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-lista-no-asistio-1440.png', fullPage: true });
});

test('lista: suma "Mis créditos" en las acciones del encabezado', async ({ page }) => {
  await simular(page, 'GET', '/reservas/mias', json(200, [reserva()]));
  await page.goto('/app/reservas/');
  await expect(page.getByRole('link', { name: 'Mis créditos' })).toHaveAttribute('href', '/app/reservas/creditos');
  await expect(page.getByRole('link', { name: 'Reservar sala' }).first()).toBeVisible();
});

test('politica: sin la cifra de la política el texto no inventa plazos', async ({ page }) => {
  await con(page, reserva({ politica: undefined }));
  await previa(page, vista(2));
  await ver(page);
  await abrir(page).click();
  await expect(panel(page)).toContainText('Nivel 2: avisas con poco tiempo.');
  await expect(panel(page)).toContainText('Se retiene una penalización.');
  expect(POLITICA.horas_nivel_1).toBe(48);
});
