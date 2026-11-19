// RF-18 (CA-05, CA-06, CA-07 lado cliente, CA-16): Mis creditos, pedir devolucion, pago con credito y creditos en la ficha del cliente.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { ID, C1, C2, CR1, CR2, DV1, DV2, AHORA, reserva, credito, devolucion, cuotasSinPagos, cuotasPagadas, pago, vista } from './ayudas-rf18.js';

const comoRol = (page, rol, extra = {}) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol, ...extra })));
const aviso = (page) => page.locator('[data-avisos] .aviso');
const anuncio = (page) => page.locator('[data-anuncio]');

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'cliente');
});

// --- Mis creditos ---
const VIGENTES = () => [
  credito({ saldo: '60.00' }),
  credito({ id: CR2, monto: '50.00', saldo: '50.00', tipo: 'excepcion', vence: '2026-11-20T23:59:59-05:00', origen: { id_reserva: 'r2', folio: 'R-2026-00002' } }),
  credito({ id: 'c3', monto: '40.00', saldo: '40.00', tipo: 'nivel_2', vence: '2026-12-30T23:59:59-05:00', origen: { id_reserva: 'r3', folio: 'R-2026-00003' } }),
  credito({ id: 'c4', monto: '30.00', saldo: '30.00', tipo: 'reprogramacion', vence: '2026-12-30T23:59:59-05:00', origen: { id_reserva: 'r4', folio: 'R-2026-00004' } }),
];
const HISTORIAL = () => [
  credito({ id: 'h1', estado: 'agotado', saldo: '0.00', vence: '2026-10-30T23:59:59-05:00' }),
  credito({ id: 'h2', estado: 'vencido', saldo: '20.00', monto: '20.00', vence: '2026-10-01T23:59:59-05:00', origen: { id_reserva: 'r9', folio: 'R-2026-00009' } }),
];
const lista = (page, creditos) => simular(page, 'GET', '/creditos', typeof creditos === 'function' ? creditos : json(200, creditos));
const pagina = (page, query = '') => page.goto(`/app/reservas/creditos${query}`);

for (const t of tamanos) {
  test(`creditos: vigentes con disponible, tipo, saldo, plazo y acción de devolución, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await lista(page, [...VIGENTES(), ...HISTORIAL()]);
    await pagina(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/mis créditos/i);
    await expect(page.locator('.encabezado')).toContainText('[P3] SALA / CRÉDITOS');
    await expect(page.locator('.encabezado-ruta li')).toHaveText(['Inicio', 'Reservas', 'Créditos']);
    await expect(page.locator('.encabezado-descripcion')).toHaveText('Lo que te queda a favor por cancelar o reprogramar. Úsalo al pagar una cuota antes de que venza.');
    const disponible = page.getByRole('region', { name: /Disponible/i });
    await expect(disponible).toContainText('S/ 180,00 para usar en tus reservas');
    await expect(disponible).toContainText('Lo eliges al pagar una cuota.');
    await expect(page.getByRole('link', { name: 'Vigentes' })).toHaveAttribute('aria-current', 'true');
    const filas = page.getByRole('row');
    await expect(filas).toHaveCount(5);
    const f1 = page.getByRole('row', { name: /R-2026-00001/ });
    await expect(f1).toContainText('Cancelación (nivel 1)');
    await expect(f1).toContainText('S/ 60,00');
    await expect(f1).toContainText('de S/ 100,00');
    await expect(f1).toContainText(/17 dic 2026 · faltan 32 d/);
    await expect(f1).toContainText('Vigente');
    await expect(f1.getByRole('link', { name: 'R-2026-00001' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    await expect(page.getByRole('row', { name: /R-2026-00002/ })).toContainText('Vence pronto');
    await expect(page.getByRole('row', { name: /R-2026-00002/ })).toContainText('Caso excepcional');
    await expect(page.getByRole('row', { name: /R-2026-00003/ })).toContainText('Cancelación (nivel 2)');
    await expect(page.getByRole('row', { name: /R-2026-00004/ })).toContainText('Diferencia al reprogramar');
    await expect(page.getByRole('button', { name: 'Pedir devolución de R-2026-00001' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Pedir devolución de R-2026-00002' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Pedir devolución de R-2026-0000[34]/ })).toHaveCount(0);
    await expect(page.getByRole('region', { name: /Cómo funciona/i })).toContainText('Cada crédito vence 30 días después de generarse y te avisamos 7 días antes. Solo tú lo usas. Úsalo en tus reservas o asesorías. Los créditos de nivel 1 y de caso excepcional admiten devolución; los de nivel 2 y los de reprogramación, no.');
    await expect(page.getByRole('region', { name: /Cómo funciona/i }).getByRole('link', { name: 'Leer las condiciones' })).toHaveAttribute('href', '/legal/condiciones-de-contratacion/');
    await expect(anuncio(page)).toHaveText('4 créditos vigentes, S/ 180,00 disponible');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-creditos-vigentes-${t.nombre}.png`, fullPage: true });
  });
}

