// RF-15 etapa B: detalle de la asesoria para el profesional y el Administrador (spec RF-15-gestion). La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { json, errorApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { AID, PROF, asesoria, confirmada, comoCliente, dentroDe, paraAdmin, paraProfesional } from './ayudas-rf15b.js';

const sinDesborde = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const URL_DETALLE = `/app/asesorias/detalle?id=${AID}`;
const ver = async (page, a, consulta = '') => {
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, a));
  await page.goto(URL_DETALLE + consulta);
};
const panelLugar = (page) => page.getByRole('region', { name: /Lugar o enlace · A-2026-00001/ });
const aviso = (page) => page.locator('[data-avisos] .aviso');
// Una confirmada dentro de una semana (virtual, sin enlace): lo que el profesional y el Administrador completan.
const proxima = (extra = {}) => confirmada({ inicio: dentroDe(3 * 24 * 60), fin: dentroDe(3 * 24 * 60 + 60), ...extra });

for (const t of tamanos) {
  test(`detalle del profesional: D0 CLIENTE, sin pagos ni condiciones, lugar por confirmar y pedir al Administrador a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(proxima()));
    await expect(page.getByRole('heading', { level: 1 })).toContainText('A-2026-00001');
    await expect(page.locator('.encabezado-descripcion')).toContainText('Con Lu Beats ·');
    await expect(page.locator('.encabezado-indice')).toHaveText('[E3] ASESORÍAS / AGENDA');
    await expect(page.locator('.encabezado-ruta a', { hasText: 'Asesorías' })).toHaveAttribute('href', '/app/asesorias/agenda');
    const d0 = page.getByRole('region', { name: /D0 Cliente/i });
    await expect(d0).toContainText('Lu Beats');
    await expect(d0).toContainText('Luis Mora');
    await expect(d0.getByRole('link', { name: '999 111 222' })).toHaveAttribute('href', 'tel:999111222');
    await expect(d0.getByRole('link', { name: 'luis@correo.com' })).toHaveAttribute('href', 'mailto:luis@correo.com');
    await expect(page.getByRole('region', { name: /D2 Precio/i })).toHaveCount(0);
    await expect(page.getByRole('region', { name: /D3 Cuotas/i })).toHaveCount(0);
    await expect(page.locator('dt', { hasText: 'Condiciones' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /Cancelar asesoría|Solicitar cancelación/ })).toHaveCount(0);
    await expect(page.getByText('¿No puedes darla? Pide al Administrador que la cancele por el estudio. El cliente podrá reprogramar contigo sin costo o pedir la devolución.')).toBeVisible();
    await expect(page.getByText('Falta confirmar el enlace')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Registrar enlace' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Asesorías' }).first()).toHaveAttribute('aria-current', 'page');
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-gestion-profesional-${t.nombre}.png`, fullPage: true });
  });
}

for (const t of tamanos) {
  test(`detalle del Administrador: cliente, precio, cuotas y cancelar a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(proxima({ enlace: 'https://meet.google.com/abc-defg-hij' })));
    await expect(page.locator('.encabezado-descripcion')).toContainText('Lu Beats con Ana Beat ·');
    await expect(page.locator('.encabezado-indice')).toHaveText('[A15] ASESORÍAS / AGENDA');
    await expect(page.locator('.encabezado-ruta a')).toHaveText(['Inicio', 'Asesorías', 'Agendadas']);
    await expect(page.locator('.encabezado-ruta a').nth(2)).toHaveAttribute('href', '/app/asesorias/agenda');
    await expect(page.getByRole('region', { name: /D0 Cliente/i })).toContainText('luis@correo.com');
    await expect(page.getByRole('region', { name: /D2 Precio/i })).toContainText('Asesoría de 1 h con Ana Beat');
    await expect(page.getByRole('region', { name: /D3 Cuotas/i })).toContainText('Pago único');
    await expect(page.getByRole('button', { name: 'Cancelar asesoría', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cambiar enlace' })).toBeVisible();
    await expect(page.getByText('¿No puedes darla?')).toBeHidden();
    await sinViolaciones(page);
    expect(await sinDesborde(page)).toBe(true);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf15-gestion-admin-${t.nombre}.png`, fullPage: true });
  });
}

