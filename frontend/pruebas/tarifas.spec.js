// RF-02 (CA-02, CA-03, CA-04): tarifas, especialistas, recargos y feriados del Administrador. La API se simula con page.route.
import { test, expect } from '@playwright/test';
import { sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos, json, errorApi } from './ayudas-admin.js';

const SERVICIOS = [
  { id: 's1', nombre: 'Grabación de voces', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '15.00', especialistas_por_defecto: ['e1'], activo: true },
  { id: 's2', nombre: 'Mezcla', categoria: 'posproduccion', ocupa_sala: false, tarifa_hora: '0.00', monto_fijo: '350.00', especialistas_por_defecto: [], activo: false },
];
const ESPECIALISTAS = [
  { id: 'e1', nombre: 'Ingeniero de sonido', monto_fijo: '0.00', monto_variable: '25.00', unidad: 'hora', activo: true },
  { id: 'e2', nombre: 'Productor', monto_fijo: '100.00', monto_variable: '40.00', unidad: 'lapso_30', activo: false },
];
const RECARGOS = { noche: { porcentaje: '25.00', desde: '22:00', hasta: '06:00' }, fin_de_semana: { porcentaje: '10.00' }, feriado: { porcentaje: '50.00' } };
const FERIADOS = [{ fecha: '2026-12-25', nombre: 'Navidad' }, { fecha: '2026-12-08', nombre: 'Inmaculada Concepción' }];

async function base(page, extra = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z')); // "hoy" fijo: el domingo 15 nov 2026
  await comoAdministrador(page);
  const vistas = {};
  vistas.servicios = await simular(page, 'GET', '/servicios', extra.servicios ?? json(200, SERVICIOS));
  vistas.especialistas = await simular(page, 'GET', '/especialistas', extra.especialistas ?? json(200, ESPECIALISTAS));
  vistas.recargos = await simular(page, 'GET', '/recargos', json(200, RECARGOS));
  vistas.feriados = await simular(page, 'GET', '/feriados', extra.feriados ?? json(200, FERIADOS));
  return vistas;
}
const grupo = (page, nombre) => page.getByRole('group', { name: nombre });

// --- 1. Lista ---
for (const t of tamanos) {
  test(`lista: servicios y especialistas con sus tarifas a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await base(page);
    await page.goto('/app/tarifas');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Tarifas');
    await expect(page.getByRole('link', { name: 'Recargos y feriados' })).toHaveAttribute('href', '/app/tarifas/recargos');
    const servicios = page.getByRole('table', { name: 'Servicios' }).getByRole('row');
    await expect(servicios).toHaveCount(3);
    await expect(servicios.nth(1)).toContainText('Grabación de voces');
    await expect(servicios.nth(1)).toContainText('GRABACIÓN');
    await expect(servicios.nth(1)).toContainText('S/ 120,00');
    await expect(servicios.nth(1)).toContainText('S/ 15,00');
    await expect(servicios.nth(1)).toContainText('Ingeniero de sonido');
    await expect(servicios.nth(1)).toContainText('ACTIVO');
    await expect(servicios.nth(2)).toContainText('No (va por proyecto)');
    await expect(servicios.nth(2)).toContainText('INACTIVO');
    await expect(servicios.nth(2)).toContainText('—');
    await expect(page.getByRole('link', { name: 'Editar Grabación de voces' })).toHaveAttribute('href', '/app/tarifas/servicio?id=s1');
    const especialistas = page.getByRole('table', { name: 'Especialistas' }).getByRole('row');
    await expect(especialistas.nth(1)).toContainText('S/ 25,00');
    await expect(especialistas.nth(1)).toContainText('por hora');
    await expect(especialistas.nth(2)).toContainText('por media hora');
    await expect(especialistas.nth(2)).toContainText('INACTIVO');
    await expect(page.getByRole('link', { name: 'Editar Productor' })).toHaveAttribute('href', '/app/tarifas/especialista?id=e2');
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/tarifas-lista-${t.nombre}.png`, fullPage: true });
  });
}

test('lista: vacia explica y no ofrece accion', async ({ page }) => {
  await base(page, { servicios: json(200, []), especialistas: json(200, []) });
  await page.goto('/app/tarifas');
  await expect(page.getByText('Aún no hay servicios cargados.')).toBeVisible();
  await expect(page.getByText('Aún no hay especialistas cargados.')).toBeVisible();
  await expect(page.getByText('Se cargan con la base de datos inicial; avisa al equipo técnico.')).toHaveCount(2);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-lista-vacia-1440.png', fullPage: true });
});