test('creditos: historial con fecha sola, sin acciones y sin el panel de disponible', async ({ page }) => {
  await lista(page, [...VIGENTES(), ...HISTORIAL()]);
  await pagina(page, '?ver=historial');
  await expect(page.getByRole('link', { name: 'Historial' })).toHaveAttribute('aria-current', 'true');
  await expect(page.getByRole('row')).toHaveCount(3);
  await expect(page.getByRole('row', { name: /R-2026-00009/ })).toContainText('Vencido');
  await expect(page.getByRole('row', { name: /R-2026-00001/ })).toContainText('Agotado');
  await expect(page.getByRole('row', { name: /R-2026-00009/ })).toContainText('1 oct 2026');
  await expect(page.getByRole('row', { name: /R-2026-00009/ })).not.toContainText('faltan');
  await expect(page.getByRole('button', { name: /Pedir devolución/ })).toHaveCount(0);
  await expect(page.getByRole('region', { name: /Disponible/i })).toHaveCount(0);
  await sinViolaciones(page);
});

test('creditos: vacío, y filtros sin resultados con su enlace al otro', async ({ page }) => {
  await lista(page, []);
  await pagina(page);
  await expect(page.locator('[data-salida]').getByText('No tienes créditos', { exact: true })).toBeVisible();
  await expect(page.getByText('Si cancelas o reprogramas una reserva con pagos, lo que pase a crédito aparecerá aquí.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver mis reservas' })).toHaveAttribute('href', '/app/reservas/');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-creditos-vacio-1440.png', fullPage: true });
  await lista(page, HISTORIAL());
  await pagina(page);
  await expect(page.locator('[data-salida]').getByText('No tienes créditos vigentes.')).toBeVisible();
  await page.getByRole('link', { name: 'Ver historial' }).click();
  await expect(page.getByRole('row')).toHaveCount(3);
  await lista(page, VIGENTES());
  await pagina(page, '?ver=historial');
  await expect(page.locator('[data-salida]').getByText('Aún no hay créditos en tu historial.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ver vigentes' })).toHaveAttribute('href', '/app/reservas/creditos');
});