test('lugar o enlace: aviso de falta con la cita en menos de 48 h', async ({ page }) => {
  await comoCliente(page, 'profesional');
  await ver(page, paraProfesional(confirmada({ inicio: dentroDe(24 * 60), fin: dentroDe(25 * 60) })));
  await expect(page.getByText('Falta confirmar el enlace. El cliente lo espera antes de la cita.')).toBeVisible();
  await sinViolaciones(page);
  await ver(page, paraProfesional(confirmada({ inicio: dentroDe(24 * 60), fin: dentroDe(25 * 60), modalidad: 'presencial' })));
  await expect(page.getByText('Falta confirmar el lugar. El cliente lo espera antes de la cita.')).toBeVisible();
});

test('lugar o enlace: registrar el enlace de Meet, con teclado, y avisar', async ({ page }) => {
  const consola = vigilarConsola(page);
  await comoCliente(page, 'profesional');
  await ver(page, paraProfesional(proxima()));
  const cambios = await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, json(200, paraProfesional(proxima({ enlace: 'https://meet.google.com/abc-defg-hij' }))));
  await page.getByRole('button', { name: 'Registrar enlace' }).click();
  await expect(page.getByRole('heading', { name: /Lugar o enlace · A-2026-00001/ })).toBeFocused();
  await expect(page.getByRole('radio', { name: /Virtual/ })).toBeChecked();
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toHaveAttribute('inputmode', 'url');
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toHaveAttribute('spellcheck', 'false');
  await expect(panelLugar(page)).toContainText('Avisamos a Lu Beats y a Ana Beat por correo, con el evento de calendario actualizado. Escribe solo lo que ya acordaron.');
  await sinViolaciones(page);
  // Enlace que no es de Meet: error local, sin enviar.
  await page.getByRole('textbox', { name: 'Enlace' }).fill('https://zoom.us/j/123');
  await panelLugar(page).getByRole('button', { name: 'Guardar y avisar' }).click();
  await expect(page.getByText('Pega un enlace de Google Meet que empiece por https://meet.google.com/.').first()).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toHaveAttribute('aria-invalid', 'true');
  expect(cambios).toHaveLength(0);
  await page.getByRole('textbox', { name: 'Enlace' }).fill('https://meet.google.com/abc-defg-hij');
  await panelLugar(page).getByRole('button', { name: 'Guardar y avisar' }).click();
  await expect(aviso(page)).toContainText('Guardado. Avisamos a Lu Beats y a Ana Beat por correo con el evento actualizado.');
  await expect(aviso(page)).toBeFocused();
  expect(cambios[0].cuerpo).toEqual({ modalidad: 'virtual', enlace: 'https://meet.google.com/abc-defg-hij' });
  await expect(page.getByRole('button', { name: 'Cambiar enlace' })).toBeVisible();
  await expect(page.getByText('https://meet.google.com/abc-defg-hij').first()).toBeVisible();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
});