test('lista: aviso de exito por URL solo de la lista cerrada y se quita de la URL', async ({ page }) => {
  await base(page);
  await page.goto('/app/tarifas?aviso=servicio-actualizado');
  await expect(page.getByText('Servicio actualizado. El precio nuevo se aplica a las simulaciones y reservas desde ahora.')).toBeVisible();
  await expect(page.locator('.aviso-exito')).toBeFocused();
  await expect(page).not.toHaveURL(/aviso/);
  await page.goto('/app/tarifas?aviso=lo-que-sea');
  await expect(page.locator('.aviso-exito')).toHaveCount(0);
  await page.goto('/app/tarifas?aviso=especialista-actualizado');
  await expect(page.getByText('Especialista actualizado. El precio nuevo se aplica a las simulaciones y reservas desde ahora.')).toBeVisible();
});

test('lista: servicio con datos del servidor se muestra como texto', async ({ page }) => {
  await base(page, { servicios: json(200, [{ ...SERVICIOS[0], nombre: '<img src=x onerror=window.__xss=1>' }]) });
  await page.goto('/app/tarifas');
  await expect(page.getByText('<img src=x onerror=window.__xss=1>').first()).toBeVisible();
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

// --- 2. Servicio ---
test('servicio: edita tarifa, monto fijo, especialistas por defecto y activo', async ({ page }) => {
  const consola = vigilarConsola(page);
  await base(page);
  const parches = await simular(page, 'PATCH', '/servicios/s1', json(200, SERVICIOS[0]));
  await page.goto('/app/tarifas/servicio?id=s1');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Editar servicio');
  await expect(page.getByText('Tarifa por hora y quién va incluido en Grabación de voces.')).toBeVisible();
  await expect(page.getByLabel('Tarifa por hora (S/)')).toHaveValue('120,00');
  await expect(page.getByLabel('Monto fijo (S/)')).toHaveValue('15,00');
  await expect(grupo(page, 'Especialistas por defecto').getByLabel('Ingeniero de sonido')).toBeChecked();
  await expect(grupo(page, 'Especialistas por defecto').getByLabel('Productor')).not.toBeChecked();
  await expect(page.getByLabel('Activo')).toBeChecked();
  await expect(page.getByText('Los cambios valen para las simulaciones y reservas nuevas; las ya hechas guardan su precio.')).toBeVisible();
  await expect(page.getByText('Se cobra una vez por reserva.')).toBeVisible();
  await expect(page.getByText('Van incluidos y el cliente no puede quitarlos.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-servicio-1440.png', fullPage: true });
  await page.getByLabel('Tarifa por hora (S/)').fill('120');
  await grupo(page, 'Especialistas por defecto').getByLabel('Productor').check();
  await page.getByLabel('Activo').uncheck();
  await page.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(page.getByText('Servicio actualizado. El precio nuevo se aplica')).toBeVisible();
  expect(parches[0].cuerpo).toEqual({ activo: false, especialistas_por_defecto: ['e1', 'e2'] });
  expect(consola).toEqual([]);
});

test('servicio: importes con dos decimales y sin negativos', async ({ page }) => {
  await base(page);
  const parches = await simular(page, 'PATCH', '/servicios/s1', json(200, SERVICIOS[0]));
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('-5');
  await page.getByLabel('Monto fijo (S/)').fill('10,123');
  await page.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(page.getByText('Escribe un importe de 0 o más, con hasta dos decimales, como 120,50.')).toHaveCount(2);
  await expect(page.locator('.aviso-error')).toBeFocused();
  await expect(page.getByText('Revisa 2 campos')).toBeVisible();
  expect(parches).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-servicio-errores-1440.png', fullPage: true });
});

test('servicio: id desconocido', async ({ page }) => {
  await base(page);
  await page.goto('/app/tarifas/servicio?id=nada');
  await expect(page.locator('[data-salida] .aviso')).toContainText('No encontramos este servicio.');
  await expect(page.getByRole('link', { name: 'Volver a tarifas' })).toHaveAttribute('href', '/app/tarifas');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-servicio-no-encontrado-1440.png', fullPage: true });
});

test('servicio: 403 y 404 al guardar sustituyen la vista; 422 se muestra', async ({ page }) => {
  await base(page);
  await simular(page, 'PATCH', '/servicios/s1', (r) => r.fulfill(errorApi(403, 'sin_permiso')));
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(page.getByRole('main')).toContainText('Esta sección es solo para el Administrador.');
  await simular(page, 'PATCH', '/servicios/s1', (r) => r.fulfill(errorApi(404, 'no_encontrado')));
  await page.reload();
  await page.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(page.locator('[data-salida] .aviso')).toContainText('No encontramos este servicio.');
});

test('servicio: error de red al guardar conserva los datos', async ({ page }) => {
  await base(page);
  await simular(page, 'PATCH', '/servicios/s1', (r) => r.abort('connectionrefused'));
  await page.goto('/app/tarifas/servicio?id=s1');
  await page.getByLabel('Tarifa por hora (S/)').fill('120'); // mismo importe: sin cambio sensible, un solo paso
  await page.getByRole('button', { name: 'Guardar servicio' }).click();
  await expect(page.getByText('Sin conexión. Revisa tu red y vuelve a intentarlo.')).toBeVisible();
  await expect(page.getByLabel('Tarifa por hora (S/)')).toHaveValue('120');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Guardar servicio' })).toBeEnabled();
});

// --- 3. Especialista ---
test('especialista: edita fijo, variable, unidad y activo', async ({ page }) => {
  await base(page);
  const parches = await simular(page, 'PATCH', '/especialistas/e2', json(200, ESPECIALISTAS[1]));
  await page.goto('/app/tarifas/especialista?id=e2');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Editar especialista');
  await expect(page.getByText('Cuánto suma Productor a cada reserva.')).toBeVisible();
  await expect(page.getByLabel('Monto fijo (S/)')).toHaveValue('100,00');
  await expect(page.getByLabel('Monto variable (S/)')).toHaveValue('40,00');
  await expect(grupo(page, 'Unidad').getByLabel('Por media hora')).toBeChecked();
  await expect(page.getByLabel('Activo')).not.toBeChecked();
  await expect(page.getByText('Se cobra por cada hora o media hora de la reserva, según la unidad.')).toBeVisible();
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-especialista-1440.png', fullPage: true });
  await page.getByLabel('Monto variable (S/)').fill('40'); // lo sensible igual: un solo paso (los cambios sensibles van en cambios-sensibles.spec.js)
  await page.getByLabel('Activo').check();
  await page.getByRole('button', { name: 'Guardar especialista' }).click();
  await expect(page.getByText('Especialista actualizado. El precio nuevo se aplica')).toBeVisible();
  expect(parches[0].cuerpo).toEqual({ activo: true });
});

test('especialista: id desconocido y importe invalido', async ({ page }) => {
  await base(page);
  await page.goto('/app/tarifas/especialista?id=nada');
  await expect(page.locator('[data-salida] .aviso')).toContainText('No encontramos este especialista.');
  await page.goto('/app/tarifas/especialista?id=e1');
  await page.getByLabel('Monto fijo (S/)').fill('abc');
  await page.getByRole('button', { name: 'Guardar especialista' }).click();
  await expect(page.getByText('Escribe un importe de 0 o más, con hasta dos decimales, como 120,50.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
});

// --- 4. Recargos y feriados ---
for (const t of tamanos) {
  test(`recargos: porcentajes, noche y feriados del anio a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    const { feriados } = await base(page);
    await page.goto('/app/tarifas/recargos?anio=2026');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Recargos y feriados');
    await expect(grupo(page, 'Noche').getByLabel('Recargo (%)')).toHaveValue('25');
    await expect(grupo(page, 'Noche').getByLabel('Desde')).toHaveValue('22:00');
    await expect(grupo(page, 'Noche').getByLabel('Hasta')).toHaveValue('06:00');
    await expect(grupo(page, 'Fin de semana').getByLabel('Recargo (%)')).toHaveValue('10');
    await expect(grupo(page, 'Feriado').getByLabel('Recargo (%)')).toHaveValue('50');
    await expect(page.getByText('Puede pasar la medianoche: de 22:00 a 06:00.')).toBeVisible();
    await expect(page.getByText('Se aplica a la parte variable de cada media hora que cae en ese horario, nunca al monto fijo.').first()).toBeVisible();
    expect(feriados[0].url.searchParams.get('anio')).toBe('2026');
    const filas = page.getByRole('table', { name: 'Feriados 2026' }).getByRole('row');
    await expect(filas).toHaveCount(3);
    await expect(filas.nth(1)).toContainText('8 dic 2026');
    await expect(filas.nth(1)).toContainText('Inmaculada Concepción');
    await expect(page.getByRole('link', { name: '2025' })).toHaveAttribute('href', '/app/tarifas/recargos?anio=2025');
    await expect(page.getByRole('link', { name: '2027' })).toHaveAttribute('href', '/app/tarifas/recargos?anio=2027');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/tarifas-recargos-${t.nombre}.png`, fullPage: true });
  });
}

test('recargos: guarda con PUT y porcentajes validados', async ({ page }) => {
  await base(page);
  const puts = await simular(page, 'PUT', '/recargos', json(200, RECARGOS));
  await page.goto('/app/tarifas/recargos?anio=2026');
  await grupo(page, 'Fin de semana').getByLabel('Recargo (%)').fill('-1');
  await grupo(page, 'Noche').getByLabel('Desde').fill('');
  await page.getByRole('button', { name: 'Guardar recargos' }).click();
  await expect(page.getByText('Escribe un porcentaje de 0 o más.')).toBeVisible();
  await expect(page.getByText('Elige la hora.')).toBeVisible();
  expect(puts).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/tarifas-recargos-errores-1440.png', fullPage: true });
  await grupo(page, 'Fin de semana').getByLabel('Recargo (%)').fill('10');
  await grupo(page, 'Noche').getByLabel('Desde').fill('22:00');
  await page.getByRole('button', { name: 'Guardar recargos' }).click();
  await expect(page.getByText('Recargos guardados.')).toBeVisible();
  expect(puts[0].cuerpo).toEqual({ noche: { porcentaje: '25.00', desde: '22:00', hasta: '06:00' }, fin_de_semana: { porcentaje: '10.00' }, feriado: { porcentaje: '50.00' } });
});

test('feriados: anadir, 409 en la fecha y quitar', async ({ page }) => {
  await base(page);
  const altas = await simular(page, 'POST', '/feriados', json(201, { fecha: '2026-11-01', nombre: 'Todos los Santos' }));
  const bajas = await simular(page, 'DELETE', '/feriados/2026-12-25', { status: 204, body: '' });
  await page.goto('/app/tarifas/recargos?anio=2026');
  const r2 = page.getByRole('region', { name: /Feriados 2026/ });
  await r2.getByRole('button', { name: 'Añadir feriado' }).click();
  await expect(r2.getByText('Elige la fecha.')).toBeVisible();
  await expect(r2.getByText('Escribe el nombre del feriado.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await r2.getByLabel('Fecha').fill('2026-11-01');
  await r2.getByLabel('Nombre').fill('Todos los Santos');
  await r2.getByRole('button', { name: 'Añadir feriado' }).click();
  await expect(page.getByText('Feriado añadido.')).toBeVisible();
  expect(altas[0].cuerpo).toEqual({ fecha: '2026-11-01', nombre: 'Todos los Santos' });
  await page.getByRole('button', { name: 'Quitar feriado del 25 dic' }).click();
  await expect(page.getByText('Feriado quitado.')).toBeVisible();
  expect(bajas).toHaveLength(1);
  await simular(page, 'POST', '/feriados', json(409, { error: { codigo: 'conflicto', mensaje: 'x' } }));
  await r2.getByLabel('Fecha').fill('2026-12-25');
  await r2.getByLabel('Nombre').fill('Navidad');
  await r2.getByRole('button', { name: 'Añadir feriado' }).click();
  await expect(r2.getByText('Ya hay un feriado en esa fecha.')).toBeVisible();
  await expect(page.locator('.aviso-error')).toBeFocused();
  await sinViolaciones(page);
});

test('feriados: anio sin feriados deja el formulario disponible; anio invalido usa el actual', async ({ page }) => {
  const { feriados } = await base(page, { feriados: json(200, []) });
  await page.goto('/app/tarifas/recargos?anio=2027');
  await expect(page.getByText('No hay feriados en 2027.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Añadir feriado' })).toBeVisible();
  await sinViolaciones(page);
  await page.goto('/app/tarifas/recargos?anio=abc');
  await expect(page.getByText('No hay feriados en 2026.')).toBeVisible();
  expect(feriados.at(-1).url.searchParams.get('anio')).toBe('2026');
});

test('recargos: 403 al guardar', async ({ page }) => {
  await base(page);
  await simular(page, 'PUT', '/recargos', errorApi(403, 'sin_permiso'));
  await page.goto('/app/tarifas/recargos?anio=2026');
  await page.getByRole('button', { name: 'Guardar recargos' }).click();
  await expect(page.getByRole('main')).toContainText('Esta sección es solo para el Administrador.');
});

// --- 5. Fallos de carga y sin JS ---
for (const [nombre, ruta, camino] of [['lista', '/app/tarifas', '/servicios'], ['servicio', '/app/tarifas/servicio?id=s1', '/servicios'], ['recargos', '/app/tarifas/recargos?anio=2026', '/recargos']]) {
  for (const f of fallos) {
    test(`${nombre}: respuesta ${f.n} al cargar`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await base(page);
      await simular(page, 'GET', camino, f.r);
      await page.goto(ruta);
      await expect(page.getByRole('main')).toContainText(f.texto);
      if (f.extra) await expect(page.getByRole('main')).toContainText(f.extra);
      if (f.enlace) await expect(page.getByRole('link', { name: f.enlace[0] })).toHaveAttribute('href', f.enlace[1](ruta));
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(f.reintentar ? 1 : 0);
      await expect(page.locator('[aria-busy]')).toHaveCount(0);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      if (nombre === 'lista') await page.screenshot({ path: `pruebas/capturas/tarifas-error-${f.n}-1440.png`, fullPage: true });
    });
  }
}

test('lista: carga con aria-busy mientras la API tarda', async ({ page }) => {
  await base(page);
  let soltar;
  const llega = new Promise((ok) => (soltar = ok));
  await simular(page, 'GET', '/servicios', async (r) => { await llega; await r.fulfill(json(200, SERVICIOS)); });
  await page.goto('/app/tarifas');
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
  await expect(page.getByText('Cargando…')).toBeVisible();
  soltar();
  await expect(page.getByRole('table', { name: 'Servicios' })).toBeVisible();
});

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const ruta of ['/app/tarifas', '/app/tarifas/servicio', '/app/tarifas/especialista', '/app/tarifas/recargos', '/app/tarifas/impuestos']) {
    test(`${ruta} explica que hace falta JS`, async ({ page }) => {
      await page.goto(ruta);
      expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-tarifas [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await expect(page.getByText('Cargando…')).toBeHidden();
      if (ruta.endsWith('s') || ruta.endsWith('franjas')) await page.screenshot({ path: 'pruebas/capturas/tarifas-sin-js-1440.png', fullPage: true });
    });
  }
});