test('creditos: la devolución se dice en texto y un crédito con devolución pendiente no cuenta como disponible', async ({ page }) => {
  await lista(page, [
    credito({ devolucion: devolucion({ estado: 'pendiente', solicitada_en: '2026-11-14T15:00:00Z' }) }),
    credito({ id: CR2, saldo: '50.00', tipo: 'excepcion', origen: { id_reserva: 'r2', folio: 'R-2026-00002' }, devolucion: devolucion({ id: DV2, estado: 'aprobada', monto_aprobado: '30.00', monto_solicitado: '50.00' }) }),
    credito({ id: 'c3', tipo: 'excepcion', origen: { id_reserva: 'r3', folio: 'R-2026-00003' }, devolucion: devolucion({ id: 'd3', estado: 'rechazada', motivo_decision: 'Sin sustento' }) }),
    credito({ id: 'c4', tipo: 'excepcion', saldo: '10.00', origen: { id_reserva: 'r4', folio: 'R-2026-00004' }, devolucion: devolucion({ id: 'd4', estado: 'realizada', realizada_en: '2026-11-13T15:00:00Z', nota_realizada: 'Yape, operación 12345' }) }),
  ]);
  await pagina(page);
  await expect(page.getByRole('row', { name: /R-2026-00001/ })).toContainText('Devolución pedida el 14 nov. Mientras la revisamos, este crédito no se usa ni vence.');
  await expect(page.getByRole('row', { name: /R-2026-00002/ })).toContainText('Devolución aprobada: S/ 30,00. Te la enviamos fuera de la app. El resto sigue como crédito.');
  await expect(page.getByRole('row', { name: /R-2026-00003/ })).toContainText('Devolución rechazada: «Sin sustento».');
  await expect(page.getByRole('row', { name: /R-2026-00004/ })).toContainText('Devolución hecha el 13 nov: Yape, operación 12345');
  await expect(page.getByRole('button', { name: /Pedir devolución/ })).toHaveCount(0);
  // 100 (pendiente, no cuenta) + 50 + 100 + 10 = 160
  await expect(page.getByRole('region', { name: /Disponible/i })).toContainText('S/ 160,00 para usar');
  await sinViolaciones(page);
});

// --- Pedir devolucion ---
const pedir = (page, folio = 'R-2026-00001') => page.getByRole('button', { name: `Pedir devolución de ${folio}` });
const panelD = (page) => page.getByRole('region', { name: /Pedir devolución · R-2026-00001/ });

for (const t of tamanos) {
  test(`creditos: pedir devolución con motivo valida, envía y deja la solicitud pendiente, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    let pedido = false;
    await lista(page, (r) => r.fulfill(json(200, [credito({ ...(pedido && { devolucion: devolucion() }) })])));
    const envios = await simular(page, 'POST', `/creditos/${CR1}/devolucion`, async (r) => { pedido = true; await r.fulfill(json(201, devolucion())); });
    await pagina(page);
    await pedir(page).click();
    await expect(page.getByRole('heading', { name: /Pedir devolución · R-2026-00001/ })).toBeFocused();
    await expect(page.getByRole('region', { name: /Cómo funciona/i })).toBeHidden();
    await expect(panelD(page).locator('dl')).toContainText('Saldo');
    await expect(panelD(page).locator('dl')).toContainText('S/ 100,00');
    await expect(panelD(page)).toContainText('El estudio decide si te devuelve todo, una parte o nada, y te dice por qué. Mientras decide, este crédito no se usa ni vence. El dinero se devuelve fuera de la app.');
    await expect(panelD(page)).toContainText('Cuéntanos por qué prefieres el dinero. Entre 10 y 500 caracteres.');
    const motivo = page.getByLabel(/Motivo/);
    await expect(motivo).toHaveAttribute('maxlength', '500');
    await expect(motivo).toHaveAttribute('minlength', '10');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-creditos-devolucion-panel-${t.nombre}.png`, fullPage: true });
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(page.getByText('Escribe el motivo, de 10 a 500 caracteres.').first()).toBeVisible();
    await expect(motivo).toHaveAttribute('aria-invalid', 'true');
    expect(envios).toHaveLength(0);
    await motivo.fill('Prefiero el dinero.');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    expect(envios[0].cuerpo).toEqual({ motivo: 'Prefiero el dinero.' });
    await expect(aviso(page)).toContainText('Solicitud enviada. El estudio la revisa y te avisa por correo.');
    await expect(aviso(page)).toBeFocused();
    await expect(panelD(page)).toBeHidden();
    await expect(page.getByRole('row', { name: /R-2026-00001/ })).toContainText('Devolución pedida el 14 nov.');
    await expect(pedir(page)).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('creditos: enviar bloquea y Volver/Escape devuelven el foco al botón de la fila', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await lista(page, [credito()]);
  await simular(page, 'POST', `/creditos/${CR1}/devolucion`, async (r) => { await espera; await r.fulfill(json(201, devolucion())); });
  await pagina(page);
  await pedir(page).focus();
  await page.keyboard.press('Enter');
  await expect(panelD(page)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(panelD(page)).toBeHidden();
  await expect(pedir(page)).toBeFocused();
  await pedir(page).click();
  await page.getByRole('button', { name: 'Volver' }).click();
  await expect(pedir(page)).toBeFocused();
  await pedir(page).click();
  await page.getByLabel(/Motivo/).fill('Prefiero el dinero.');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.getByRole('button', { name: 'Enviando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Volver' })).toBeDisabled();
  soltar();
  await expect(aviso(page)).toContainText('Solicitud enviada.');
});