test('lugar o enlace: cambiar a presencial deja el foco en la casilla y valida el largo', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await ver(page, paraAdmin(proxima({ enlace: 'https://meet.google.com/abc-defg-hij' })), '&accion=lugar');
  await expect(page.getByRole('heading', { name: /Lugar o enlace · A-2026-00001/ })).toBeFocused();
  expect(new URL(page.url()).searchParams.has('accion')).toBe(false);
  await page.getByRole('radio', { name: 'Presencial' }).focus();
  await page.keyboard.press('Space');
  await expect(page.getByRole('radio', { name: 'Presencial' })).toBeFocused();
  await expect(page.getByRole('textbox', { name: 'Lugar', exact: true })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Lugar', exact: true })).toHaveAttribute('maxlength', '300');
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toBeHidden();
  const cambios = await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, json(200, paraAdmin(proxima({ modalidad: 'presencial', lugar: 'Ambiente 2 del estudio' }))));
  await page.getByRole('textbox', { name: 'Lugar', exact: true }).fill('Ambiente 2 del estudio');
  await panelLugar(page).getByRole('button', { name: 'Guardar y avisar' }).click();
  await expect(aviso(page)).toContainText('Guardado');
  expect(cambios[0].cuerpo).toEqual({ modalidad: 'presencial', lugar: 'Ambiente 2 del estudio' });
  await expect(page.getByRole('region', { name: /D1 Asesoría/i })).toContainText('Ambiente 2 del estudio');
  // Escape cierra el panel y devuelve el foco al botón.
  await page.getByRole('button', { name: 'Cambiar lugar' }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Cambiar lugar' })).toBeFocused();
});

test('lugar o enlace: dejarlo vacio lo manda en null (por confirmar)', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await ver(page, paraAdmin(proxima({ enlace: 'https://meet.google.com/abc-defg-hij' })));
  const cambios = await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, json(200, paraAdmin(proxima())));
  await page.getByRole('button', { name: 'Cambiar enlace' }).click();
  await page.getByRole('textbox', { name: 'Enlace' }).fill('');
  await panelLugar(page).getByRole('button', { name: 'Guardar y avisar' }).click();
  await expect(aviso(page)).toContainText('Guardado');
  expect(cambios[0].cuerpo).toEqual({ modalidad: 'virtual', enlace: null });
  await expect(page.getByText('Por confirmar').first()).toBeVisible();
});

test('lugar o enlace: errores 422, 409, 403, 404 y de red al guardar', async ({ page }) => {
  const consola = vigilarConsola(page);
  await comoCliente(page, 'profesional');
  await ver(page, paraProfesional(proxima()));
  const abrir = async () => {
    await page.getByRole('button', { name: /Registrar enlace|Cambiar enlace/ }).click();
    await page.getByRole('textbox', { name: 'Enlace' }).fill('https://meet.google.com/abc-defg-hij');
  };
  const guardar = () => panelLugar(page).getByRole('button', { name: 'Guardar y avisar' }).click();
  // 422 enlace_invalido (el servidor lo rechaza aunque el formato local pase).
  await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, json(422, { error: { codigo: 'enlace_invalido', mensaje: 'x' } }));
  await abrir();
  await guardar();
  await expect(page.getByText('Pega un enlace de Google Meet que empiece por https://meet.google.com/.').first()).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Enlace' })).toHaveValue('https://meet.google.com/abc-defg-hij');
  // 409 no_editable: el panel se cierra, el detalle se vuelve a leer y se explica.
  await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, errorApi(409, 'no_editable'));
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, paraProfesional(asesoria({ estado: 'cancelada', motivo_cancelacion: 'administrador' }))));
  await guardar();
  await expect(aviso(page)).toContainText('Esta asesoría ya no admite cambios de lugar o enlace: está cancelada o ya terminó.');
  await expect(panelLugar(page)).toHaveCount(0);
  // 503, red, 403 y 404 sobre una asesoría viva.
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, paraProfesional(proxima())));
  for (const [resp, texto] of [
    [errorApi(503, 'servicio_no_disponible'), 'El servicio no responde'],
    [{ abort: true }, 'Sin conexión'],
    [{ status: 200, contentType: 'text/html', body: 'no' }, 'Algo salió mal'],
  ]) {
    await page.goto(URL_DETALLE);
    await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, (r) => (resp.abort ? r.abort('connectionrefused') : r.fulfill(resp)));
    await abrir();
    await guardar();
    await expect(aviso(page)).toContainText(texto);
    await expect(page.getByRole('textbox', { name: 'Enlace' })).toHaveValue('https://meet.google.com/abc-defg-hij');
    await expect(aviso(page).getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  }
  await page.goto(URL_DETALLE);
  await simular(page, 'PATCH', `/asesorias/${AID}/encuentro`, errorApi(403, 'sin_permiso'));
  await abrir();
  await guardar();
  await expect(page.locator('[data-salida]')).toContainText('[403]');
  expect(consola).toEqual([]);
});

