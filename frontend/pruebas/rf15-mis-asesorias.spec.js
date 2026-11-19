// RF-15 etapa B: Mis asesorias (lista y detalle del cliente), pago y reprogramar. La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { vista } from './ayudas-rf18.js';
import { AID, CUOTA, asesoria, confirmada, resumen, comoCliente, dentroDe } from './ayudas-rf15b.js';

const detalle = (page, a) => simular(page, 'GET', `/asesorias/${AID}`, json(200, a)).then(() => page.goto(`/app/asesorias/detalle?id=${AID}`));
const barra = (page) => page.locator('[data-estado-reserva]');

for (const t of tamanos) {
  test(`mis asesorias: lista con estados, POR CONFIRMAR y plazo a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page);
    await simular(page, 'GET', '/asesorias/mias', json(200, [resumen(), resumen({ id: 'x2', folio: 'A-2026-00002', estado: 'confirmada', encuentro_pendiente: false, vence_pago: null }), resumen({ id: 'x3', folio: 'A-2026-00003', estado: 'cancelada', vence_pago: null, encuentro_pendiente: false })]));
    await page.goto('/app/asesorias/mias');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mis asesorías');
    await expect(page.locator('[data-total]')).toHaveText('2 asesorías');
    await expect(page.getByText('Pendiente de pago').first()).toBeVisible();
    await expect(page.getByText(/por confirmar/i).first()).toBeVisible();
    await expect(page.getByText(/Paga antes del/).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Ver asesoría A-2026-00001/ })).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
    await expect(page.getByRole('link', { name: 'Asesorías' }).first()).toHaveAttribute('aria-current', 'page');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-mis-asesorias-${t.nombre}.png`, fullPage: true });
  });
}

test('mis asesorias: historial, vacio y fallos', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', '/asesorias/mias', json(200, []));
  await page.goto('/app/asesorias/mias');
  await expect(page.locator('.gestion-vacio-titulo')).toHaveText('Aún no tienes asesorías');
  await expect(page.getByRole('link', { name: 'Ver profesionales' })).toHaveAttribute('href', '/asesorias/');
  await simular(page, 'GET', '/asesorias/mias', json(200, [resumen({ estado: 'realizada' })]));
  await page.goto('/app/asesorias/mias?ver=historial');
  await expect(page.locator('[data-total]')).toHaveText('1 asesoría');
  for (const [resp, texto] of [[errorApi(401, 'no_autenticado'), 'Inicia sesión para ver tus asesorías.'], [errorApi(403, 'sin_permiso'), 'Esta sección es para artistas.'], [errorApi(503, 'servicio_no_disponible'), 'El servicio no responde']]) {
    await simular(page, 'GET', '/asesorias/mias', resp);
    await page.goto('/app/asesorias/mias');
    await expect(page.locator('[data-salida]')).toContainText(texto);
  }
});

for (const t of tamanos) {
  test(`detalle: pendiente de pago, virtual por confirmar, Registrar pago a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page);
    await simular(page, 'GET', `/reservas/${AID}/cancelacion`, json(200, vista(1)));
    await detalle(page, asesoria());
    await expect(page.getByRole('heading', { level: 1 })).toContainText('A-2026-00001');
    await expect(barra(page)).toContainText('Paga antes del');
    await expect(page.locator('[data-campo="modalidad"]')).toHaveText('Virtual (Google Meet)');
    await expect(page.getByText(/por confirmar/i).first()).toBeVisible();
    await expect(page.getByText('Ana Beat y el estudio te confirmarán el enlace antes de la cita.')).toBeVisible();
    await expect(page.getByRole('table', { name: 'Desglose del precio' })).toContainText('Asesoría de 1 h con Ana Beat');
    await expect(page.getByRole('table', { name: 'Cuotas' })).toContainText('Pago único');
    await expect(page.getByRole('link', { name: 'Registrar pago' })).toHaveAttribute('href', `/app/asesorias/pagar?id=${AID}&cuota=${CUOTA}`);
    await expect(page.getByRole('link', { name: 'Reprogramar' })).toHaveAttribute('href', `/app/asesorias/reprogramar?id=${AID}`);
    await expect(page.getByRole('link', { name: /versión 0.4.0/ })).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-detalle-pendiente-${t.nombre}.png`, fullPage: true });
  });
}

