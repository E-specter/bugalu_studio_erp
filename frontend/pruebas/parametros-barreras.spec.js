// RF-20 (CA-04 a CA-06, CA-09): los parametros sensibles de /app/franjas/parametros pasan por la revision con confirmacion escrita. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, json, errorApi } from './ayudas-admin.js';

const PARAMETROS = {
  dias_limite_pago: 3, horas_limite_pago: 24, anticipacion_minima_horas: 2, anticipacion_maxima_semanas: 8,
  porcentaje_adelanto: 50, horas_nivel_1: 48, horas_nivel_2: 24, porcentaje_penalizacion_nivel_2: 25, minutos_tolerancia_inasistencia: 15,
  dias_vigencia_credito: 30, reprogramaciones_nivel_1: 2, reprogramaciones_nivel_2: 1,
};
const previa = (cambios, extra = {}) => ({
  token: 't1', expira_en: '2026-11-16T15:10:00Z', palabra: 'CONFIRMAR', recurso: 'parametros', id_recurso: null, nombre_recurso: 'Parámetros de reserva',
  cambios,
  impacto: { ejemplos: [{ concepto: 'Adelanto de una reserva de S/ 200,00', tipo: 'importe', antes: '100.00', despues: '60.00' }], operaciones_vigentes: 4 },
  ...extra,
});
const CAMBIOS_PREVIA = [{ campo: 'porcentaje_adelanto', anterior: '50', nuevo: '30' }, { campo: 'dias_vigencia_credito', anterior: '30', nuevo: '1' }, { campo: 'reprogramaciones_nivel_1', anterior: '2', nuevo: '3' }];
const CONFIRMADA = { recurso: 'parametros', id_recurso: null, valor: PARAMETROS, cambios: [] };

// `actuales` es el estado "del servidor": el GET de despues de confirmar ve los valores nuevos.
async function base(page, { previsualizar = json(200, previa(CAMBIOS_PREVIA)), confirmar = json(200, CONFIRMADA) } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-16T15:00:00Z'));
  await comoAdministrador(page);
  let actuales = PARAMETROS;
  await simular(page, 'GET', '/parametros', (r) => r.fulfill(json(200, actuales)));
  const patches = await simular(page, 'PATCH', '/parametros', (r) => {
    actuales = { ...actuales, ...r.request().postDataJSON() };
    return r.fulfill(json(200, actuales));
  });
  return {
    patches,
    previas: await simular(page, 'POST', '/cambios-sensibles/previsualizar', previsualizar),
    confirmaciones: await simular(page, 'POST', '/cambios-sensibles/confirmar', (r) => {
      if (typeof confirmar === 'function') return confirmar(r);
      actuales = { ...actuales, porcentaje_adelanto: 30, dias_vigencia_credito: 1, reprogramaciones_nivel_1: 3 };
      return r.fulfill(confirmar);
    }),
  };
}
const guardar = (page) => page.getByRole('button', { name: 'Guardar parámetros' });
const aplicar = (page) => page.getByRole('button', { name: 'Aplicar cambio' });
const palabra = (page) => page.getByLabel('Escribe CONFIRMAR');
const dice = (page, texto) => expect(page.locator('.aviso').filter({ hasText: texto }).first()).toBeVisible();
async function aRevision(page, extra = async () => {}) {
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Adelanto para confirmar (%)').fill('30');
  await page.getByLabel('Vigencia del crédito (días)').fill('1');
  await page.getByLabel('Reprogramaciones del nivel 1').fill('3');
  await extra();
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
}

for (const t of tamanos) {
  test(`parametros: los 8 campos de cancelacion y adelanto con sus valores a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await base(page);
    await page.goto('/app/franjas/parametros');
    await expect(page.getByRole('heading', { name: /P3 Cancelación y adelanto/i })).toBeVisible();
    const valores = { 'Adelanto para confirmar (%)': '50', 'Límite del nivel 1 (horas)': '48', 'Límite del nivel 2 (horas)': '24', 'Penalización del nivel 2 (%)': '25', 'Tolerancia de inasistencia (min)': '15', 'Vigencia del crédito (días)': '30', 'Reprogramaciones del nivel 1': '2', 'Reprogramaciones del nivel 2': '1' };
    for (const [etiqueta, v] of Object.entries(valores)) await expect(page.getByLabel(etiqueta)).toHaveValue(v);
    await expect(page.getByText('Si cambias un plazo, un porcentaje o un límite, te mostraremos el impacto y te pediremos confirmarlo.')).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/parametros-p3-${t.nombre}.png`, fullPage: true });
    expect(consola).toEqual([]);
  });
}

