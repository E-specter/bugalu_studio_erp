// RF-18 (CA-08, CA-13, CA-16): lo que el detalle dice de "Reprogramar" y la elección tras una cancelación del estudio.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { ID, AHORA, reserva, vista, cuotasSinPagos, delEstudio } from './ayudas-rf18.js';

const ver = (page, query = '') => page.goto(`/app/reservas/detalle?id=${ID}${query}`);
const con = (page, r) => simular(page, 'GET', `/reservas/${ID}`, typeof r === 'function' ? r : json(200, r));
const previa = (page, v) => simular(page, 'GET', `/reservas/${ID}/cancelacion`, typeof v === 'function' ? v : json(200, v));
const reprogramar = (page) => page.getByRole('link', { name: 'Reprogramar', exact: true });
const barra = (page) => page.locator('[data-estado-reserva]');
const eleccion = (page) => page.locator('[data-boton="devolucion"]');
const sinCosto = (page) => page.getByRole('link', { name: 'Reprogramar sin costo' });
const pedir = (page) => page.getByRole('button', { name: 'Pedir la devolución íntegra' });
const panel = (page) => page.getByRole('region', { name: /Devolución íntegra · R-2026-00001/ });
const DEVOLUCION = (extra = {}) => ({ id: 'dv1', id_reserva: ID, folio: 'R-2026-00001', cliente: { id: 'u1', nombre: 'Ana Pérez' }, tipo: 'estudio', motivo: 'Cancelación del estudio', solicitada_en: '2026-11-15T15:00:00Z', estado: 'aprobada', monto_solicitado: '100.00', monto_aprobado: '100.00', limite: '2026-11-26T23:59:59-05:00', ...extra });

const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'cliente');
});

// --- Botón "Reprogramar" (spec RF-18-reprogramar, Entrada desde el detalle) ---
for (const tm of tamanos) {
  test(`detalle: el botón "Reprogramar" con su ayuda en nivel 1, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await con(page, reserva());
    await previa(page, vista(1));
    await ver(page);
    await expect(reprogramar(page)).toBeVisible();
    await expect(reprogramar(page)).toHaveAttribute('href', `/app/reservas/reprogramar?id=${ID}`);
    await expect(reprogramar(page)).toHaveAccessibleDescription('Te quedan 2 cambios de horario.');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-reprogramar-detalle-${tm.nombre}.png`, fullPage: true });
  });
}

test('detalle: en nivel 2 la ayuda avisa de la penalización', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(2, { reprogramaciones_restantes: 1 }));
  await ver(page);
  await expect(reprogramar(page)).toHaveAccessibleDescription('Te queda 1 cambio de horario. Faltan 48 h o menos: reprogramar tiene una penalización del 25 %.');
});

for (const [nombre, v, texto] of [
  ['nivel 3', vista(3), 'Ya no puedes reprogramarla: faltan 24 h o menos para el inicio.'],
  ['sin cambios restantes', vista(1, { puede_reprogramar: false, reprogramaciones_restantes: 0 }), 'Ya no puedes reprogramarla: usaste los cambios de horario que permite una reserva.'],
  ['nivel 2 ya usado', vista(2, { puede_reprogramar: false, reprogramaciones_restantes: 1 }), 'Ya la reprogramaste una vez con poco tiempo de aviso, que es el máximo en el nivel 2.'],
]) {
  test(`detalle: sin botón cuando no puede (${nombre}) y se explica`, async ({ page }) => {
    await con(page, reserva());
    await previa(page, v);
    await ver(page);
    await expect(page.locator('[data-no-reprogramar]')).toHaveText(texto);
    await expect(reprogramar(page)).toHaveCount(0);
    await sinViolaciones(page);
  });
}

test('detalle: una pre-reservada dice cuándo podrá reprogramarla', async ({ page }) => {
  const vistas = await previa(page, vista(2));
  await con(page, reserva({ estado: 'pre_reservada', vence_pago: '2026-11-16T10:00:00-05:00', cuotas: cuotasSinPagos(), pagado: '0.00' }));
  await ver(page);
  await expect(page.locator('[data-no-reprogramar]')).toHaveText('Podrás reprogramarla cuando esté confirmada.');
  await expect(reprogramar(page)).toHaveCount(0);
  expect(vistas).toHaveLength(0);
});

