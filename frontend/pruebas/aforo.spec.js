// RF-03 (CA-10 a CA-13): aforo por sala en el calendario, en el paso 04 de Reservar y en el panel F4 de Franjas.
// La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular, comoAdministrador, fallos } from './ayudas-admin.js';

const t = (dia, hora) => `2026-11-${dia}T${hora}:00-05:00`;
const sala = (extra = {}) => ({ id: 'sala-1', nombre: 'La Molina', sede: 'Lima', aforo: 6, itse: { certificado: '0123-2026', vence: '2027-03-01' }, ...extra });
const DISP = {
  limites: { desde: t('16', '10:00'), hasta: '2026-12-15T10:00:00-05:00' },
  franjas: [{ id: 'f1', inicio: t('19', '10:00'), fin: t('19', '14:00') }],
  ocupados: [], cierres: [],
  dias: ['16', '17', '18', '19', '20', '21', '22'].map((d) => ({ fecha: `2026-11-${d}`, minutos_libres: d === '19' ? 240 : 0 })),
};
const LINEA = 'Aforo máximo: 6 personas · Certificado ITSE 0123-2026';

async function montarPublico(page, { salas = () => json(200, [sala()]), rol = null } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  if (rol) await conSesion(page);
  await silenciarApi(page);
  if (rol) await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
  await page.route(`${API}/salas`, (r) => r.fulfill(salas()));
  await page.route(`${API}/disponibilidad?**`, (r) => r.fulfill(json(200, DISP)));
  await page.route(`${API}/reservas?**`, (r) => r.fulfill(json(200, [])));
  await page.route(`${API}/reservas/mias`, (r) => r.fulfill(json(200, [])));
}
const lineaCal = (page) => page.locator('bugalu-calendario [data-aforo]');

// --- Calendario ---

for (const tm of tamanos) {
  test(`calendario (reservar): aforo y certificado a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montarPublico(page);
    await page.goto('/reservar/?fecha=2026-11-16');
    await expect(lineaCal(page)).toHaveText(LINEA);
    await expect(lineaCal(page).locator('abbr')).toHaveAttribute('title', 'Inspección Técnica de Seguridad en Edificaciones');
    await expect(lineaCal(page)).not.toHaveAttribute('aria-live');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/aforo-calendario-${tm.nombre}.png`, fullPage: true });
  });
}

test('calendario: 1 persona en singular', async ({ page }) => {
  await montarPublico(page, { salas: () => json(200, [sala({ aforo: 1 })]) });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(lineaCal(page)).toHaveText('Aforo máximo: 1 persona · Certificado ITSE 0123-2026');
});

test('calendario: sin aforo no hay línea ni hueco', async ({ page }) => {
  await montarPublico(page, { salas: () => json(200, [sala({ aforo: null, itse: null })]) });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(page.getByText('Horario de Lima')).toBeVisible();
  await expect(lineaCal(page)).toHaveCount(0);
  await expect(page.getByText(/Aforo máximo/)).toHaveCount(0);
});

test('calendario: con aforo y sin certificado solo muestra el aforo', async ({ page }) => {
  await montarPublico(page, { salas: () => json(200, [sala({ itse: null })]) });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(lineaCal(page)).toHaveText('Aforo máximo: 6 personas');
});

test('calendario: certificado vencido, el público ve lo mismo y nunca "vigente" ni el vencimiento', async ({ page }) => {
  await montarPublico(page, { salas: () => json(200, [sala({ itse: { certificado: '0123-2026', vence: '2026-11-10' } })]) });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(lineaCal(page)).toHaveText(LINEA);
  await expect(page.getByText(/vigente|10 nov|2026-11-10/i)).toHaveCount(0);
});

test('calendario: con varias salas la línea cambia con el selector', async ({ page }) => {
  await montarPublico(page, { salas: () => json(200, [sala(), sala({ id: 'sala-2', nombre: 'Miraflores', aforo: 12, itse: { certificado: 'ITSE-77', vence: '2027-01-01' } })]) });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(lineaCal(page)).toHaveText(LINEA);
  await page.getByRole('combobox', { name: 'Sala' }).selectOption('sala-2');
  await expect(lineaCal(page)).toHaveText('Aforo máximo: 12 personas · Certificado ITSE ITSE-77');
});

