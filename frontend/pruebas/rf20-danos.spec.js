// RF-20 (CA-11 a CA-13): grupo "Daños" de /app/franjas/parametros con el flujo de cambio sensible, y pie VALORES VIGENTES de las condiciones. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos, API } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const PARAMETROS = {
  dias_limite_pago: 3, horas_limite_pago: 24, anticipacion_minima_horas: 2, anticipacion_maxima_semanas: 8,
  porcentaje_adelanto: 50, horas_nivel_1: 48, horas_nivel_2: 24, porcentaje_penalizacion_nivel_2: 25, minutos_tolerancia_inasistencia: 15,
  dias_vigencia_credito: 30, reprogramaciones_nivel_1: 2, reprogramaciones_nivel_2: 1, tarifa_hora_gestion: '25.00', tope_horas_sesiones_perdidas: 8,
};
const AVISO_DANOS = 'Se aplica a los daños que se registren desde ahora.';
const previa = (cambios, extra = {}) => ({
  token: 't1', expira_en: '2026-11-16T15:10:00Z', palabra: 'CONFIRMAR', recurso: 'parametros', id_recurso: null, nombre_recurso: 'Parámetros de reserva',
  cambios, impacto: { ejemplos: [], operaciones_vigentes: 0 }, ...extra,
});
const CAMBIO_TARIFA = [{ campo: 'tarifa_hora_gestion', anterior: '25.00', nuevo: '30.00' }];