test('detalle: si la vista previa falla se ofrece "Reprogramar" sin ayuda: la barrera es la API', async ({ page }) => {
  await con(page, reserva());
  await previa(page, (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')));
  await ver(page);
  await expect(reprogramar(page)).toBeVisible();
  await expect(page.locator('[data-ayuda-reprogramar]')).toBeHidden();
});

test('detalle: una confirmada que ya empezó no se reprograma', async ({ page }) => {
  await con(page, reserva({ inicio: '2026-11-14T10:00:00-05:00', fin: '2026-11-14T12:00:00-05:00' }));
  await previa(page, vista(1));
  await ver(page);
  await expect(reprogramar(page)).toHaveCount(0);
  await expect(page.locator('[data-no-reprogramar]')).toBeHidden();
});

for (const rol of ['administrador', 'personal']) {
  test(`detalle: ${rol} no ve "Reprogramar" en una confirmada`, async ({ page }) => {
    await page.unroute(`${API}/perfil`);
    await comoRol(page, rol);
    await con(page, reserva());
    const vistas = await previa(page, vista(1));
    await ver(page);
    await expect(page.getByRole('heading', { name: 'Reserva', level: 2 })).toBeVisible();
    await expect(reprogramar(page)).toHaveCount(0);
    expect(vistas).toHaveLength(0);
  });
}

test('detalle: "Reprogramar" lleva a la pantalla de reprogramar', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(1));
  await ver(page);
  await reprogramar(page).click();
  await expect(page).toHaveURL(new RegExp(`/app/reservas/reprogramar\\?id=${ID}$`));
});

// --- "Reprogramar en lugar de cancelar" ---
for (const [nivel, hay] of [[1, true], [2, true], [3, false]]) {
  test(`cancelar: el enlace "Reprogramar en lugar de cancelar" ${hay ? 'aparece' : 'no aparece'} en el nivel ${nivel}`, async ({ page }) => {
    await con(page, reserva());
    await previa(page, vista(nivel));
    await ver(page);
    await page.getByRole('button', { name: 'Solicitar cancelación' }).click();
    const enlace = page.getByRole('link', { name: 'Reprogramar en lugar de cancelar' });
    if (!hay) return expect(enlace).toBeHidden();
    await expect(enlace).toBeVisible();
    await expect(enlace).toHaveAttribute('href', `/app/reservas/reprogramar?id=${ID}`);
    // Orden de foco: condiciones, reprogramar, volver, confirmar.
    await page.getByRole('link', { name: 'Leer las condiciones de cancelación' }).focus();
    await page.keyboard.press('Tab');
    await expect(enlace).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Volver a la reserva' })).toBeFocused();
    await sinViolaciones(page);
  });
}

// --- Elección tras una cancelación del estudio (CA-13) ---
for (const tm of tamanos) {
  test(`elección: dos opciones del mismo peso, sin primario, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    await con(page, delEstudio());
    await ver(page);
    await expect(barra(page)).toContainText('El estudio canceló tu sesión · elige qué hacer');
    await expect(page.locator('[data-nota-estudio]')).toHaveText('Nota del estudio: Falla en la consola principal.');
    await expect(eleccion(page)).toContainText('Eliges otro horario libre de la misma sala. Mantienes el precio y lo que pagaste.');
    await expect(eleccion(page)).toContainText('Te devolvemos S/ 100,00 por el mismo medio, en un máximo de 7 días hábiles.');
    await expect(eleccion(page)).toContainText('Mientras no elijas, nada vence.');
    await expect(sinCosto(page)).toHaveAttribute('href', `/app/reservas/reprogramar?id=${ID}`);
    // Mismo tamaño y misma variante: ninguna se empuja.
    const [a, b] = await Promise.all([sinCosto(page).boundingBox(), pedir(page).boundingBox()]);
    expect(Math.abs(a.height - b.height)).toBeLessThan(1);
    expect(Math.abs(a.width - b.width)).toBeLessThan(1);
    await expect(eleccion(page).locator('.boton-primario')).toHaveCount(0);
    await expect(page.getByRole('button', { name: /Solicitar cancelación|Cancelar reserva/ })).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-eleccion-estudio-${tm.nombre}.png`, fullPage: true });
  });
}

test('elección: "Reprogramar sin costo" lleva a la pantalla de reprogramar', async ({ page }) => {
  await con(page, delEstudio());
  await ver(page);
  await sinCosto(page).click();
  await expect(page).toHaveURL(new RegExp(`/app/reservas/reprogramar\\?id=${ID}$`));
});