test('calendario (agenda del personal): muestra la línea', async ({ page }) => {
  const consola = vigilarConsola(page);
  await montarPublico(page, { rol: 'personal' });
  await page.goto('/app/agenda/?vista=semana&fecha=2026-11-16');
  await expect(lineaCal(page)).toHaveText(LINEA);
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/aforo-agenda-1440.png', fullPage: true });
});

test('calendario: si GET /salas falla rige el error del calendario, sin línea', async ({ page }) => {
  await montarPublico(page, { salas: () => errorApi(503, 'servicio_no_disponible') });
  await page.goto('/reservar/?fecha=2026-11-16');
  await expect(page.locator('bugalu-calendario .aviso-titulo')).toHaveText('El calendario no responde.');
  await expect(lineaCal(page)).toHaveCount(0);
});

// --- Reservar, paso 04 ---

const INI = t('19', '10:00');
const PASO4 = `/reservar/confirmar/?inicio=${encodeURIComponent(INI)}&duracion=120&sala=sala-1&servicio=s1`;
async function montarPaso4(page, salas) {
  await montarPublico(page, { salas, rol: 'cliente' });
  await page.route(`${API}/servicios`, (r) => r.fulfill(json(200, [{ id: 's1', nombre: 'Grabación', categoria: 'grabacion', ocupa_sala: true, tarifa_hora: '120.00', monto_fijo: '0.00', especialistas_por_defecto: [], activo: true }])));
  await page.route(`${API}/especialistas`, (r) => r.fulfill(json(200, [])));
  await page.route(`${API}/impuestos`, (r) => r.fulfill(json(200, { porcentaje_igv: '18.00', precios_incluyen_igv: true })));
  await page.route(`${API}/simulaciones`, (r) => r.fulfill(json(200, { lineas: [], recargos: [], total: '240.00', anticipo: '120.00', porcentaje_adelanto: 50 })));
  await page.route(`${API}/textos-legales`, (r) => r.fulfill(json(200, [{ tipo: 'condiciones_contratacion', version: '1.0.0', tipo_cambio: 'mayor', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes: { reserva: 'Pagas el adelanto para confirmar.' }, programada: false }])));
}
const fila = (page) => page.locator('bugalu-reserva [data-revision] > div').filter({ has: page.getByText('Aforo', { exact: true }) });

for (const tm of tamanos) {
  test(`reservar 04: fila AFORO tras SALA con la regla y el certificado a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montarPaso4(page, () => json(200, [sala()]));
    await page.goto(PASO4);
    await expect(fila(page)).toContainText('Máximo 6 personas');
    await expect(fila(page)).toContainText('Cuenta a todas las personas dentro de la sala, también al personal del estudio. Al llegar indicas quiénes te acompañan; quien exceda el aforo espera en la recepción.');
    await expect(fila(page)).toContainText('Certificado ITSE 0123-2026');
    await expect(fila(page).locator('abbr')).toHaveAttribute('title', 'Inspección Técnica de Seguridad en Edificaciones');
    // Va justo después de SALA.
    await expect(page.locator('bugalu-reserva [data-revision] > div').nth(1)).toContainText('Aforo');
    await expect(page.locator('bugalu-reserva [data-revision] > div').first()).toContainText('La Molina');
    await expect(fila(page)).not.toContainText(/vigente|2027/);
    await expect(page.locator('bugalu-reserva [data-resumen] dt', { hasText: 'Aforo' })).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/aforo-reservar-04-${tm.nombre}.png`, fullPage: true });
  });
}

test('reservar 04: 1 persona en singular y sin aforo no hay fila', async ({ page }) => {
  await montarPaso4(page, () => json(200, [sala({ aforo: 1 })]));
  await page.goto(PASO4);
  await expect(fila(page)).toContainText('Máximo 1 persona');
});

test('reservar 04: sin aforo no se pinta la fila', async ({ page }) => {
  await montarPaso4(page, () => json(200, [sala({ aforo: null, itse: null })]));
  await page.goto(PASO4);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Confirma tu reserva');
  await expect(page.locator('bugalu-reserva [data-revision]')).toContainText('La Molina');
  await expect(fila(page)).toHaveCount(0);
});

test('reservar 04: si GET /salas falla, avisa y no bloquea confirmar', async ({ page }) => {
  await montarPaso4(page, () => errorApi(503, 'servicio_no_disponible'));
  await page.goto(PASO4);
  await expect(fila(page)).toContainText('No pudimos cargar el aforo; lo verás en el cartel de la sala.');
  await page.getByRole('checkbox', { name: /Acepto las Condiciones de contratación/ }).check();
  await expect(page.getByRole('button', { name: 'Confirmar reserva' })).toBeEnabled();
});

