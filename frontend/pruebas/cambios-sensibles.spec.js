// RF-20 (CA-04 a CA-06, CA-09): revision con barreras de los cambios sensibles e impuestos. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, json, errorApi } from './ayudas-admin.js';

const SERVICIOS = [{ id: 's1', nombre: 'Grabación de voces', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '15.00', especialistas_por_defecto: ['e1'], activo: true }];
const ESPECIALISTAS = [{ id: 'e1', nombre: 'Ingeniero de sonido', monto_fijo: '0.00', monto_variable: '25.00', unidad: 'hora', activo: true }];
const RECARGOS = { noche: { porcentaje: '25.00', desde: '22:00', hasta: '06:00' }, fin_de_semana: { porcentaje: '10.00' }, feriado: { porcentaje: '50.00' } };
const previa = (token = 't1', extra = {}) => ({
  token, expira_en: '2026-11-15T15:10:00Z', palabra: 'CONFIRMAR', recurso: 'servicio', id_recurso: 's1', nombre_recurso: 'Grabación de voces',
  cambios: [{ campo: 'tarifa_hora', anterior: '120.00', nuevo: '150.00' }],
  impacto: { ejemplos: [{ concepto: '2 h en horario normal', tipo: 'importe', antes: '255.00', despues: '315.00' }, { concepto: 'Vence el pago de una reserva a 36 h', tipo: 'fecha_hora', antes: '2026-11-20T15:00:00-05:00', despues: '2026-11-20T16:30:00-05:00' }, { concepto: 'Ajuste', tipo: 'texto', antes: 'uno', despues: 'otro' }], operaciones_vigentes: 12 },
  ...extra,
});
const confirmada = { recurso: 'servicio', id_recurso: 's1', valor: SERVICIOS[0], cambios: [] };

async function base(page, { previsualizar = json(200, previa()), confirmar = json(200, confirmada) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  await comoAdministrador(page);
  await simular(page, 'GET', '/servicios', json(200, SERVICIOS));
  await simular(page, 'GET', '/especialistas', json(200, ESPECIALISTAS));
  await simular(page, 'GET', '/recargos', json(200, RECARGOS));
  await simular(page, 'GET', '/feriados', json(200, []));
  await simular(page, 'GET', '/impuestos', json(200, { porcentaje_igv: '18.00', precios_incluyen_igv: true }));
  return {
    previas: await simular(page, 'POST', '/cambios-sensibles/previsualizar', previsualizar),
    confirmaciones: await simular(page, 'POST', '/cambios-sensibles/confirmar', confirmar),
    patches: await simular(page, 'PATCH', '/servicios/s1', json(200, SERVICIOS[0])),
  };
}
// Titulo y texto de un aviso son nodos distintos: se lee la frase entera.
const dice = (page, texto) => expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
const guardar = (page) => page.getByRole('button', { name: 'Guardar servicio' });
const aplicar = (page) => page.getByRole('button', { name: 'Aplicar cambio' });
const palabra = (page) => page.getByLabel('Escribe CONFIRMAR');
async function aRevision(page) {
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('150');
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
}

for (const t of tamanos) {
  test(`servicio: un cambio sensible abre la revision y se confirma con CONFIRMAR a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const v = await base(page);
    await aRevision(page);
    expect(v.previas[0].cuerpo).toEqual({ recurso: 'servicio', id_recurso: 's1', cambios: { tarifa_hora: '150.00' } });
    const c1 = page.getByRole('table', { name: 'Qué cambia' });
    await expect(c1).toContainText('TARIFA POR HORA');
    await expect(c1).toContainText('S/ 120,00');
    await expect(c1).toContainText('S/ 150,00');
    const c2 = page.getByRole('table', { name: 'Impacto' });
    await expect(c2).toContainText('S/ 255,00');
    await expect(c2).toContainText('20 nov, 15:00');
    await expect(c2).toContainText('otro');
    await dice(page, '12 reservas vigentes conservan sus condiciones');
    await expect(page.getByRole('heading', { name: /Guardar|Tarifa$/ })).toHaveCount(0);
    await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'true');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/cambio-sensible-revision-${t.nombre}.png`, fullPage: true });
    // Boton bloqueado: pulsarlo explica el motivo; minusculas no valen.
    await aplicar(page).click({ force: true }); // aria-disabled: Playwright lo trata como deshabilitado, el usuario si puede pulsarlo
    await expect(page.getByText('Escribe CONFIRMAR, en mayúsculas, para aplicar el cambio.')).toBeVisible();
    await palabra(page).fill('confirmar');
    await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'true');
    await sinViolaciones(page);
    await palabra(page).fill('  CONFIRMAR ');
    await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'false');
    await aplicar(page).click();
    await expect(page).toHaveURL(/\/app\/tarifas\?aviso=servicio-actualizado|\/app\/tarifas$/);
    expect(v.confirmaciones[0].cuerpo).toEqual({ token: 't1', palabra: 'CONFIRMAR' });
    expect(v.patches).toHaveLength(0);
    expect(consola).toEqual([]);
  });
}