test('cancelacion del estudio por el Administrador tambien tras el inicio, solo con la opcion "El estudio"', async ({ page }) => {
  const consola = vigilarConsola(page);
  await comoCliente(page, 'administrador');
  const enCurso = paraAdmin(confirmada({ inicio: dentroDe(-30), fin: dentroDe(30), enlace: 'https://meet.google.com/abc-defg-hij' }));
  await ver(page, enCurso);
  await page.getByRole('button', { name: 'Cancelar asesoría', exact: true }).click();
  const panel = page.getByRole('region', { name: /Cancelar asesoría A-2026-00001/ });
  await expect(panel.getByRole('radio')).toHaveCount(1);
  await expect(panel.getByRole('radio', { name: /El cliente, por otro canal/ })).toHaveCount(0);
  await expect(panel).toContainText('El profesional no puede darla, falla técnica o fuerza mayor.');
  await panel.getByRole('radio', { name: /El estudio/ }).check();
  await expect(panel).toContainText('El cliente elegirá en la app entre reprogramar sin costo con Ana Beat o la devolución íntegra de S/ 140,00, que haces en un máximo de 7 días hábiles. Si prefiere a otro profesional, agenda una asesoría nueva. Avisamos al cliente y a Ana Beat por correo.');
  await sinViolaciones(page);
  const cancelaciones = await simular(page, 'POST', `/reservas/${AID}/cancelar`, json(200, paraAdmin(confirmada({ estado: 'cancelada', motivo_cancelacion: 'administrador', eleccion_estudio: 'pendiente', cancelacion: { nivel: null, aviso_en: dentroDe(0), por: 'estudio', pagado: '140.00', retenido: '0.00', credito: '0.00', nota: 'Se cayó la luz.' } }))));
  await panel.getByLabel(/Nota para el cliente/).fill('Se cayó la luz.');
  await panel.getByRole('button', { name: 'Cancelar asesoría A-2026-00001' }).click();
  expect(cancelaciones[0].cuerpo).toEqual({ por: 'estudio', nota: 'Se cayó la luz.' });
  await expect(aviso(page)).toContainText('Asesoría cancelada. Avisamos al cliente para que elija y a Ana Beat.');
  await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toContainText('Del estudio');
  await expect(page.getByRole('link', { name: /Reprogramar sin costo/ })).toHaveAttribute('href', `/app/asesorias/reprogramar?id=${AID}`);
  await expect(page.getByRole('button', { name: 'Pedir la devolución íntegra' })).toBeVisible();
  expect(consola).toEqual([]);
});

test('antes del inicio el Administrador ve las dos opciones y, ya cerrada o realizada, no cancela', async ({ page }) => {
  await comoCliente(page, 'administrador');
  await ver(page, paraAdmin(proxima()));
  await page.getByRole('button', { name: 'Cancelar asesoría', exact: true }).click();
  await expect(page.getByRole('region', { name: /Cancelar asesoría/ }).getByRole('radio')).toHaveCount(2);
  await expect(page.getByRole('radio', { name: /El cliente, por otro canal/ })).toBeVisible();
  await ver(page, paraAdmin(confirmada({ estado: 'realizada', inicio: dentroDe(-90), fin: dentroDe(-30) })));
  await expect(page.getByRole('button', { name: 'Cancelar asesoría', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Cambiar|Registrar/ })).toHaveCount(0);
});