// --- Sin JavaScript ---

test.describe('sin JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('franjas y calendario explican que necesitan JavaScript', async ({ page }) => {
    await page.goto('/app/franjas');
    expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
    await expect(page.locator('bugalu-franjas [data-salida]')).toBeHidden();
    await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
    await expect(page.getByText('Cargando…')).toBeHidden();
    await page.goto('/reservar/');
    expect(await page.content()).toContain('El calendario necesita JavaScript');
    await expect(page.getByText('Cargando…')).toBeHidden();
  });
});

// --- Franjas: F4 AFORO DE LA SALA ---

async function montarFranjas(page, { salas = [sala()], salasResp } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-15T15:00:00Z'));
  await comoAdministrador(page);
  await simular(page, 'GET', '/salas', salasResp ?? json(200, salas));
  await simular(page, 'GET', '/disponibilidad', json(200, DISP));
  await simular(page, 'GET', '/franjas/sugerencia', json(200, []));
}
const f4 = (page) => page.getByRole('region', { name: /Aforo de la sala/ });
const campoAforo = (page) => f4(page).getByLabel('Aforo (personas)');
const campoCert = (page) => f4(page).getByLabel('Certificado ITSE');
const campoVence = (page) => f4(page).getByLabel('Vence el');
const guardar = (page, nombre = 'Guardar aforo') => f4(page).getByRole('button', { name: nombre });
const resumen = (page, n) => page.locator('bugalu-franjas [data-avisos]').getByText(`Revisa ${n} ${n === 1 ? 'dato' : 'datos'}`);
const llenar = async (page, aforo, cert, vence) => {
  await campoAforo(page).fill(aforo);
  await campoCert(page).fill(cert);
  await campoVence(page).fill(vence);
};
const parche = (page, resp) => simular(page, 'PATCH', '/salas/sala-1', resp);

for (const tm of tamanos) {
  test(`F4: sala con certificado vigente, campos rellenos y ayudas a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await montarFranjas(page);
    await page.goto('/app/franjas?semana=2026-W47');
    await expect(f4(page).getByRole('heading', { level: 2 })).toHaveText(/F4 Aforo de la sala/i);
    await expect(f4(page)).toContainText('Lo ven los clientes al reservar y en el calendario. Los tres datos se guardan juntos.');
    await expect(f4(page).getByText('VIGENTE', { exact: true })).toBeVisible();
    await expect(campoAforo(page)).toHaveValue('6');
    await expect(campoAforo(page)).toHaveAttribute('min', '1');
    await expect(campoAforo(page)).toHaveAttribute('max', '200');
    await expect(campoAforo(page)).toHaveAttribute('step', '1');
    await expect(campoAforo(page)).toHaveAccessibleDescription(/Sale del cálculo de aforo del certificado ITSE/);
    await expect(campoCert(page)).toHaveValue('0123-2026');
    await expect(campoCert(page)).toHaveAttribute('maxlength', '40');
    await expect(campoVence(page)).toHaveValue('2027-03-01');
    await expect(campoVence(page)).toHaveAttribute('min', '2026-11-15');
    await expect(f4(page).getByText('Mientras no lo guardes')).toBeHidden();
    await expect(page.locator('bugalu-franjas [data-itse]')).toBeHidden();
    await expect(guardar(page)).toBeVisible();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/aforo-franjas-${tm.nombre}.png`, fullPage: true });
  });
}

test('F4: sala sin aforo, campos vacíos, SIN REGISTRAR y su ayuda', async ({ page }) => {
  await montarFranjas(page, { salas: [sala({ aforo: null, itse: null })] });
  await page.goto('/app/franjas?semana=2026-W47');
  await expect(f4(page).getByText('SIN REGISTRAR')).toBeVisible();
  await expect(f4(page).getByText('Mientras no lo guardes, los clientes no ven el aforo de esta sala.')).toBeVisible();
  for (const c of [campoAforo(page), campoCert(page), campoVence(page)]) await expect(c).toHaveValue('');
  await expect(page.locator('bugalu-franjas [data-itse]')).toBeHidden();
});