test('servicio: tras confirmar envia por el endpoint de siempre lo no sensible', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('150');
  await page.getByLabel('Activo').uncheck();
  await guardar(page).click();
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await expect(page).toHaveURL(/\/app\/tarifas(\?.*)?$/);
  expect(v.patches[0].cuerpo).toEqual({ activo: false, especialistas_por_defecto: ['e1'] });
});

test('servicio: confirmado pero falla lo no sensible, avisa y recarga el formulario', async ({ page }) => {
  await base(page);
  await simular(page, 'PATCH', '/servicios/s1', json(503, { error: { codigo: 'servicio_no_disponible', mensaje: 'x' } }));
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('150');
  await page.getByLabel('Activo').uncheck();
  await guardar(page).click();
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'La tarifa se cambió, pero no pudimos guardar Activo.');
  await expect(guardar(page)).toBeVisible();
});

test('servicio: sin cambios sensibles guarda en un paso, sin revision', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Activo').uncheck();
  await guardar(page).click();
  await expect(page).toHaveURL(/\/app\/tarifas(\?.*)?$/);
  expect(v.previas).toHaveLength(0);
  expect(v.patches).toHaveLength(1);
});

test('cancelar: vuelve al formulario con lo escrito, sin aplicar, y el foco al boton de guardar', async ({ page }) => {
  const v = await base(page);
  await aRevision(page);
  await page.getByRole('button', { name: 'Cancelar' }).click();
  await dice(page, 'No se aplicó ningún cambio.');
  await expect(page.getByLabel('Tarifa por hora (S/)')).toHaveValue('150');
  await expect(guardar(page)).toBeFocused();
  expect(v.confirmaciones).toHaveLength(0);
  await sinViolaciones(page);
});

test('teclado: Enter en el campo aplica y el foco entra y sale de la revision', async ({ page }) => {
  const v = await base(page);
  await aRevision(page);
  await page.keyboard.press('Tab');
  await expect(palabra(page)).toBeFocused();
  await page.keyboard.type('CONFIRMAR');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/app\/tarifas(\?.*)?$/);
  expect(v.confirmaciones).toHaveLength(1);
});

test('palabra_incorrecta del servidor: error bajo el campo y el token sigue vigente', async ({ page }) => {
  await base(page, { confirmar: json(422, { error: { codigo: 'palabra_incorrecta', mensaje: 'x' } }) });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await expect(page.getByText('Escribe CONFIRMAR, en mayúsculas, para aplicar el cambio.')).toBeVisible();
  await expect(palabra(page)).toHaveValue('CONFIRMAR');
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeVisible();
});

test('confirmacion_no_valida: renueva la vista previa y conserva la palabra', async ({ page }) => {
  let n = 0;
  const v = await base(page, {
    previsualizar: (r) => r.fulfill(json(200, previa(`t${++n}`))),
    confirmar: (r) => (JSON.parse(r.request().postData()).token === 't1' ? r.fulfill(errorApi(409, 'confirmacion_no_valida')) : r.fulfill(json(200, confirmada))),
  });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'La vista previa caducó y la actualizamos. Revisa el impacto y vuelve a aplicar.');
  await expect(palabra(page)).toHaveValue('CONFIRMAR');
  expect(v.previas).toHaveLength(2);
  await sinViolaciones(page);
  await aplicar(page).click();
  await expect(page).toHaveURL(/\/app\/tarifas(\?.*)?$/);
  expect(v.confirmaciones.at(-1).cuerpo.token).toBe('t2');
});