async function base(page, { parametros = PARAMETROS, previsualizar = json(200, previa(CAMBIO_TARIFA)), confirmar = json(200, { recurso: 'parametros', id_recurso: null, valor: PARAMETROS, cambios: [] }) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-16T15:00:00Z'));
  await comoAdministrador(page);
  let actuales = parametros;
  await simular(page, 'GET', '/parametros', (r) => r.fulfill(json(200, actuales)));
  const patches = await simular(page, 'PATCH', '/parametros', (r) => {
    actuales = { ...actuales, ...r.request().postDataJSON() };
    return r.fulfill(json(200, actuales));
  });
  return {
    patches,
    previas: await simular(page, 'POST', '/cambios-sensibles/previsualizar', previsualizar),
    confirmaciones: await simular(page, 'POST', '/cambios-sensibles/confirmar', (r) => {
      actuales = { ...actuales, tarifa_hora_gestion: '30.00' };
      return typeof confirmar === 'function' ? confirmar(r) : r.fulfill(confirmar);
    }),
  };
}
const guardar = (page) => page.getByRole('button', { name: 'Guardar parámetros' });
const tarifa = (page) => page.getByLabel(/^Tarifa por hora de gestión/);
const tope = (page) => page.getByLabel(/^Tope por sesiones perdidas/);
const dice = (page, texto) => expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();

for (const t of tamanos) {
  test(`danos: P4 con los dos valores, ayudas y sin etiqueta POR FIJAR a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await base(page);
    await page.goto('/app/franjas/parametros');
    await expect(page.getByRole('heading', { level: 2, name: /P4 Daños/i })).toBeVisible();
    await expect(page.getByText('Se publican al pie de las condiciones de contratación.')).toBeVisible();
    await expect(tarifa(page)).toHaveValue('25.00'); // el valor tal como llega
    await expect(tarifa(page)).toHaveAttribute('step', '0.01');
    await expect(tarifa(page)).toHaveAttribute('max', '9999.99');
    await expect(tarifa(page)).toHaveAttribute('inputmode', 'decimal');
    await expect(tope(page)).toHaveValue('8');
    await expect(tope(page)).toHaveAttribute('min', '1');
    await expect(tope(page)).toHaveAttribute('max', '200');
    await expect(page.getByText('Lo que cobramos por cada hora que el personal dedica a conseguir una reparación. Con 0,00 las condiciones dicen «por fijar».')).toBeVisible();
    await expect(page.getByText('Máximo de horas de reservas canceladas que se cobran por un daño intencional o un incumplimiento grave.')).toBeVisible();
    await expect(page.getByText('POR FIJAR', { exact: true })).toBeHidden();
    await expect(page.getByText('Si cambias un plazo, un porcentaje, un límite o un valor de daños, te mostraremos el impacto y te pediremos confirmarlo.')).toBeVisible();
    // Orden: P3 antes que P4, y P4 antes de guardar.
    const orden = await page.locator('h2.panel-titulo').allTextContents();
    expect(orden.findIndex((x) => /P3/.test(x))).toBeLessThan(orden.findIndex((x) => /P4/.test(x)));
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf20-danos-p4-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('danos: tarifa en 0.00 muestra POR FIJAR junto al titulo, como texto', async ({ page }) => {
  await base(page, { parametros: { ...PARAMETROS, tarifa_hora_gestion: '0.00' } });
  await page.goto('/app/franjas/parametros');
  await expect(tarifa(page)).toHaveValue('0.00');
  const etiqueta = page.getByText('POR FIJAR', { exact: true });
  await expect(etiqueta).toBeVisible();
  await expect(page.locator('h2.panel-titulo').filter({ hasText: 'POR FIJAR' })).toHaveCount(0); // fuera del <h2>
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf20-danos-por-fijar-1440.png', fullPage: true });
});

test('danos: reescribir el mismo valor (25 por 25.00) no abre la revision', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('25');
  await tope(page).fill('08');
  await page.getByLabel('Anticipación mínima (horas)').fill('5');
  await guardar(page).click();
  await dice(page, 'Parámetros guardados');
  expect(v.previas).toHaveLength(0);
  expect(v.patches[0].cuerpo).toEqual({ anticipacion_minima_horas: 5 });
});

test('danos: la tarifa viaja como texto con dos decimales', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('25,5'.replace(',', '.'));
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(v.previas[0].cuerpo).toEqual({ recurso: 'parametros', cambios: { tarifa_hora_gestion: '25.50' } });
});

test('danos: tarifa y tope cambiados abren la revision con sus etiquetas y formatos y se confirman', async ({ page }) => {
  const consola = vigilarConsola(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  const cambios = [{ campo: 'tarifa_hora_gestion', anterior: '25.00', nuevo: '30.50' }, { campo: 'tope_horas_sesiones_perdidas', anterior: '8', nuevo: '1' }];
  const v = await base(page, { previsualizar: json(200, previa(cambios)) });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30.5');
  await tope(page).fill('1');
  await guardar(page).click();
  await expect(guardar(page)).toBeHidden();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(v.previas[0].cuerpo).toEqual({ recurso: 'parametros', cambios: { tarifa_hora_gestion: '30.50', tope_horas_sesiones_perdidas: 1 } });
  const c1 = page.getByRole('table', { name: 'Qué cambia' });
  await expect(c1).toContainText('TARIFA POR HORA DE GESTIÓN');
  await expect(c1).toContainText('S/ 25,00');
  await expect(c1).toContainText('S/ 30,50');
  await expect(c1).toContainText('TOPE POR SESIONES PERDIDAS');
  await expect(c1).toContainText('8 h de sala');
  await expect(c1).toContainText('1 h de sala');
  // Sin reservas que conserven condiciones y sin ejemplos: solo el aviso, sin tabla de impacto.
  await dice(page, AVISO_DANOS);
  await expect(page.getByText('reservas vigentes conservan')).toHaveCount(0);
  await expect(page.getByRole('table', { name: 'Impacto' })).toBeHidden();
  await expect(page.locator('[role="status"]').filter({ hasText: 'Revisión lista: 2 cambios. Se aplica a los daños que se registren desde ahora.' })).toHaveCount(1);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf20-danos-revision-1440.png', fullPage: true });
  await page.getByLabel('Escribe CONFIRMAR').fill('CONFIRMAR');
  await page.getByRole('button', { name: 'Aplicar cambio' }).click();
  await dice(page, 'Parámetros guardados. La anticipación ya vale en el calendario; los plazos de pago, en las reservas nuevas. Los valores de daños ya se ven al pie de las condiciones.');
  await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=parametros');
  await expect(tarifa(page)).toHaveValue('30.00');
  expect(v.confirmaciones[0].cuerpo).toEqual({ token: 't1', palabra: 'CONFIRMAR' });
  expect(v.patches).toHaveLength(0);
  await sinViolaciones(page);
  expect(consola).toEqual([]);
});

test('danos: con ejemplos de impacto del servidor la tabla se pinta con el concepto tal cual', async ({ page }) => {
  const impacto = { ejemplos: [{ concepto: 'Tarifa por hora de gestión', tipo: 'importe', antes: '25.00', despues: '30.00' }], operaciones_vigentes: 0 };
  await base(page, { previsualizar: json(200, previa(CAMBIO_TARIFA, { impacto })) });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await expect(page.getByRole('table', { name: 'Impacto' })).toContainText('Tarifa por hora de gestión');
  await dice(page, AVISO_DANOS);
});

test('danos: mezclados con otro campo, el aviso de reservas y el de danos van juntos', async ({ page }) => {
  const cambios = [{ campo: 'porcentaje_adelanto', anterior: '50', nuevo: '40' }, ...CAMBIO_TARIFA];
  await base(page, { previsualizar: json(200, previa(cambios, { impacto: { ejemplos: [], operaciones_vigentes: 3 } })) });
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Adelanto para confirmar (%)').fill('40');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await dice(page, `3 reservas vigentes conservan sus condiciones. ${AVISO_DANOS}`);
});

test('danos: el registro y la revision de una tarifa por fijar dicen "(por fijar)"', async ({ page }) => {
  await base(page, { parametros: { ...PARAMETROS, tarifa_hora_gestion: '0.00' }, previsualizar: json(200, previa([{ campo: 'tarifa_hora_gestion', anterior: '0.00', nuevo: '25.00' }])) });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('25');
  await guardar(page).click();
  await expect(page.getByRole('table', { name: 'Qué cambia' })).toContainText('S/ 0,00 (por fijar)');
});

test('danos: cancelar vuelve al formulario con lo escrito y el foco al boton', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await page.getByRole('button', { name: 'Cancelar' }).click();
  await dice(page, 'No se aplicó ningún cambio.');
  await expect(tarifa(page)).toHaveValue('30');
  await expect(guardar(page)).toBeFocused();
  expect(v.confirmaciones).toHaveLength(0);
});

// --- Rangos y vacios ---
const CASOS = [
  ['tarifa vacía', () => tarifa, '', 'Escribe la tarifa por hora de gestión.'],
  ['tarifa negativa', () => tarifa, '-1', 'Escribe un importe de 0 a 9 999,99, con hasta dos decimales.'],
  ['tarifa sobre el máximo', () => tarifa, '10000', 'Escribe un importe de 0 a 9 999,99, con hasta dos decimales.'],
  ['tarifa con tres decimales', () => tarifa, '1.234', 'Escribe un importe de 0 a 9 999,99, con hasta dos decimales.'],
  ['tope vacío', () => tope, '', 'Escribe el tope de horas de sala.'],
  ['tope en 0', () => tope, '0', 'Escribe un número entero de 1 a 200.'],
  ['tope en 201', () => tope, '201', 'Escribe un número entero de 1 a 200.'],
  ['tope decimal', () => tope, '1.5', 'Escribe un número entero de 1 a 200.'],
];
for (const [nombre, campo, valor, mensaje] of CASOS) {
  test(`danos: ${nombre} da error bajo el campo y resumen, sin llamar a la API`, async ({ page }) => {
    const v = await base(page);
    await page.goto('/app/franjas/parametros');
    await campo()(page).fill(valor);
    await guardar(page).click();
    await expect(campo()(page)).toHaveAttribute('aria-invalid', 'true');
    await expect(page.locator('p.mensaje-error').filter({ hasText: mensaje })).toBeVisible();
    await expect(page.locator('.aviso-error')).toContainText('Revisa 1 campo');
    await expect(page.locator('.aviso-error')).toBeFocused();
    expect(await campo()(page).getAttribute('aria-describedby')).toMatch(/-error$/);
    expect(v.previas).toHaveLength(0);
    expect(v.patches).toHaveLength(0);
  });
}

test('danos: el error de un campo aparece al salir de el y se corrige al escribir bien', async ({ page }) => {
  await base(page);
  await page.goto('/app/franjas/parametros');
  await tope(page).fill('500');
  await tarifa(page).focus();
  await expect(page.locator('p.mensaje-error').filter({ hasText: 'Escribe un número entero de 1 a 200.' })).toBeVisible();
  await tope(page).fill('12');
  await tope(page).blur();
  await expect(page.locator('p.mensaje-error')).toHaveCount(0);
  await page.setViewportSize({ width: 1440, height: 900 });
  await tarifa(page).fill('99999');
  await guardar(page).click();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf20-danos-errores-1440.png', fullPage: true });
});

// --- Errores de la API ---
test('danos: 422 datos_invalidos de la vista previa marca el campo indicado', async ({ page }) => {
  await base(page, { previsualizar: json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'tope_horas_sesiones_perdidas' } } }) });
  await page.goto('/app/franjas/parametros');
  await tope(page).fill('20'); // valido aqui; el servidor lo contradice
  await guardar(page).click();
  await expect(tope(page)).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('p.mensaje-error').filter({ hasText: 'Escribe un número entero de 1 a 200.' })).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
});

test('danos: 422 datos_invalidos sobre la tarifa usa el texto del importe', async ({ page }) => {
  await base(page, { previsualizar: json(422, { error: { codigo: 'datos_invalidos', mensaje: 'x', detalles: { campo: 'tarifa_hora_gestion' } } }) });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await expect(page.locator('p.mensaje-error').filter({ hasText: 'Escribe un importe de 0 a 9 999,99, con hasta dos decimales.' })).toBeVisible();
});

for (const f of [
  { n: '503', r: errorApi(503, 'servicio_no_disponible'), t: 'El servicio no responde. Inténtalo de nuevo en unos minutos.' },
  { n: 'no-json', r: { status: 200, contentType: 'text/html', body: '<h1>x</h1>' }, t: 'Algo salió mal. Inténtalo de nuevo.' },
]) {
  test(`danos: ${f.n} al pedir la vista previa conserva lo escrito`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await base(page, { previsualizar: f.r });
    await page.goto('/app/franjas/parametros');
    await tarifa(page).fill('30');
    await guardar(page).click();
    await expect(page.locator('.aviso-error')).toContainText(f.t);
    await expect(tarifa(page)).toHaveValue('30');
    await expect(guardar(page)).toBeEnabled();
    expect(consola).toEqual([]);
  });
}

test('danos: red caida al pedir la vista previa conserva lo escrito', async ({ page }) => {
  await base(page, { previsualizar: (r) => r.abort('connectionrefused') });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await expect(page.locator('.aviso-error')).toContainText('Sin conexión. Revisa tu red y vuelve a intentarlo.');
  await expect(tarifa(page)).toHaveValue('30');
});

for (const f of fallos.filter((x) => ['401', '403'].includes(x.n))) {
  test(`danos: ${f.n} al pedir la vista previa sustituye la vista`, async ({ page }) => {
    await base(page, { previsualizar: f.r });
    await page.goto('/app/franjas/parametros');
    await tarifa(page).fill('30');
    await guardar(page).click();
    await expect(page.getByRole('main')).toContainText(f.texto);
  });
}

test('danos: 409 confirmacion_no_valida renueva la vista previa y conserva lo escrito', async ({ page }) => {
  let n = 0;
  const v = await base(page, {
    previsualizar: (r) => r.fulfill(json(200, previa(CAMBIO_TARIFA, { token: `t${++n}` }))),
    confirmar: (r) => (r.request().postDataJSON().token === 't1' ? r.fulfill(errorApi(409, 'confirmacion_no_valida')) : r.fulfill(json(200, { recurso: 'parametros', id_recurso: null, valor: PARAMETROS, cambios: [] }))),
  });
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await page.getByLabel('Escribe CONFIRMAR').fill('CONFIRMAR');
  await page.getByRole('button', { name: 'Aplicar cambio' }).click();
  await dice(page, 'La vista previa caducó y la actualizamos.');
  await expect(page.getByLabel('Escribe CONFIRMAR')).toHaveValue('CONFIRMAR');
  await page.getByRole('button', { name: 'Aplicar cambio' }).click();
  await dice(page, 'Parámetros guardados');
  expect(v.confirmaciones.map((c) => c.cuerpo.token)).toEqual(['t1', 't2']);
});

test('danos: palabra distinta no aplica', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await tarifa(page).fill('30');
  await guardar(page).click();
  await page.getByLabel('Escribe CONFIRMAR').fill('confirmar');
  await page.keyboard.press('Enter'); // "Aplicar cambio" sigue aria-disabled: Playwright no lo pulsa, el usuario si
  await expect(page.getByText('Escribe CONFIRMAR, en mayúsculas, para aplicar el cambio.')).toBeVisible();
  expect(v.confirmaciones).toHaveLength(0);
});

// --- 320 px ---
test('320 px: P4 y su revision no desbordan', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await base(page, { parametros: { ...PARAMETROS, tarifa_hora_gestion: '0.00' } });
  await page.goto('/app/franjas/parametros');
  await expect(page.getByText('POR FIJAR', { exact: true })).toBeVisible();
  const desborda = () => page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(await desborda()).toBe(false);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf20-danos-p4-320.png', fullPage: true });
  await tarifa(page).fill('30');
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(await desborda()).toBe(false);
  await page.screenshot({ path: 'pruebas/capturas/rf20-danos-revision-320.png', fullPage: true });
});

// --- Pie VALORES VIGENTES de las condiciones (CA-12) ---
const CONDICIONES = { tipo: 'condiciones_contratacion', version: '2.0.0', tipo_cambio: 'mayor', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes: { reserva: 'Pagas el adelanto para confirmar.' }, programada: false };
const PIE = 'Tarifa por hora de gestión: S/ 25,00 · Tope por sesiones perdidas: 8 horas de sala';

async function publica(page, { danos = json(200, { tarifa_hora_gestion: '25.00', tope_horas_sesiones_perdidas: 8 }), slug = 'condiciones_contratacion' } = {}) {
  await page.route(`${API}/**`, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
  await simular(page, 'GET', '/textos-legales', json(200, [{ ...CONDICIONES, tipo: slug }]));
  await page.route((u) => /^\/api\/v1\/textos-legales\/[^/]+\/versiones\/[^/]+$/.test(u.pathname), (r) => r.fulfill(json(200, { ...CONDICIONES, tipo: slug, contenido: '# x', contenido_html: '<h2>Daños</h2><p>Texto de las condiciones.</p>', publicado_en: '2026-10-20T10:00:00-05:00', resumen_cambios: null })));
  return simular(page, 'GET', '/parametros/danos', danos);
}
const valores = (page) => page.getByRole('heading', { level: 2, name: /valores vigentes/i });

for (const t of tamanos) {
  test(`pie: VALORES VIGENTES tras la prosa con tarifa y tope a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const llamadas = await publica(page);
    await page.goto('/legal/condiciones-de-contratacion/');
    await expect(page.getByText('Texto de las condiciones.')).toBeVisible();
    await expect(valores(page)).toBeVisible();
    await expect(page.getByText(PIE, { exact: true })).toBeVisible();
    // Va tras la prosa.
    const despues = await page.evaluate(() => {
      const prosa = document.querySelector('.prosa');
      const panel = [...document.querySelectorAll('.panel')].find((p) => /valores vigentes/i.test(p.textContent));
      return Boolean(prosa.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(despues).toBe(true);
    expect(llamadas).toHaveLength(1);
    expect(llamadas[0].url.search).toBe('');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf20-pie-condiciones-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

test('pie: vale para cualquier ?version= (son los vigentes)', async ({ page }) => {
  await publica(page);
  await page.goto('/legal/condiciones-de-contratacion/?version=2.0.0');
  await expect(page.getByText(PIE, { exact: true })).toBeVisible();
});

test('pie: tarifa 0.00 dice "por fijar"', async ({ page }) => {
  await publica(page, { danos: json(200, { tarifa_hora_gestion: '0.00', tope_horas_sesiones_perdidas: 8 }) });
  await page.goto('/legal/condiciones-de-contratacion/');
  await expect(page.getByText('Tarifa por hora de gestión: por fijar · Tope por sesiones perdidas: 8 horas de sala', { exact: true })).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf20-pie-por-fijar-1440.png', fullPage: true });
});

test('pie: tope de 1 dice "1 hora de sala"', async ({ page }) => {
  await publica(page, { danos: json(200, { tarifa_hora_gestion: '25.00', tope_horas_sesiones_perdidas: 1 }) });
  await page.goto('/legal/condiciones-de-contratacion/');
  await expect(page.getByText('Tarifa por hora de gestión: S/ 25,00 · Tope por sesiones perdidas: 1 hora de sala', { exact: true })).toBeVisible();
});

test('pie: los demas textos no lo piden ni lo pintan', async ({ page }) => {
  const llamadas = await publica(page, { slug: 'terminos_uso' });
  await page.goto('/legal/terminos-de-uso/');
  await expect(page.getByText('Texto de las condiciones.')).toBeVisible();
  await expect(valores(page)).toHaveCount(0);
  expect(llamadas).toHaveLength(0);
});

for (const f of [
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')) },
  { n: 'red', r: (r) => r.abort('connectionrefused') },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>x</h1>' }) },
  { n: 'incompleto', r: (r) => r.fulfill(json(200, { tarifa_hora_gestion: null })) },
]) {
  test(`pie: si la peticion falla (${f.n}) el texto queda legible, sin pie y sin aviso`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await publica(page, { danos: f.r });
    await page.goto('/legal/condiciones-de-contratacion/');
    await expect(page.getByText('Texto de las condiciones.')).toBeVisible();
    await expect(valores(page)).toHaveCount(0);
    await expect(page.locator('.aviso')).toHaveCount(0);
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    expect(consola).toEqual([]);
  });
}

test('pie: 320 px no desborda', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await publica(page);
  await page.goto('/legal/condiciones-de-contratacion/');
  await expect(valores(page)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  await page.screenshot({ path: 'pruebas/capturas/rf20-pie-condiciones-320.png', fullPage: true });
});