// --- Revision visual TAREA-RF04-6 ---
test('N11: importes de las tablas Directorio a la derecha con tabular-nums, cabecera incluida (1440)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto('/app/tarifas');
  const tabla = page.getByRole('table', { name: 'Servicios' });
  const filas = tabla.getByRole('row');
  await expect(filas).toHaveCount(3);
  for (const celda of [tabla.getByRole('columnheader', { name: 'Tarifa por hora' }), filas.nth(1).getByRole('cell').nth(2), filas.nth(1).getByRole('cell').nth(3)]) {
    expect(await celda.evaluate((e) => getComputedStyle(e).textAlign)).toMatch(/right|end/);
    expect(await celda.evaluate((e) => getComputedStyle(e).fontVariantNumeric)).toContain('tabular-nums');
  }
  const esp = page.getByRole('table', { name: 'Especialistas' });
  expect(await esp.getByRole('row').nth(1).getByRole('cell').nth(0).evaluate((e) => getComputedStyle(e).textAlign)).toMatch(/right|end/);
  expect(await esp.getByRole('columnheader', { name: 'Monto variable' }).evaluate((e) => getComputedStyle(e).textAlign)).toMatch(/right|end/);
});

test('N12 y B2: porcentajes sin decimales y feriados como tarjetas en el lateral (1440)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await base(page);
  await page.goto('/app/tarifas/recargos?anio=2026');
  await expect(grupo(page, 'Noche').getByLabel('Recargo (%)')).toHaveValue('25');
  await expect(grupo(page, 'Fin de semana').getByLabel('Recargo (%)')).toHaveValue('10');
  await expect(grupo(page, 'Feriado').getByLabel('Recargo (%)')).toHaveValue('50');
  const fila = page.getByRole('table', { name: 'Feriados 2026' }).getByRole('row').nth(1);
  expect(await fila.evaluate((e) => getComputedStyle(e).display)).toBe('block');
});

// --- Botón bloqueado hasta navegar y vuelta con "Atrás" (bfcache) ---
test('servicio: tras guardar, el botón sigue bloqueado hasta navegar y se libera al volver desde la caché', async ({ page }) => {
  await base(page);
  await simular(page, 'PATCH', '/servicios/s1', json(200, SERVICIOS[0]));
  await page.route('**/app/tarifas?aviso=*', (ruta) => ruta.fulfill({ status: 204 })); // 204: el navegador se queda en la página, como si la navegación no llegara
  await page.goto('/app/tarifas/servicio?id=s1');
  const boton = page.locator('[data-envio]').first();
  await boton.click();
  await page.waitForTimeout(300);
  await expect(boton).toHaveAttribute('aria-busy', 'true'); // no se suelta tras el éxito
  await expect(boton).toBeDisabled();
  // Volver con "Atrás": la página sale de la caché del navegador con el botón aún en carga.
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })));
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Guardar servicio' })).toBeEnabled();
});