for (const tm of tamanos) {
  test(`elección: pedir la devolución abre su panel, vuelve con foco y confirma, a ${tm.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: tm.ancho, height: tm.alto });
    let hecha = false;
    await con(page, (r) => r.fulfill(json(200, hecha ? delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION() }) : delEstudio())));
    const envios = await simular(page, 'POST', `/reservas/${ID}/eleccion-estudio`, async (r) => { hecha = true; await r.fulfill(json(200, delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION() }))); });
    await ver(page);
    await pedir(page).click();
    await expect(panel(page)).toBeVisible();
    await expect(page.getByRole('heading', { name: /Devolución íntegra · R-2026-00001/ })).toBeFocused();
    await expect(panel(page)).toContainText('Te devolvemos S/ 100,00 por el mismo medio con que pagaste, en un máximo de 7 días hábiles. Después ya no podrás reprogramar esta reserva.');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-eleccion-devolucion-panel-${tm.nombre}.png`, fullPage: true });
    // Volver devuelve el foco al botón que lo abrió; Escape también.
    await page.getByRole('button', { name: 'Volver', exact: true }).click();
    await expect(pedir(page)).toBeFocused();
    await pedir(page).click();
    await page.keyboard.press('Escape');
    await expect(pedir(page)).toBeFocused();
    await pedir(page).click();
    await page.getByRole('button', { name: 'Confirmar devolución' }).click();
    expect(envios[0].cuerpo).toEqual({ opcion: 'devolucion' });
    const aviso = page.locator('[data-avisos] .aviso');
    await expect(aviso).toContainText('Elegiste la devolución íntegra. Avisamos al estudio.');
    await expect(aviso).toBeFocused();
    await expect(barra(page)).toContainText('Cancelada por el estudio · devolución íntegra');
    await expect(barra(page)).toContainText('Te devolvemos S/ 100,00 en un máximo de 7 días hábiles, a más tardar el 26 nov 2026. Te avisaremos por correo cuando esté hecha.');
    await expect(eleccion(page)).toBeHidden();
    await expect(panel(page)).toBeHidden();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: `pruebas/capturas/rf18-eleccion-devolucion-elegida-${tm.nombre}.png`, fullPage: true });
  });
}

test('elección: confirmar carga y bloquea los botones del panel', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => (soltar = r));
  await con(page, delEstudio());
  await simular(page, 'POST', `/reservas/${ID}/eleccion-estudio`, async (r) => { await espera; await r.fulfill(json(200, delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION() }))); });
  await ver(page);
  await pedir(page).click();
  await page.getByRole('button', { name: 'Confirmar devolución' }).click();
  await expect(page.getByRole('button', { name: 'Confirmando…' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('button', { name: 'Volver', exact: true })).toBeDisabled();
  soltar();
  await expect(barra(page)).toContainText('devolución íntegra');
});

test('elección: la devolución realizada se dice con su fecha', async ({ page }) => {
  await con(page, delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION({ estado: 'realizada', realizada_en: '2026-11-20T15:00:00Z' }) }));
  await ver(page);
  await expect(barra(page)).toContainText('Te devolvimos S/ 100,00 el 20 nov, 10:00.');
  await expect(eleccion(page)).toBeHidden();
});

test('elección: sin el dato de la devolución, el estado sigue diciendo el plazo', async ({ page }) => {
  await con(page, delEstudio({ eleccion_estudio: 'devolucion' }));
  await ver(page);
  await expect(barra(page)).toContainText('Te devolvemos S/ 100,00 en un máximo de 7 días hábiles. Te avisaremos por correo cuando esté hecha.');
});

test('elección: con ?aviso=devolucion-elegida se muestra el éxito y se quita de la URL', async ({ page }) => {
  await con(page, delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION() }));
  await ver(page, '&aviso=devolucion-elegida');
  await expect(page.locator('[data-avisos] .aviso')).toContainText('Elegiste la devolución íntegra. Avisamos al estudio.');
  expect(new URL(page.url()).searchParams.has('aviso')).toBe(false);
});

test('elección: una elegida reprogramada deja la reserva en su estado', async ({ page }) => {
  await con(page, reserva({ eleccion_estudio: 'reprogramada' }));
  await previa(page, vista(1));
  await ver(page);
  await expect(eleccion(page)).toBeHidden();
  await expect(barra(page)).toContainText('Confirmada');
});