test('cambio_desactualizado: nueva vista previa, aviso y campo vacio', async ({ page }) => {
  let n = 0;
  const v = await base(page, {
    previsualizar: (r) => r.fulfill(json(200, previa(`t${++n}`, n > 1 ? { cambios: [{ campo: 'tarifa_hora', anterior: '130.00', nuevo: '150.00' }] } : {}))),
    confirmar: (r) => r.fulfill(errorApi(409, 'cambio_desactualizado')),
  });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Otro administrador cambió Grabación de voces mientras revisabas.');
  await expect(palabra(page)).toHaveValue('');
  await expect(page.getByRole('table', { name: 'Qué cambia' })).toContainText('S/ 130,00');
  // La renovada lleva solo lo que el usuario tocó: no revierte el monto fijo de otro administrador.
  expect(v.previas).toHaveLength(2);
  for (const p of v.previas) expect(p.cuerpo.cambios).toEqual({ tarifa_hora: '150.00' });
  await sinViolaciones(page);
});

test('cambio_desactualizado con sin_cambios: recarga el formulario y avisa', async ({ page }) => {
  let n = 0;
  await base(page, {
    previsualizar: (r) => (++n === 1 ? r.fulfill(json(200, previa())) : r.fulfill(errorApi(422, 'sin_cambios'))),
    confirmar: (r) => r.fulfill(errorApi(409, 'cambio_desactualizado')),
  });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Otro administrador ya aplicó estos mismos valores.');
  await expect(guardar(page)).toBeVisible();
});

test('403 al confirmar: vuelve al formulario con el aviso de otra cuenta', async ({ page }) => {
  await base(page, { confirmar: json(403, { error: { codigo: 'sin_permiso', mensaje: 'x' } }) });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Esta vista previa la pidió otra cuenta. Vuelve a guardar para generar la tuya.');
  await expect(guardar(page)).toBeVisible();
});

for (const [n, resp, texto] of [
  ['503', json(503, { error: { codigo: 'servicio_no_disponible', mensaje: 'x' } }), 'El servicio no responde. Inténtalo de nuevo en unos minutos.'],
  ['no-json', { status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }, 'Algo salió mal. Inténtalo de nuevo.'],
]) {
  test(`confirmar ${n}: nada aplicado, la revision y lo escrito se conservan`, async ({ page }) => {
    await base(page, { confirmar: resp });
    await aRevision(page);
    await palabra(page).fill('CONFIRMAR');
    await aplicar(page).click();
    await expect(page.getByText(texto)).toBeVisible();
    await expect(palabra(page)).toHaveValue('CONFIRMAR');
    await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'false');
  });
}

test('confirmar con red caida: conserva lo escrito', async ({ page }) => {
  await base(page, { confirmar: (r) => r.abort('connectionrefused') });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Sin conexión. Revisa tu red y vuelve a intentarlo.');
  await expect(palabra(page)).toHaveValue('CONFIRMAR');
});

test('previsualizar: sin_cambios y 422 de campo vuelven al formulario con su error', async ({ page }) => {
  await base(page, { previsualizar: errorApi(422, 'sin_cambios') });
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('150');
  await guardar(page).click();
  await dice(page, 'Ya tiene esos valores. No hay nada que cambiar.');
  await expect(guardar(page)).toBeEnabled();
  await sinViolaciones(page);
});

test('previsualizar: 422 datos_invalidos pone el error bajo el campo', async ({ page }) => {
  await base(page, { previsualizar: json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'tarifa_hora' } } }) });
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('150');
  await guardar(page).click();
  await expect(page.getByText('Escribe un importe de 0 o más, con hasta dos decimales, como 120,50.').first()).toBeVisible();
});

test('red de seguridad: un 428 del endpoint de siempre abre la revision', async ({ page }) => {
  const v = await base(page);
  await simular(page, 'PATCH', '/servicios/s1', json(428, { error: { codigo: 'confirmacion_requerida', mensaje: 'x', detalles: { campos: ['tarifa_hora'] } } }));
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Activo').uncheck();
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(v.previas).toHaveLength(1);
});

test('especialista: la vista previa lleva solo el campo sensible tocado', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/tarifas/especialista?id=e1');
  await page.getByLabel('Por media hora').check();
  await page.getByRole('button', { name: 'Guardar especialista' }).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(v.previas[0].cuerpo.cambios).toEqual({ unidad: 'lapso_30' });
});