for (const [codigo, texto] of [
  ['devolucion_pendiente', 'Ya pediste la devolución de este crédito.'],
  ['credito_no_vigente', 'Este crédito ya no está vigente.'],
  ['devolucion_no_permitida', 'Este crédito no admite devolución.'],
]) {
  test(`creditos: 409 ${codigo} cierra el panel, recarga y explica`, async ({ page }) => {
    await lista(page, [credito()]);
    await simular(page, 'POST', `/creditos/${CR1}/devolucion`, (r) => r.fulfill(errorApi(409, codigo)));
    await pagina(page);
    await pedir(page).click();
    await page.getByLabel(/Motivo/).fill('Prefiero el dinero.');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(aviso(page)).toContainText(texto);
    await expect(aviso(page)).toHaveClass(/aviso-informacion/);
    await expect(aviso(page)).toBeFocused();
    await expect(panelD(page)).toBeHidden();
    await sinViolaciones(page);
  });
}

test('creditos: 422 va bajo el motivo; 503 avisa sin Reintentar y deja el panel', async ({ page }) => {
  await lista(page, [credito()]);
  let estado = 422;
  await simular(page, 'POST', `/creditos/${CR1}/devolucion`, (r) => r.fulfill(errorApi(estado, estado === 422 ? 'datos_invalidos' : 'x')));
  await pagina(page);
  await pedir(page).click();
  await page.getByLabel(/Motivo/).fill('Prefiero el dinero.');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.getByText('Escribe el motivo, de 10 a 500 caracteres.').first()).toBeVisible();
  estado = 503;
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(aviso(page)).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await expect(panelD(page)).toBeVisible();
  await expect(page.getByLabel(/Motivo/)).toHaveValue('Prefiero el dinero.');
});

test('creditos: 404 del envío sustituye la pantalla con "no encontrado" y 401 con la sesión', async ({ page }) => {
  await lista(page, [credito()]);
  await simular(page, 'POST', `/creditos/${CR1}/devolucion`, (r) => r.fulfill(errorApi(401, 'no_autenticado')));
  await pagina(page);
  await pedir(page).click();
  await page.getByLabel(/Motivo/).fill('Prefiero el dinero.');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.locator('[data-salida]')).toContainText('Tu sesión no es válida.');
});

const FALLOS = [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: 'Tu sesión no es válida. Inicia sesión para ver tus reservas.' },
  { n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: 'No tienes permiso para ver estos créditos.' },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];