test('detalle: confirmada virtual con enlace muestra la videollamada; terminó, realizada y no asistió', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', `/reservas/${AID}/cancelacion`, json(200, vista(1)));
  await detalle(page, confirmada({ enlace: 'https://meet.google.com/abc-defg-hij' }));
  await expect(barra(page)).toContainText('Confirmada');
  await expect(barra(page)).toContainText('Te esperamos el 18 dic, a las 15:00.');
  const enlace = page.getByRole('link', { name: /Entrar a la videollamada/ });
  await expect(enlace).toHaveAttribute('href', 'https://meet.google.com/abc-defg-hij');
  await expect(enlace).toHaveAttribute('target', '_blank');
  await expect(page.getByText(/¿Necesitas cambiarlo\?/)).toBeVisible();
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, confirmada({ inicio: '2026-11-15T08:00:00-05:00', fin: '2026-11-15T09:00:00-05:00' })));
  await page.goto(`/app/asesorias/detalle?id=${AID}`);
  await expect(barra(page)).toContainText('Terminó');
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, confirmada({ estado: 'realizada', constancia_disponible: true })));
  await page.goto(`/app/asesorias/detalle?id=${AID}`);
  await expect(barra(page)).toContainText('Tu constancia de asistencia está lista.');
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, confirmada({ estado: 'no_asistio' })));
  await page.goto(`/app/asesorias/detalle?id=${AID}`);
  await expect(barra(page)).toContainText('Lo pagado no se devuelve.');
});

test('detalle: cancelar con la politica, sin devolucion en dinero', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', `/reservas/${AID}/cancelacion`, json(200, vista(1)));
  const cancelaciones = await simular(page, 'POST', `/reservas/${AID}/cancelar`, json(200, { ...confirmada(), estado: 'cancelada', cancelacion: { nivel: 1, aviso_en: dentroDe(0), por: 'cliente', pagado: '100.00', retenido: '0.00', credito: '100.00' } }));
  await detalle(page, confirmada());
  await page.getByRole('button', { name: 'Solicitar cancelación' }).click();
  await expect(page.getByText('Todo lo que pagaste pasa a crédito para otra reserva o asesoría tuya, sin devolución en dinero.')).toBeVisible();
  await page.getByRole('button', { name: 'Confirmar cancelación' }).click();
  await expect(page.locator('[data-avisos]')).toContainText('Asesoría cancelada');
  expect(cancelaciones[0].cuerpo).toEqual({ nivel_esperado: 1 });
});

test('detalle: 404 de una asesoria ajena y sin JS', async ({ page, browser }) => {
  await comoCliente(page);
  await simular(page, 'GET', `/asesorias/${AID}`, errorApi(404, 'no_encontrado'));
  await page.goto(`/app/asesorias/detalle?id=${AID}`);
  await expect(page.locator('.aviso-titulo', { hasText: 'No encontramos esta asesoría.' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a mis asesorías' })).toBeVisible();
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const sinJs = await ctx.newPage();
  await sinJs.goto('/app/asesorias/mias');
  expect(await sinJs.content()).toContain('Esta sección necesita JavaScript');
  await ctx.close();
});

// ---------- Pagar ----------
test('pagar: la cuota de la asesoria, sin sala ni anticipo', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, asesoria()));
  await simular(page, 'GET', '/instrucciones-pago', json(200, [{ metodo: 'yape', texto: 'Yapea al 999', activo: true }]));
  await simular(page, 'GET', '/creditos', json(200, []));
  await simular(page, 'GET', '/textos-legales', json(200, []));
  await page.goto(`/app/asesorias/pagar?id=${AID}&cuota=${CUOTA}`);
  await expect(page.locator('[data-campo="cuota"]')).toHaveText('Pago único');
  await expect(page.locator('[data-campo="servicio"]')).toHaveText('Ana Beat');
  await expect(page.getByText('Asesoría', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver a la asesoría' }).first()).toHaveAttribute('href', `/app/asesorias/detalle?id=${AID}`);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf15-pagar-1440.png', fullPage: true });
  // 403: cuenta de profesional
  await simular(page, 'GET', `/asesorias/${AID}`, errorApi(403, 'sin_permiso'));
  await page.goto(`/app/asesorias/pagar?id=${AID}&cuota=${CUOTA}`);
  await expect(page.locator('.aviso-titulo', { hasText: 'Las cuentas de profesional no registran pagos.' })).toBeVisible();
});