for (const t of tamanos) {
  test(`parametros: un cambio sensible abre la revision y se confirma a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const v = await base(page);
    await aRevision(page);
    expect(v.previas[0].cuerpo).toEqual({ recurso: 'parametros', cambios: { porcentaje_adelanto: 30, dias_vigencia_credito: 1, reprogramaciones_nivel_1: 3 } });
    const c1 = page.getByRole('table', { name: 'Qué cambia' });
    await expect(c1).toContainText('ADELANTO PARA CONFIRMAR');
    await expect(c1).toContainText('50 %');
    await expect(c1).toContainText('30 %');
    await expect(c1).toContainText('VIGENCIA DEL CRÉDITO');
    await expect(c1).toContainText('30 días');
    await expect(c1).toContainText('1 día');
    await expect(c1).toContainText('REPROGRAMACIONES DEL NIVEL 1');
    await dice(page, '4 reservas vigentes conservan sus condiciones');
    await expect(aplicar(page)).toHaveAttribute('aria-disabled', 'true');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/parametros-revision-${t.nombre}.png`, fullPage: true });
    await palabra(page).fill('CONFIRMAR');
    await aplicar(page).click();
    await dice(page, 'Parámetros guardados');
    await expect(page.getByRole('link', { name: 'Ver en el registro de cambios' })).toHaveAttribute('href', '/app/cambios?recurso=parametros');
    await expect(page.getByLabel('Adelanto para confirmar (%)')).toHaveValue('30');
    await expect(guardar(page)).toBeVisible();
    expect(v.confirmaciones[0].cuerpo).toEqual({ token: 't1', palabra: 'CONFIRMAR' });
    expect(v.patches).toHaveLength(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('parametros: los plazos de pago tambien son sensibles', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Horas desde la solicitud').fill('12');
  await guardar(page).click();
  await expect(page.getByRole('heading', { name: /Qué cambia/i })).toBeFocused();
  expect(v.previas[0].cuerpo.cambios).toEqual({ horas_limite_pago: 12 });
});

test('parametros: tras confirmar envia por el endpoint de siempre la anticipacion', async ({ page }) => {
  const v = await base(page);
  await aRevision(page, () => page.getByLabel('Anticipación mínima (horas)').fill('5'));
  expect(v.previas[0].cuerpo.cambios).not.toHaveProperty('anticipacion_minima_horas');
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Parámetros guardados');
  expect(v.patches[0].cuerpo).toEqual({ anticipacion_minima_horas: 5 });
});

test('parametros: confirmado pero falla la anticipacion, avisa y recarga', async ({ page }) => {
  await base(page);
  await simular(page, 'PATCH', '/parametros', errorApi(503, 'servicio_no_disponible'));
  await aRevision(page, () => page.getByLabel('Anticipación mínima (horas)').fill('5'));
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Los parámetros se cambiaron, pero no pudimos guardar Anticipación. Vuelve a guardar.');
  await expect(guardar(page)).toBeVisible();
});

test('parametros: solo anticipacion cambiada se guarda en un paso, sin revision', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Anticipación máxima (semanas)').fill('10');
  await guardar(page).click();
  await dice(page, 'Parámetros guardados');
  expect(v.previas).toHaveLength(0);
  expect(v.patches).toHaveLength(1);
});

test('parametros: cancelar vuelve al formulario con lo escrito, sin aplicar, y el foco al boton', async ({ page }) => {
  const v = await base(page);
  await aRevision(page);
  await page.getByRole('button', { name: 'Cancelar' }).click();
  await dice(page, 'No se aplicó ningún cambio.');
  await expect(page.getByLabel('Adelanto para confirmar (%)')).toHaveValue('30');
  await expect(guardar(page)).toBeFocused();
  expect(v.confirmaciones).toHaveLength(0);
  await sinViolaciones(page);
});