test('especialista: la unidad se muestra como Por hora / Por media hora', async ({ page }) => {
  await base(page, { previsualizar: json(200, previa('t1', { recurso: 'especialista', cambios: [{ campo: 'unidad', anterior: 'hora', nuevo: 'lapso_30' }] })) });
  await page.goto('/app/tarifas/especialista?id=e1');
  await page.getByLabel('Por media hora').check();
  await page.getByRole('button', { name: 'Guardar especialista' }).click();
  const c1 = page.getByRole('table', { name: 'Qué cambia' });
  await expect(c1).toContainText('UNIDAD');
  await expect(c1).toContainText('Por hora');
  await expect(c1).toContainText('Por media hora');
});

test('recargos: cambio de porcentaje revisa, confirma y ofrece el registro de cambios', async ({ page }) => {
  const v = await base(page, { previsualizar: json(200, previa('t1', { recurso: 'recargos', id_recurso: null, nombre_recurso: 'Recargos', cambios: [{ campo: 'noche.porcentaje', anterior: '25.00', nuevo: '30.00' }] })) });
  await page.goto('/app/tarifas/recargos?anio=2026');
  await page.getByRole('group', { name: 'Noche' }).getByLabel('Recargo (%)').fill('30');
  await page.getByRole('button', { name: 'Guardar recargos' }).click();
  expect(v.previas[0].cuerpo.cambios).toEqual({ noche: { porcentaje: '30.00' } });
  await expect(page.getByRole('table', { name: 'Qué cambia' })).toContainText('NOCHE (%)');
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Recargos guardados.');
  await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=recargos');
});

// --- Impuestos ---
for (const t of tamanos) {
  test(`impuestos: muestra el IGV vigente y cambia por la revision a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const v = await base(page, { previsualizar: json(200, previa('t1', { recurso: 'impuestos', id_recurso: null, nombre_recurso: 'Impuestos', cambios: [{ campo: 'porcentaje_igv', anterior: '18.00', nuevo: '19.00' }, { campo: 'precios_incluyen_igv', anterior: 'true', nuevo: 'false' }] })) });
    await page.goto('/app/tarifas/impuestos');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Impuestos');
    await expect(page.getByLabel('Porcentaje de IGV (%)')).toHaveValue('18');
    await expect(page.getByRole('radio', { name: /^Sí/ })).toBeChecked();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/impuestos-${t.nombre}.png`, fullPage: true });
    await page.getByLabel('Porcentaje de IGV (%)').fill('19');
    await page.getByRole('radio', { name: /^No/ }).check();
    await page.getByRole('button', { name: 'Revisar cambio' }).click();
    expect(v.previas[0].cuerpo).toEqual({ recurso: 'impuestos', cambios: { porcentaje_igv: '19.00', precios_incluyen_igv: false } });
    const c1 = page.getByRole('table', { name: 'Qué cambia' });
    await expect(c1).toContainText('PORCENTAJE DE IGV');
    await expect(c1).toContainText('18 %');
    await expect(c1).toContainText('19 %');
    await expect(c1).toContainText('LOS PRECIOS INCLUYEN IGV');
    await sinViolaciones(page);
    await palabra(page).fill('CONFIRMAR');
    await aplicar(page).click();
    await dice(page, 'IGV actualizado. Rige para las simulaciones y reservas nuevas.');
    await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=impuestos');
    expect(consola).toEqual([]);
  });
}

test('impuestos: porcentaje fuera de rango no pide vista previa', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/tarifas/impuestos');
  await page.getByLabel('Porcentaje de IGV (%)').fill('100');
  await page.getByRole('button', { name: 'Revisar cambio' }).click();
  await expect(page.getByText('Escribe un porcentaje de 0 a 99,99, con hasta dos decimales.').first()).toBeVisible();
  expect(v.previas).toHaveLength(0);
});

test('impuestos: 503 al cargar ofrece Reintentar', async ({ page }) => {
  await base(page);
  await simular(page, 'GET', '/impuestos', json(503, { error: { codigo: 'servicio_no_disponible', mensaje: 'x' } }));
  await page.goto('/app/tarifas/impuestos');
  await dice(page, 'El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
});