test('"Tratar como nivel 1" en una asesoria: crédito sin devolución en dinero', async ({ page }) => {
  await comoCliente(page, 'administrador');
  const cancelada = paraAdmin(asesoria({
    estado: 'cancelada', motivo_cancelacion: 'cliente', cuotas: [{ id: 'c', hito: 'al_reservar', monto: '140.00', estado: 'pagada', pagable: false, pagado: '140.00', pagos: [] }], pagado: '140.00',
    cancelacion: { nivel: 2, aviso_en: dentroDe(-60), por: 'cliente', pagado: '140.00', retenido: '35.00', credito: '105.00' },
  }));
  await ver(page, cancelada);
  await page.getByRole('button', { name: 'Tratar como nivel 1' }).click();
  const panel = page.getByRole('region', { name: /Tratar como nivel 1 · A-2026-00001/ });
  await expect(panel).toContainText('Lo retenido (S/ 35,00) pasa a un crédito de caso excepcional que vence 30 días después de hoy. Nació de una asesoría: no admite devolución en dinero (sí la parte que venía de un crédito de sala). Solo una vez por asesoría.');
  await expect(panel.getByLabel(/Motivo/)).toContainText('');
  await expect(panel).toContainText('El cliente lo verá en su asesoría.');
  await expect(panel.getByRole('button', { name: 'Volver a la asesoría' })).toBeVisible();
  await sinViolaciones(page);
});

test('el profesional ve la cancelacion y las reprogramaciones sin montos ni nivel', async ({ page }) => {
  await comoCliente(page, 'profesional');
  const a = paraProfesional(asesoria({
    estado: 'cancelada', motivo_cancelacion: 'administrador',
    cancelacion: { aviso_en: '2026-11-14T10:00:00-05:00', por: 'estudio' },
    reprogramaciones: [{ en: '2026-11-12T10:00:00-05:00', anterior_inicio: '2026-12-10T15:00:00-05:00', nuevo_inicio: '2026-12-18T15:00:00-05:00' }],
  }));
  await ver(page, a);
  const d4 = page.getByRole('region', { name: /D4 Cancelación/i });
  await expect(d4).toContainText('Del estudio');
  await expect(d4.getByText('Retenido')).toBeHidden();
  await expect(d4.getByText('Pagado')).toBeHidden();
  await expect(d4.getByText('Nivel')).toBeHidden();
  const d5 = page.getByRole('region', { name: /D5 Reprogramaciones/i });
  await expect(d5.getByRole('columnheader')).toHaveText(['Fecha del cambio', 'Antes', 'Ahora']);
  await expect(d5).toContainText('10 dic 2026, 15:00');
  await sinViolaciones(page);
});

test('detalle: 404 de una ajena lleva a la agenda; 401, 503, red y no JSON muestran su estado', async ({ page }) => {
  const consola = vigilarConsola(page);
  await comoCliente(page, 'profesional');
  await simular(page, 'GET', `/asesorias/${AID}`, errorApi(404, 'no_encontrada'));
  await page.goto(URL_DETALLE);
  await expect(page.locator('[data-salida]')).toContainText('[404]');
  await expect(page.locator('[data-salida]')).toContainText('No encontramos esta asesoría.');
  await expect(page.getByRole('link', { name: 'Volver a asesorías' })).toHaveAttribute('href', '/app/asesorias/agenda');
  await sinViolaciones(page);
  for (const [r, texto] of [
    [(x) => x.fulfill(errorApi(401, 'no_autenticado')), 'Tu sesión no es válida'],
    [(x) => x.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde'],
    [(x) => x.abort('connectionrefused'), 'Sin conexión'],
    [(x) => x.fulfill({ status: 200, contentType: 'text/html', body: 'no' }), 'Algo salió mal'],
  ]) {
    await simular(page, 'GET', `/asesorias/${AID}`, r);
    await page.goto(URL_DETALLE);
    await expect(page.locator('[data-salida]')).toContainText(texto);
  }
  expect(consola).toEqual([]);
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('detalle de la asesoria: el contenido estatico avisa de que necesita JavaScript', async ({ page }) => {
    await page.goto(URL_DETALLE);
    expect(await page.content()).toContain('Esta sección necesita JavaScript');
    await expect(page.locator('bugalu-reservas noscript .aviso-titulo')).toBeVisible();
  });
});