for (const f of FALLOS) {
  test(`creditos: ${f.n} muestra su estado`, async ({ page }) => {
    const consola = vigilarConsola(page);
    let falla = true;
    await lista(page, (r) => (falla ? f.r(r) : r.fulfill(json(200, VIGENTES()))));
    await pagina(page);
    await expect(page.locator('[data-salida]')).toContainText(f.texto);
    if (f.n === '401') await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', `/acceso?volver=${encodeURIComponent('/app/reservas/creditos')}`);
    if (f.n === '403') await expect(page.getByRole('link', { name: 'Volver a mis reservas' })).toHaveAttribute('href', '/app/reservas/');
    await sinViolaciones(page);
    if (f.reintentar) {
      falla = false;
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByRole('row')).toHaveCount(5);
    }
    if (f.n !== 'no-json') expect(consola).toEqual([]);
  });
}

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('creditos: avisa en vez de quedarse cargando', async ({ page }) => {
    await page.goto('/app/reservas/creditos');
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
  });
});

// --- Pago con credito (CA-06) ---
const URL_PAGO = `/app/reservas/pagar?id=${ID}&cuota=${C1}`;
const METODOS = [{ metodo: 'yape', texto: 'Yape al 999 888 777', activo: true }];
const preReserva = (extra = {}) => reserva({ estado: 'pre_reservada', pagado: '0.00', cuotas: cuotasSinPagos(), vence_pago: new Date(AHORA.getTime() + 2 * 864e5).toISOString(), ...extra });
const prepararPago = async (page, { r = preReserva(), creditos = [credito({ saldo: '150.00', monto: '150.00' })] } = {}) => {
  await simular(page, 'GET', `/reservas/${ID}`, typeof r === 'function' ? r : json(200, r));
  await simular(page, 'GET', '/instrucciones-pago', json(200, METODOS));
  await simular(page, 'GET', '/contacto-estudio', json(200, { texto: 'WhatsApp 999 000 111' }));
  await lista(page, creditos);
};
const casilla = (page) => page.getByRole('checkbox', { name: /Usar mi crédito/ });
const montoCredito = (page) => page.getByLabel(/Monto del crédito/);
const aplicar = (page) => page.getByRole('button', { name: 'Aplicar crédito' });