test('elección 409 eleccion_no_disponible: aviso informativo y el detalle se recarga', async ({ page }) => {
  let elegida = false;
  await con(page, (r) => r.fulfill(json(200, elegida ? delEstudio({ eleccion_estudio: 'devolucion', devolucion: DEVOLUCION() }) : delEstudio())));
  await simular(page, 'POST', `/reservas/${ID}/eleccion-estudio`, async (r) => { elegida = true; await r.fulfill(errorApi(409, 'eleccion_no_disponible')); });
  await ver(page);
  await pedir(page).click();
  await page.getByRole('button', { name: 'Confirmar devolución' }).click();
  const aviso = page.locator('[data-avisos] .aviso-informacion');
  await expect(aviso).toContainText('Ya se eligió qué hacer con esta reserva, quizá desde otra sesión.');
  await expect(aviso).toBeFocused();
  await expect(barra(page)).toContainText('devolución íntegra');
  await expect(eleccion(page)).toBeHidden();
  await sinViolaciones(page);
});

for (const [n, resp, texto] of [
  ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde'],
  ['red', (r) => r.abort('connectionrefused'), 'Sin conexión'],
  ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: 'x' }), 'Algo salió mal'],
]) {
  test(`elección con ${n}: aviso de error y el panel sigue abierto`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await con(page, delEstudio());
    await simular(page, 'POST', `/reservas/${ID}/eleccion-estudio`, resp);
    await ver(page);
    await pedir(page).click();
    await page.getByRole('button', { name: 'Confirmar devolución' }).click();
    await expect(page.locator('[data-avisos] .aviso-error')).toContainText(texto);
    await expect(panel(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Confirmar devolución' })).toBeEnabled();
    expect(consola).toEqual([]);
  });
}

for (const [n, estado, texto] of [['401', 401, 'Tu sesión no es válida'], ['403', 403, 'Esta reserva no es tuya.'], ['404', 404, 'No encontramos esta reserva.']]) {
  test(`elección con ${n}: sustituye la pantalla`, async ({ page }) => {
    await con(page, delEstudio());
    await simular(page, 'POST', `/reservas/${ID}/eleccion-estudio`, (r) => r.fulfill(errorApi(estado, 'x')));
    await ver(page);
    await pedir(page).click();
    await page.getByRole('button', { name: 'Confirmar devolución' }).click();
    await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
  });
}

test('elección: el Administrador elige por el cliente', async ({ page }) => {
  await page.unroute(`${API}/perfil`);
  await comoRol(page, 'administrador');
  await con(page, delEstudio());
  await ver(page);
  await expect(barra(page)).toContainText('El estudio canceló la sesión · elige por el cliente');
  await expect(eleccion(page)).toContainText('Se devuelven al cliente S/ 100,00 por el mismo medio, en un máximo de 7 días hábiles.');
  await expect(sinCosto(page)).toHaveAttribute('href', `/app/reservas/reprogramar?id=${ID}`);
  await pedir(page).click();
  await expect(panel(page)).toContainText('Se devuelven S/ 100,00 al cliente por el mismo medio con que pagó');
  await sinViolaciones(page);
});

test('elección: el personal no elige por el cliente', async ({ page }) => {
  await page.unroute(`${API}/perfil`);
  await comoRol(page, 'personal');
  await con(page, delEstudio());
  await ver(page);
  await expect(eleccion(page)).toBeHidden();
});

test('detalle: la reprogramación vuelve con ?aviso=reserva-reprogramada, el crédito y el nuevo horario', async ({ page }) => {
  await con(page, reserva({ inicio: '2026-12-19T10:00:00-05:00', fin: '2026-12-19T12:00:00-05:00' }));
  await previa(page, vista(1));
  await ver(page, '&aviso=reserva-reprogramada&credito=20.00');
  const aviso = page.locator('[data-avisos] .aviso-exito');
  await expect(aviso).toContainText('Reserva reprogramada al 19 dic, 10:00.');
  await expect(aviso).toContainText('S/ 20,00 pasaron a crédito.');
  await expect(aviso).toBeFocused();
  expect(new URL(page.url()).search).toBe(`?id=${ID}`);
  await sinViolaciones(page);
});

test('detalle: el aviso de reprogramada sin crédito no lo menciona, y un crédito inválido se ignora', async ({ page }) => {
  await con(page, reserva());
  await previa(page, vista(1));
  await ver(page, '&aviso=reserva-reprogramada&credito=<b>');
  const aviso = page.locator('[data-avisos] .aviso-exito');
  await expect(aviso).toContainText('Reserva reprogramada al 18 dic, 15:00.');
  await expect(aviso).not.toContainText('crédito.');
});