test('parametros: validacion local de cada campo y del nivel 2 frente al nivel 1', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Adelanto para confirmar (%)').fill('101');
  await page.getByLabel('Penalización del nivel 2 (%)').fill('2.5');
  await page.getByLabel('Tolerancia de inasistencia (min)').fill('-1');
  await guardar(page).click();
  await expect(page.getByText('Escribe un número entero de 1 a 100.')).toBeVisible();
  await expect(page.getByText('Escribe un número entero de 0 a 100.')).toBeVisible();
  await expect(page.getByText('Escribe un número entero de 0 o más.')).toBeVisible();
  await expect(page.getByLabel('Adelanto para confirmar (%)')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('.aviso-error')).toBeFocused();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/parametros-p3-errores-1440.png', fullPage: true });
  await page.getByLabel('Adelanto para confirmar (%)').fill('50');
  await page.getByLabel('Penalización del nivel 2 (%)').fill('25');
  await page.getByLabel('Tolerancia de inasistencia (min)').fill('15');
  await page.getByLabel('Límite del nivel 2 (horas)').fill('48');
  await guardar(page).click();
  await expect(page.getByText('Debe ser menor que el límite del nivel 1 (48 h).')).toBeVisible();
  expect(v.previas).toHaveLength(0);
  expect(v.patches).toHaveLength(0);
});

test('parametros: 422 plazos_incoherentes de la vista previa marca el nivel 2', async ({ page }) => {
  await base(page, { previsualizar: errorApi(422, 'plazos_incoherentes') });
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Límite del nivel 1 (horas)').fill('72'); // coherente aqui; el servidor lo contradice
  await guardar(page).click();
  await expect(page.getByLabel('Límite del nivel 2 (horas)')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText('Debe ser menor que el límite del nivel 1 (72 h).').first()).toBeVisible();
});

test('parametros: 422 sin_cambios avisa que ya tiene esos valores', async ({ page }) => {
  await base(page, { previsualizar: errorApi(422, 'sin_cambios') });
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Adelanto para confirmar (%)').fill('40');
  await guardar(page).click();
  await dice(page, 'Ya tiene esos valores. No hay nada que cambiar.');
});

test('parametros: 428 sin cambios sensibles propios recarga y avisa, sin revision engañosa', async ({ page }) => {
  const v = await base(page);
  await simular(page, 'PATCH', '/parametros', json(428, { error: { codigo: 'confirmacion_requerida', mensaje: 'x', detalles: { campos: ['porcentaje_adelanto'] } } }));
  let lecturas = 0;
  page.on('request', (r) => r.method() === 'GET' && r.url().includes('/parametros') && lecturas++);
  await page.goto('/app/franjas/parametros');
  const antes = lecturas;
  await page.getByLabel('Anticipación mínima (horas)').fill('4');
  await guardar(page).click(); // solo anticipacion: un paso -> otro administrador cambio un sensible y el servidor responde 428
  await dice(page, 'Otro administrador cambió los parámetros. Revisa los valores y vuelve a guardar.');
  expect(lecturas).toBeGreaterThan(antes);
  expect(v.patches).toHaveLength(0); // el 428 simulado reemplaza al PATCH de base
  expect(v.previas).toHaveLength(0);
  await expect(page.getByText('Ya tiene esos valores')).toHaveCount(0);
});

test('parametros: la ruta sin revision envia solo los campos cambiados', async ({ page }) => {
  const v = await base(page);
  await page.goto('/app/franjas/parametros');
  await page.getByLabel('Anticipación máxima (semanas)').fill('10');
  await guardar(page).click();
  await dice(page, 'Parámetros guardados');
  expect(v.patches[0].cuerpo).toEqual({ anticipacion_maxima_semanas: 10 });
});

test('parametros: cambio_desactualizado vuelve a pedir la vista previa y vacia la palabra', async ({ page }) => {
  let n = 0;
  await base(page, {
    previsualizar: (r) => r.fulfill(json(200, previa(CAMBIOS_PREVIA, { token: `t${++n}` }))),
    confirmar: (r) => r.fulfill(errorApi(409, 'cambio_desactualizado')),
  });
  await aRevision(page);
  await palabra(page).fill('CONFIRMAR');
  await aplicar(page).click();
  await dice(page, 'Otro administrador cambió Parámetros de reserva mientras revisabas.');
  await expect(palabra(page)).toHaveValue('');
  await sinViolaciones(page);
});

test('parametros: teclado, Enter en el campo aplica', async ({ page }) => {
  const v = await base(page);
  await aRevision(page);
  await page.keyboard.press('Tab');
  await expect(palabra(page)).toBeFocused();
  await page.keyboard.type('CONFIRMAR');
  await page.keyboard.press('Enter');
  await dice(page, 'Parámetros guardados');
  expect(v.confirmaciones).toHaveLength(1);
});