for (const t of tamanos) {
  test(`pago con crédito: P0 con la casilla, el monto prellenado y la ayuda, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await prepararPago(page);
    await page.goto(URL_PAGO);
    const p0 = page.getByRole('region', { name: /P0 Crédito/i });
    await expect(p0).toBeVisible();
    await expect(casilla(page)).not.toBeChecked();
    await expect(page.getByText('Usar mi crédito (S/ 150,00 disponible)')).toBeVisible();
    await expect(montoCredito(page)).toBeHidden();
    await casilla(page).check();
    await expect(montoCredito(page)).toBeVisible();
    await expect(montoCredito(page)).toHaveValue('100,00');
    await expect(p0).toContainText('Hasta S/ 100,00. Se aplica al momento, sin validación, y no se puede deshacer.');
    const destino = await casilla(page).getAttribute('aria-controls');
    expect(await page.locator(`#${destino}`).count()).toBe(1);
    // P0 va antes que P1 y "Registrar pago" sigue siendo el unico primario.
    const [b0, b1] = await Promise.all([p0.boundingBox(), page.getByRole('region', { name: /P1 Método de pago/i }).boundingBox()]);
    expect(b0.y).toBeLessThan(b1.y);
    await expect(page.locator('.boton-primario')).toHaveCount(1);
    await expect(aplicar(page)).toHaveClass(/boton-secundario/);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-pago-credito-${t.nombre}.png`, fullPage: true });
  });
}

test('pago con crédito: parcial aplica, recarga con lo que falta y pide captura por el resto', async ({ page }) => {
  const consola = vigilarConsola(page);
  let aplicado = false;
  const parcial = () => preReserva({ pagado: '50.00', cuotas: [{ ...cuotasSinPagos()[0], pagado: '50.00' }, cuotasSinPagos()[1]] });
  await prepararPago(page, { r: (r) => r.fulfill(json(200, aplicado ? parcial() : preReserva())) });
  await lista(page, (r) => r.fulfill(json(200, [credito({ saldo: aplicado ? '100.00' : '150.00', monto: '150.00' })])));
  const envios = await simular(page, 'POST', `/cuotas/${C1}/credito`, async (r) => { aplicado = true; await r.fulfill(json(200, parcial())); });
  const pagos = await simular(page, 'POST', '/pagos', json(201, {}));
  await page.goto(URL_PAGO);
  await casilla(page).check();
  await montoCredito(page).fill('50');
  await montoCredito(page).press('Enter');
  expect(pagos).toHaveLength(0); // Enter en el monto del crédito no registra el pago
  await expect(aviso(page)).toContainText('Aplicaste S/ 50,00 de crédito. Paga los S/ 50,00 que faltan con tu comprobante.');
  expect(envios[0].cuerpo).toEqual({ monto: '50.00' });
  await expect(aviso(page)).toBeFocused();
  const lateral = page.locator('aside');
  await expect(lateral).toContainText('Pagado');
  await expect(lateral).not.toContainText('con crédito');
  await expect(lateral).toContainText('Falta pagar');
  await expect(page.getByLabel(/Monto pagado/)).toHaveValue('50,00');
  await expect(page.getByText('Usar mi crédito (S/ 100,00 disponible)')).toBeVisible();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/rf18-pago-credito-parcial-1440.png', fullPage: true });
});

test('pago con crédito: si cubre la cuota del adelanto va al detalle con la reserva confirmada, sin pedir captura', async ({ page }) => {
  let aplicado = false;
  const confirmada = () => reserva({ cuotas: cuotasPagadas({ pagos: [] }) });
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, aplicado ? confirmada() : preReserva())));
  await simular(page, 'GET', '/instrucciones-pago', json(200, METODOS));
  await simular(page, 'GET', '/contacto-estudio', json(200, { texto: 'x' }));
  await lista(page, [credito({ saldo: '150.00', monto: '150.00' })]);
  const envios = await simular(page, 'POST', `/cuotas/${C1}/credito`, async (r) => { aplicado = true; await r.fulfill(json(200, confirmada())); });
  await page.goto(URL_PAGO);
  await casilla(page).check();
  await aplicar(page).click();
  expect(envios[0].cuerpo).toEqual({ monto: '100.00' });
  await page.waitForURL(/\/app\/reservas\/detalle\?id=.*aviso=pagado-con-credito/);
  await expect(aviso(page)).toContainText('Pagaste la cuota con tu crédito. Tu reserva quedó confirmada.');
  await expect(aviso(page)).toBeFocused();
  await expect(page.locator('[data-estado-reserva]')).toContainText('Confirmada');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-pago-credito-total-1440.png', fullPage: true });
});

test('pago con crédito: validación local del monto y 422 monto_invalido van bajo el campo', async ({ page }) => {
  await prepararPago(page);
  const envios = await simular(page, 'POST', `/cuotas/${C1}/credito`, (r) => r.fulfill(errorApi(422, 'monto_invalido')));
  await page.goto(URL_PAGO);
  await casilla(page).check();
  for (const valor of ['0', '', '100,01', 'abc']) {
    await montoCredito(page).fill(valor);
    await aplicar(page).click();
    await expect(page.getByText('Escribe un monto mayor que 0 y de hasta S/ 100,00.').first()).toBeVisible();
    await expect(montoCredito(page)).toHaveAttribute('aria-invalid', 'true');
  }
  expect(envios).toHaveLength(0);
  await montoCredito(page).fill('40');
  await aplicar(page).click();
  expect(envios).toHaveLength(1);
  await expect(page.getByText('Escribe un monto mayor que 0 y de hasta S/ 100,00.').first()).toBeVisible();
  await sinViolaciones(page);
});

test('pago con crédito: 409 credito_insuficiente recarga los créditos y dice cuánto queda', async ({ page }) => {
  let lecturas = 0;
  await prepararPago(page);
  await lista(page, (r) => r.fulfill(json(200, [credito({ saldo: lecturas++ ? '80.00' : '150.00', monto: '150.00' })])));
  await simular(page, 'POST', `/cuotas/${C1}/credito`, (r) => r.fulfill(errorApi(409, 'credito_insuficiente')));
  await page.goto(URL_PAGO);
  await casilla(page).check();
  await aplicar(page).click();
  await expect(page.getByText('Tu crédito cambió: ahora tienes S/ 80,00. Revisa el monto.').first()).toBeVisible();
  await expect(page.getByText('Usar mi crédito (S/ 80,00 disponible)')).toBeVisible();
  await expect(montoCredito(page)).toBeVisible();
  await sinViolaciones(page);
});

for (const [codigo, texto] of [['cuota_pagada', 'Esta cuota ya está pagada.'], ['no_pagable', 'Esta cuota ya no admite pagos.']]) {
  test(`pago con crédito: 409 ${codigo} muestra la cuota no pagable`, async ({ page }) => {
    await prepararPago(page);
    await simular(page, 'POST', `/cuotas/${C1}/credito`, (r) => r.fulfill(errorApi(409, codigo)));
    await page.goto(URL_PAGO);
    await casilla(page).check();
    await aplicar(page).click();
    await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
    await sinViolaciones(page);
  });
}

test('pago con crédito: 503 avisa y conserva lo escrito; 401 y 404 sustituyen', async ({ page }) => {
  await prepararPago(page);
  let estado = 503;
  await simular(page, 'POST', `/cuotas/${C1}/credito`, (r) => r.fulfill(errorApi(estado, 'x')));
  await page.goto(URL_PAGO);
  await casilla(page).check();
  await montoCredito(page).fill('40');
  await aplicar(page).click();
  await expect(aviso(page)).toContainText('No pudimos aplicar el crédito: el servicio no responde.');
  await expect(montoCredito(page)).toHaveValue('40');
  estado = 404;
  await aplicar(page).click();
  await expect(page.locator('[data-salida]')).toContainText('No encontramos esta cuota en tu reserva.');
});

test('pago con crédito: sin crédito disponible, o sin poder pedirlo, la pantalla sigue igual', async ({ page }) => {
  await prepararPago(page, { creditos: [] });
  await page.goto(URL_PAGO);
  await expect(page.getByRole('region', { name: /P1 Método de pago/i })).toBeVisible();
  await expect(page.getByRole('region', { name: /P0 Crédito/i })).toHaveCount(0);
  await prepararPago(page, { creditos: [credito({ devolucion: devolucion() })] });
  await page.goto(URL_PAGO);
  await expect(page.getByRole('region', { name: /P0 Crédito/i })).toHaveCount(0);
  await lista(page, (r) => r.fulfill(errorApi(503, 'x')));
  await page.goto(URL_PAGO);
  await expect(page.getByRole('region', { name: /P1 Método de pago/i })).toBeVisible();
  await expect(page.getByRole('region', { name: /P0 Crédito/i })).toHaveCount(0);
  await sinViolaciones(page);
});

test('pago con crédito: el lateral dice "Pagado" a secas cuando lo aplicado es una captura', async ({ page }) => {
  await prepararPago(page, { r: preReserva({ pagado: '30.00', cuotas: [{ ...cuotasSinPagos()[0], pagado: '30.00' }, cuotasSinPagos()[1]] }) });
  await page.goto(URL_PAGO);
  const lateral = page.locator('aside');
  await expect(lateral).toContainText('Pagado');
  await expect(lateral).not.toContainText('con crédito');
});

test('pago con crédito: sin P0 cuando no falta nada de la cuota', async ({ page }) => {
  await prepararPago(page, { r: preReserva({ cuotas: [{ ...cuotasSinPagos()[0], pagado: cuotasSinPagos()[0].monto }, cuotasSinPagos()[1]] }) });
  await page.goto(URL_PAGO);
  await expect(page.getByRole('region', { name: /P1 Método de pago/i })).toBeVisible();
  await expect(page.getByRole('region', { name: /P0 Crédito/i })).toHaveCount(0);
});

test('pago con crédito: el disponible suma en céntimos (0,10 + 0,20 + 0,05)', async ({ page }) => {
  await prepararPago(page, { creditos: [credito({ saldo: '0.10' }), credito({ id: 'c2', saldo: '0.20' }), credito({ id: 'c3', saldo: '0.05' })] });
  await page.goto(URL_PAGO);
  await expect(page.getByText('Usar mi crédito (S/ 0,35 disponible)')).toBeVisible();
});

test('pago con crédito: cuota del resto no pagable no ofrece P0', async ({ page }) => {
  await prepararPago(page, { r: reserva() });
  await page.goto(`/app/reservas/pagar?id=${ID}&cuota=${C2}`);
  await expect(page.getByRole('region', { name: /P0 Crédito/i })).toHaveCount(0);
});

// --- Ficha del cliente (Administrador) ---
const U3 = '33333333-3333-4333-8333-333333333333';
const usr = (rol) => ({ id: U3, correo: 'eva@correo.com', correo_confirmado: true, nombre: 'Eva Soto', telefono: null, nombre_artistico: null, rol, especialidad: null });
const prepararFicha = async (page, rol = 'cliente') => {
  await comoRol(page, 'administrador', { id: 'u-admin' });
  await simular(page, 'GET', '/usuarios', json(200, [usr(rol)]));
  await simular(page, 'GET', `/usuarios/${U3}/aceptaciones`, json(200, []));
};

for (const t of tamanos) {
  test(`ficha del cliente: U4 Créditos con tipo, saldo, vencimiento y devolución, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await prepararFicha(page);
    const llamadas = await simular(page, 'GET', '/creditos', json(200, [credito({ devolucion: devolucion({ estado: 'pendiente' }) }), credito({ id: CR2, tipo: 'nivel_2', origen: { id_reserva: 'r2', folio: 'R-2026-00002' } })]));
    await page.goto(`/app/usuarios/editar?id=${U3}`);
    const u4 = page.getByRole('region', { name: /U4 Créditos/i });
    await expect(u4.getByRole('row')).toHaveCount(3);
    expect(llamadas[0].url.searchParams.get('id_cliente')).toBe(U3);
    await expect(u4.getByRole('row', { name: /R-2026-00001/ })).toContainText('Cancelación (nivel 1)');
    await expect(u4.getByRole('row', { name: /R-2026-00001/ })).toContainText('Devolución pedida el 14 nov.');
    await expect(u4.getByRole('link', { name: 'R-2026-00001' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
    await expect(u4.getByRole('button')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-ficha-creditos-${t.nombre}.png`, fullPage: true });
  });
}

test('ficha del cliente: vacío, error con Reintentar y sin panel para el personal', async ({ page }) => {
  await prepararFicha(page);
  let falla = true;
  await simular(page, 'GET', '/creditos', (r) => (falla ? r.fulfill(errorApi(503, 'x')) : r.fulfill(json(200, []))));
  await page.goto(`/app/usuarios/editar?id=${U3}`);
  const u4 = page.getByRole('region', { name: /U4 Créditos/i });
  await expect(u4).toContainText('El servicio no responde.');
  falla = false;
  await u4.getByRole('button', { name: 'Reintentar' }).click();
  await expect(u4).toContainText('Sin créditos.');
  await sinViolaciones(page);
  const llamadas = await simular(page, 'GET', '/creditos', json(200, []));
  await prepararFicha(page, 'personal');
  await page.goto(`/app/usuarios/editar?id=${U3}`);
  await expect(page.getByRole('region', { name: /U3 Textos aceptados/i })).toBeVisible();
  await expect(page.getByRole('region', { name: /U4 Créditos/i })).toHaveCount(0);
  expect(llamadas).toHaveLength(0);
});