// Avisos y etiqueta con la fecha de Lima (hoy = 15 nov 2026).
const vencimientos = [
  ['2026-12-15', 'VENCE EN 30 DÍAS', 'aviso', 'El certificado ITSE de la sala La Molina vence en 30 días (15 dic 2026). Cuando lo renueves, actualiza el número y el vencimiento.'],
  ['2026-11-16', 'VENCE MAÑANA', 'aviso', 'El certificado ITSE de la sala La Molina vence mañana (16 nov 2026). Cuando lo renueves, actualiza el número y el vencimiento.'],
  ['2026-11-15', 'VENCE HOY', 'aviso', 'El certificado ITSE de la sala La Molina vence hoy (15 nov 2026). Cuando lo renueves, actualiza el número y el vencimiento.'],
  ['2026-11-10', 'VENCIDO', 'error', 'El certificado ITSE de la sala La Molina venció el 10 nov 2026. Los clientes siguen viendo el aforo con ese certificado; registra el renovado cuando lo tengas.'],
];
for (const [vence, etiqueta, variante, texto] of vencimientos) {
  test(`F4: vence ${vence} -> ${etiqueta} y aviso ${variante}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await montarFranjas(page, { salas: [sala({ itse: { certificado: '0123-2026', vence } })] });
    await page.goto('/app/franjas?semana=2026-W47');
    await expect(f4(page).getByText(etiqueta, { exact: true })).toBeVisible();
    const aviso = page.locator(`bugalu-franjas [data-itse] .aviso-${variante}`);
    await expect(aviso).toContainText(texto);
    await expect(aviso).not.toHaveAttribute('role');
    await expect(aviso.getByRole('link', { name: /Actualizar certificado/ })).toBeVisible();
    // El aviso va antes de la barra del periodo.
    await expect(page.locator('bugalu-franjas [data-itse] + .gestion-periodo')).toBeVisible();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    if (etiqueta === 'VENCIDO') await page.screenshot({ path: 'pruebas/capturas/aforo-franjas-vencido-1440.png', fullPage: true });
  });
}

test('F4: 31 días es VIGENTE y sin aviso', async ({ page }) => {
  await montarFranjas(page, { salas: [sala({ itse: { certificado: 'X', vence: '2026-12-16' } })] });
  await page.goto('/app/franjas?semana=2026-W47');
  await expect(f4(page).getByText('VIGENTE', { exact: true })).toBeVisible();
  await expect(page.locator('bugalu-franjas [data-itse]')).toBeHidden();
});

test('F4: con varias salas hay un aviso por sala afectada y "Actualizar certificado" lleva el foco al campo', async ({ page }) => {
  await montarFranjas(page, {
    salas: [
      sala({ itse: { certificado: 'A', vence: '2027-06-01' } }),
      sala({ id: 'sala-2', nombre: 'Miraflores', itse: { certificado: 'B', vence: '2026-11-10' } }),
      sala({ id: 'sala-3', nombre: 'Surco', itse: { certificado: 'C', vence: '2026-11-20' } }),
    ],
  });
  await page.goto('/app/franjas?semana=2026-W47');
  await expect(page.locator('bugalu-franjas [data-itse] .aviso')).toHaveCount(2);
  await expect(guardar(page, 'Guardar aforo de La Molina')).toBeVisible();
  // Otra sala: el enlace elige esa sala y deja el foco en CERTIFICADO ITSE.
  await page.getByRole('link', { name: 'Actualizar certificado de la sala Miraflores' }).click();
  await expect(page).toHaveURL(/sala=sala-2/);
  await expect(campoCert(page)).toBeFocused();
  await expect(campoCert(page)).toHaveValue('B');
  await expect(guardar(page, 'Guardar aforo de Miraflores')).toBeVisible();
  // La sala elegida: el foco va directo, sin recargar.
  await campoAforo(page).focus();
  await page.getByRole('link', { name: 'Actualizar certificado de la sala Miraflores' }).click();
  await expect(campoCert(page)).toBeFocused();
});

test('F4: validaciones locales con error por campo, aria-describedby y resumen', async ({ page }) => {
  const consola = vigilarConsola(page);
  await montarFranjas(page);
  const vistas = await parche(page, json(200, sala()));
  await page.goto('/app/franjas?semana=2026-W47');
  const caso = async (aforo, cert, vence, errores) => {
    await llenar(page, aforo, cert, vence);
    await guardar(page).click();
    for (const [campo, texto] of errores) {
      await expect(campo(page)).toHaveAttribute('aria-invalid', 'true');
      await expect(campo(page)).toHaveAccessibleDescription(new RegExp(texto.replace(/[.()]/g, '\\$&')));
    }
    await expect(resumen(page, errores.length)).toBeVisible();
    await expect(page.locator('bugalu-franjas [data-avisos] .aviso')).toBeFocused();
  };
  await caso('', '', '', [[campoAforo, 'Escribe el aforo.'], [campoCert, 'Escribe el número del certificado.'], [campoVence, 'Elige la fecha de vencimiento.']]);
  await caso('0', 'X', '2026-11-15', [[campoAforo, 'Escribe un número entero de 1 a 200.']]);
  await caso('201', 'X', '2026-11-15', [[campoAforo, 'Escribe un número entero de 1 a 200.']]);
  await caso('2.5', 'X', '2026-11-15', [[campoAforo, 'Escribe un número entero de 1 a 200.']]);
  await caso('6', '   ', '2026-11-15', [[campoCert, 'Escribe el número del certificado.']]);
  await caso('6', 'X', '2026-11-14', [[campoVence, 'La fecha no puede ser anterior a hoy.']]);
  expect(vistas).toHaveLength(0); // nada de esto llega a la API
  // El enlace del resumen lleva al campo.
  await page.locator('bugalu-franjas [data-avisos]').getByRole('link', { name: 'Vence el' }).click();
  await expect(campoVence(page)).toBeFocused();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/aforo-franjas-errores-1440.png', fullPage: true });
});

test('F4: al salir de un campo se valida y al corregirlo el error desaparece', async ({ page }) => {
  await montarFranjas(page);
  await page.goto('/app/franjas?semana=2026-W47');
  await campoAforo(page).fill('300');
  await campoCert(page).focus();
  await expect(campoAforo(page)).toHaveAccessibleDescription(/Escribe un número entero de 1 a 200\./);
  await campoAforo(page).fill('10');
  await campoCert(page).focus();
  await expect(campoAforo(page)).not.toHaveAttribute('aria-invalid', 'true');
});

test('F4: guardando, éxito con la Sala de la respuesta, etiqueta y avisos recalculados', async ({ page }) => {
  const consola = vigilarConsola(page);
  await montarFranjas(page, { salas: [sala({ aforo: null, itse: null })] });
  let liberar;
  const espera = new Promise((r) => (liberar = r));
  const vistas = await parche(page, async (r) => { await espera; await r.fulfill(json(200, sala({ aforo: 8, itse: { certificado: 'N-9', vence: '2026-11-25' } }))); });
  await page.goto('/app/franjas?semana=2026-W47');
  await llenar(page, '8', ' N-9 ', '2026-11-25');
  await guardar(page).click();
  const boton = f4(page).getByRole('button', { name: 'Guardando…' });
  await expect(boton).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Publicar franjas' })).toBeDisabled();
  liberar();
  await expect(f4(page).getByText('Aforo guardado. Ya lo ven los clientes al reservar y en el calendario.')).toBeVisible();
  await expect(f4(page).locator('.aviso-exito')).toBeFocused();
  await expect(page.locator('bugalu-franjas [data-anuncio]')).toHaveText('Aforo guardado');
  expect(vistas[0].cuerpo).toEqual({ aforo: 8, itse_certificado: 'N-9', itse_vence: '2026-11-25' });
  expect(vistas[0].url.pathname).toBe('/api/v1/salas/sala-1');
  await expect(f4(page).getByText('VENCE EN 10 DÍAS')).toBeVisible();
  await expect(page.locator('bugalu-franjas [data-itse] .aviso-aviso')).toContainText('vence en 10 días (25 nov 2026)');
  await expect(f4(page).getByText('Mientras no lo guardes')).toBeHidden();
  await expect(campoCert(page)).toHaveValue('N-9');
  await expect(page.getByRole('button', { name: 'Publicar franjas' })).toBeEnabled();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/aforo-franjas-exito-1440.png', fullPage: true });
});

const campoApi = (campo, codigo = 'datos_invalidos') => json(422, { error: { codigo, mensaje: 'x', ...(campo && { detalles: { campo } }) } });
for (const [campo, getter, texto] of [
  ['aforo', campoAforo, 'Escribe un número entero de 1 a 200.'],
  ['itse_certificado', campoCert, 'Usa hasta 40 caracteres, en una sola línea.'],
  ['itse_vence', campoVence, 'Elige la fecha de vencimiento.'],
]) {
  test(`F4: 422 datos_invalidos con detalles.campo=${campo}`, async ({ page }) => {
    await montarFranjas(page);
    await parche(page, campoApi(campo));
    await page.goto('/app/franjas?semana=2026-W47');
    await guardar(page).click();
    await expect(getter(page)).toHaveAttribute('aria-invalid', 'true');
    await expect(getter(page)).toHaveAccessibleDescription(new RegExp(texto.replace(/[.()]/g, '\\$&')));
    await expect(resumen(page, 1)).toBeVisible();
    await expect(campoAforo(page)).toHaveValue('6');
  });
}

for (const [nombre, resp] of [['sin campo', campoApi(null)], ['con un campo desconocido', campoApi('otro')]]) {
  test(`F4: 422 datos_invalidos ${nombre}`, async ({ page }) => {
    await montarFranjas(page);
    await parche(page, resp);
    await page.goto('/app/franjas?semana=2026-W47');
    await guardar(page).click();
    await expect(page.locator('bugalu-franjas [data-avisos] .aviso-error')).toContainText('No pudimos guardar el aforo con estos datos. Revisa los tres campos.');
    await expect(campoAforo(page)).toHaveValue('6');
    await expect(campoCert(page)).toHaveValue('0123-2026');
  });
}

test('F4: 422 itse_vencido muestra el error bajo VENCE EL y el resumen', async ({ page }) => {
  await montarFranjas(page);
  await parche(page, campoApi(null, 'itse_vencido'));
  await page.goto('/app/franjas?semana=2026-W47');
  await guardar(page).click();
  await expect(campoVence(page)).toHaveAccessibleDescription(/La fecha no puede ser anterior a hoy \(hora de Lima\)\./);
  await expect(campoVence(page)).toHaveAttribute('aria-invalid', 'true');
  await expect(resumen(page, 1)).toBeVisible();
});

test('F4: 404 avisa y recarga GET /salas', async ({ page }) => {
  await montarFranjas(page);
  // La primera carga trae sala-1; tras el 404, la lista ya no la tiene.
  let cargas = 0;
  const salas = await simular(page, 'GET', '/salas', (r) => r.fulfill(json(200, cargas++ ? [sala({ id: 'sala-9', nombre: 'Barranco' })] : [sala()])));
  await parche(page, errorApi(404, 'sala_no_encontrada'));
  await page.goto('/app/franjas?semana=2026-W47');
  await guardar(page).click();
  await expect(page.locator('bugalu-franjas [data-avisos] .aviso-informacion')).toContainText('Esa sala ya no existe. Actualizamos la lista de salas.');
  await expect.poll(() => salas.length).toBeGreaterThan(1);
  await expect(page.locator('bugalu-franjas [data-avisos] .aviso-informacion')).toBeFocused();
  await expect(campoCert(page)).toHaveValue('0123-2026');
});

const fallosGuardar = [
  ['401', (r) => r.fulfill(errorApi(401, 'no_autenticado')), 'Tu sesión no es válida'],
  ['403', (r) => r.fulfill(errorApi(403, 'sin_permiso')), 'Esta sección es solo para el Administrador.'],
  ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde. Inténtalo de nuevo en unos minutos.'],
  ['red', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.'],
  ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), 'Algo salió mal. Inténtalo de nuevo.'],
];
for (const [nombre, resp, texto] of fallosGuardar) {
  test(`F4: al guardar, ${nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await montarFranjas(page);
    await parche(page, resp);
    await page.goto('/app/franjas?semana=2026-W47');
    await campoAforo(page).fill('9');
    await guardar(page).click();
    await expect(page.locator('bugalu-franjas').getByText(texto).first()).toBeVisible();
    if (nombre === '401') await expect(page.getByRole('link', { name: 'Ir al acceso interno' })).toBeVisible();
    else if (nombre === '403') await expect(page.getByRole('link', { name: 'Volver al inicio' })).toBeVisible();
    else {
      // Sin "Reintentar" y con los datos conservados.
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
      await expect(campoAforo(page)).toHaveValue('9');
      await expect(guardar(page)).toBeEnabled();
    }
    expect(consola).toEqual([]);
  });
}

for (const f of fallos) {
  test(`F4: al cargar GET /salas, ${f.n}`, async ({ page }) => {
    await montarFranjas(page, { salasResp: f.r });
    await page.goto('/app/franjas?semana=2026-W47');
    await expect(page.locator('bugalu-franjas').getByText(f.texto.split('. ')[0]).first()).toBeVisible();
    await expect(f4(page)).toHaveCount(0);
  });
}