// ---------- Reprogramar ----------
test('reprogramar: mismo profesional y duracion; nivel 2 crea un pago nuevo y conserva el precio', async ({ page }) => {
  await comoCliente(page);
  const sim = { nivel: 2, penalizacion: '35.00', saldo: '35.00', credito: '0.00', reprogramaciones_restantes: 0 };
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, confirmada()));
  await simular(page, 'GET', `/reservas/${AID}/cancelacion`, json(200, vista(2)));
  const disp = await simular(page, 'GET', '/profesionales/p1/disponibilidad', json(200, { limites: { desde: '2026-11-15T10:00:00-05:00', hasta: '2027-01-15T10:00:00-05:00' }, horarios: [{ id: 'h', inicio: '2026-12-19T10:00:00-05:00', fin: '2026-12-19T13:00:00-05:00' }], ocupados: [], dias: [{ fecha: '2026-12-19', minutos_libres: 180 }], duraciones: [] }));
  await simular(page, 'POST', `/reservas/${AID}/reprogramar/simular`, json(200, sim));
  const envios = await simular(page, 'POST', `/reservas/${AID}/reprogramar`, json(200, confirmada()));
  await page.goto(`/app/asesorias/reprogramar?id=${AID}&fecha=2026-12-19`);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Reprogramar asesoría A-2026-00001');
  await expect(page.getByText('Tu asesoría dura 1 h: elige dónde empieza.')).toBeVisible();
  expect(disp[0].url.searchParams.get('excluir_asesoria')).toBe(AID);
  await page.locator('bugalu-calendario button[data-inicio]:visible').first().click();
  await expect(page.getByText('Precio de la asesoría (se conserva)')).toBeVisible();
  await expect(page.getByText('Se crea un pago de S/ 35,00 que haces hasta 48 h después de tu asesoría.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf15-reprogramar-1440.png', fullPage: true });
  await page.getByRole('button', { name: 'Confirmar reprogramación' }).click();
  await expect(page).toHaveURL(/asesorias\/detalle\?id=.*aviso=asesoria-reprogramada|asesorias\/detalle\?id=/);
  expect(envios[0].cuerpo).toMatchObject({ nivel_esperado: 2, total_esperado: '140.00' });
});

test('reprogramar: 409 no_cancelable explica que ya empezo', async ({ page }) => {
  await comoCliente(page);
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, confirmada()));
  await simular(page, 'GET', '/profesionales/p1/disponibilidad', json(200, { limites: { desde: '2026-11-15T10:00:00-05:00', hasta: '2027-01-15T10:00:00-05:00' }, horarios: [{ id: 'h', inicio: '2026-12-19T10:00:00-05:00', fin: '2026-12-19T13:00:00-05:00' }], ocupados: [], dias: [{ fecha: '2026-12-19', minutos_libres: 180 }], duraciones: [] }));
  await simular(page, 'POST', `/reservas/${AID}/reprogramar/simular`, errorApi(409, 'no_cancelable'));
  await page.goto(`/app/asesorias/reprogramar?id=${AID}&fecha=2026-12-19`);
  await page.locator('bugalu-calendario button[data-inicio]:visible').first().click();
  await expect(page.locator('.aviso-titulo', { hasText: 'Tu asesoría ya empezó: ya no se puede reprogramar.' })).toBeVisible();
});

test('el rol profesional ve su destino ASESORIAS y no el del cliente', async ({ page }) => {
  await comoCliente(page, 'profesional');
  await page.goto('/app/');
  await expect(page.locator('.app-nav-lateral a[href="/app/asesorias/agenda"]')).toBeVisible();
  await expect(page.locator('.app-nav-lateral a[href="/app/asesorias/mias"]')).toBeHidden();
});
