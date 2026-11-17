// RF-18 (CA-08, CA-09, CA-10, CA-13, CA-16): reprogramar una reserva y reprogramar sin costo tras una cancelacion del estudio.
// La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima. La reserva dura 2 h el vie 18 dic 15:00.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { ID, AHORA, SALA, reservaR, disponibilidad, NUEVO, NUEVO_UTC, vistaR, delEstudio } from './ayudas-rf18.js';

const RUTA = `/app/reservas/reprogramar?id=${ID}&fecha=2026-12-19`;
const SIMULAR = `/reservas/${ID}/reprogramar/simular`;
const CONFIRMAR = `/reservas/${ID}/reprogramar`;
const libre = (page, utc = NUEVO_UTC) => page.locator(`bugalu-calendario button[data-inicio="${utc}"]`).locator('visible=true').first();
const principal = (page) => page.getByRole('button', { name: 'Confirmar reprogramación' });
const r2 = (page) => page.getByRole('region', { name: /Cómo queda/ });
const anuncio = (page) => page.locator('bugalu-reservas > [data-anuncio]');

// Monta la API: reserva, perfil, sala y disponibilidad. Devuelve las peticiones a simular, confirmar y disponibilidad.
async function montar(page, { reserva = reservaR(), rol = 'cliente', simula = json(200, vistaR(2)), confirma = json(200, reservaR({ inicio: NUEVO, fin: '2026-12-19T12:00:00-05:00' })) } = {}) {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
  // Tras reprogramar, el detalle trae el nuevo horario.
  let hecho = null;
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, hecho ?? reserva)));
  await simular(page, 'GET', '/salas', json(200, [SALA]));
  const semanas = await simular(page, 'GET', '/disponibilidad', json(200, disponibilidad()));
  const simulaciones = await simular(page, 'POST', SIMULAR, typeof simula === 'function' ? simula : simula);
  const confirmaciones = await simular(page, 'POST', CONFIRMAR, async (r) => {
    if (typeof confirma === 'function') return confirma(r);
    if (confirma.status === 200) hecho = JSON.parse(confirma.body);
    return r.fulfill(confirma);
  });
  return { semanas, simulaciones, confirmaciones };
}
const elegir = async (page) => {
  await libre(page).click();
  await expect(page.getByRole('heading', { name: /Cómo queda/ })).toBeVisible();
};

test.describe('reprogramar', () => {
  for (const tm of tamanos) {
    test(`entra con la semana de la reserva, su sala fija y la ayuda, a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      const { semanas } = await montar(page);
      await page.goto(RUTA);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Reprogramar reserva R-2026-00001');
      await expect(page.getByText('Misma sala, servicio, duración y especialistas.')).toBeVisible();
      await expect(page.getByRole('heading', { name: /R1\s*Elige el nuevo horario/ })).toBeVisible();
      await expect(page.getByText('Tu sesión dura 2 h: elige dónde empieza.')).toBeVisible();
      await expect(page.locator('bugalu-calendario').getByText('SALA · SALA PRINCIPAL')).toBeVisible();
      await expect(page.locator('bugalu-calendario select')).toHaveCount(0);
      expect(semanas[0].url.searchParams.get('sala')).toBe('sala-1');
      expect(semanas[0].url.searchParams.get('excluir_reserva')).toBe(ID);
      // Lateral con la reserva actual.
      const ficha = page.getByRole('region', { name: 'Reserva actual' });
      for (const texto of ['R-2026-00001', '18 dic 2026, 15:00–17:00', 'Grabación de voces', 'S/ 200,00', 'S/ 100,00']) await expect(ficha).toContainText(texto);
      // El Primario espera una vista previa: aria-disabled y su ayuda.
      await expect(principal(page)).toHaveAttribute('aria-disabled', 'true');
      await expect(principal(page)).toHaveAccessibleDescription('Elige un horario para ver cómo queda.');
      await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
      await expect(r2(page)).toHaveCount(0);
      await expect(page.getByRole('link', { name: 'R-2026-00001', exact: true })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  for (const tm of tamanos) {
    test(`nivel 2 (CA-09): penalización 50,00 y saldo 190,00, a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      const { simulaciones } = await montar(page);
      await page.goto(RUTA);
      await libre(page).click();
      await expect(r2(page)).toBeVisible();
      expect(simulaciones).toHaveLength(1);
      expect(simulaciones[0].cuerpo).toEqual({ inicio: NUEVO });
      await expect(r2(page)).toContainText('Nuevo horario: sáb 19 dic, 10:00–12:00');
      await expect(r2(page)).toContainText('Nivel 2 · con penalización');
      const saldo = r2(page).getByRole('table', { name: 'Saldo' });
      await expect(saldo).toContainText('Nuevo total');
      await expect(saldo).toContainText('S/ 240,00');
      await expect(saldo).toContainText('Penalización (nivel 2, 25 %)');
      await expect(saldo).toContainText('S/ 50,00');
      await expect(saldo).toContainText('Ya pagaste');
      await expect(saldo).toContainText('− S/ 100,00');
      await expect(saldo).toContainText('Saldo por pagar');
      await expect(saldo).toContainText('S/ 190,00');
      await expect(saldo).not.toContainText('Pasa a crédito');
      await expect(r2(page).getByRole('table', { name: 'Nuevo precio' })).toContainText('Sala de grabación');
      await expect(r2(page)).toContainText('Después de este cambio no te quedarán más cambios de horario.');
      await expect(r2(page)).toContainText('El precio se recalcula con las tarifas vigentes del nuevo horario.');
      // El foco sigue en el calendario y el Primario queda habilitado; se anuncia el resultado.
      await expect(libre(page)).toBeFocused();
      await expect(principal(page)).not.toHaveAttribute('aria-disabled', 'true');
      await expect(anuncio(page)).toHaveText('Nuevo horario sáb 19 dic, 10:00 a 12:00: nivel 2, saldo S/ 190,00.');
      expect(new URL(page.url()).searchParams.get('inicio')).toBe(NUEVO);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/rf18-reprogramar-nivel2-${tm.nombre}.png`, fullPage: true });
    });
  }

  for (const tm of tamanos) {
    test(`nivel 1 (CA-09): saldo 0,00 y 20,00 pasan a crédito, a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      await montar(page, { simula: json(200, vistaR(1)) });
      await page.goto(RUTA);
      await elegir(page);
      await expect(r2(page)).toContainText('Nivel 1 · sin cargo');
      const saldo = r2(page).getByRole('table', { name: 'Saldo' });
      await expect(saldo).toContainText('S/ 80,00');
      await expect(saldo).not.toContainText('Penalización');
      await expect(saldo).toContainText('Nada por pagar');
      await expect(saldo).toContainText('S/ 0,00');
      await expect(saldo).toContainText('Pasa a crédito');
      await expect(saldo).toContainText('S/ 20,00');
      await expect(r2(page)).toContainText('Después de este cambio te quedará 1 cambio de horario.');
      await expect(anuncio(page)).toHaveText('Nuevo horario sáb 19 dic, 10:00 a 12:00: nivel 1, saldo S/ 0,00, pasan S/ 20,00 a crédito.');
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/rf18-reprogramar-nivel1-${tm.nombre}.png`, fullPage: true });
    });
  }

  test('confirmar manda nivel_esperado y total_esperado y vuelve al detalle con el aviso y el crédito', async ({ page }) => {
    const { confirmaciones } = await montar(page, { simula: json(200, vistaR(1)), confirma: json(200, reservaR({ inicio: NUEVO, fin: '2026-12-19T12:00:00-05:00' })) });
    await page.goto(RUTA);
    await elegir(page);
    await principal(page).click();
    await expect(page).toHaveURL(new RegExp(`/app/reservas/detalle\\?id=${ID}&aviso=reserva-reprogramada$`));
    expect(confirmaciones).toHaveLength(1);
    expect(confirmaciones[0].cuerpo).toEqual({ inicio: NUEVO, nivel_esperado: 1, total_esperado: '80.00' });
    const aviso = page.locator('[data-avisos] .aviso');
    await expect(aviso).toContainText('Reserva reprogramada al 19 dic, 10:00.');
    await expect(aviso).toContainText('Te enviamos el correo con el nuevo horario para tu calendario.');
    await expect(aviso).toContainText('S/ 20,00 pasaron a crédito.');
    await expect(aviso).toBeFocused();
    expect(new URL(page.url()).search).toBe(`?id=${ID}`);
  });

  test('confirmar: el Primario carga, y el calendario y "Volver" se bloquean', async ({ page }) => {
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await montar(page, { confirma: async (r) => { await espera; await r.fulfill(errorApi(503, 'servicio_no_disponible')); } });
    await page.goto(RUTA);
    await elegir(page);
    await principal(page).click();
    const cargando = page.getByRole('button', { name: 'Reprogramando…' });
    await expect(cargando).toHaveAttribute('aria-busy', 'true');
    await expect(cargando).toBeDisabled();
    await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('aria-disabled', 'true');
    await expect(page.locator('[data-calendario]')).toHaveJSProperty('inert', true);
    soltar();
    await expect(page.locator('[data-avisos] .aviso')).toContainText('No pudimos reprogramar: el servicio no responde');
    await expect(page.locator('[data-calendario]')).toHaveJSProperty('inert', false);
    await expect(principal(page)).toBeEnabled();
  });

  for (const [codigo, nuevo, titulo, texto] of [
    ['nivel_cambiado', vistaR(2), 'Mientras revisabas pasó un plazo: ahora es nivel 2, con penalización.', 'Revisa cómo queda y confirma de nuevo.'],
    ['precio_cambiado', vistaR(2, { precio: { ...vistaR(2).precio, total: '260.00' }, saldo: '210.00' }), 'El precio de ese horario cambió mientras revisabas.', 'Revisa el nuevo total y confirma de nuevo.'],
  ]) {
    test(`409 ${codigo}: repinta con los detalles, enfoca el aviso y se confirma otra vez`, async ({ page }) => {
      let intento = 0;
      const { confirmaciones } = await montar(page, {
        simula: json(200, vistaR(1)),
        confirma: (r) => (++intento === 1 ? r.fulfill(json(409, { error: { codigo, mensaje: 'x', detalles: nuevo } })) : r.fulfill(json(200, reservaR({ inicio: NUEVO })))),
      });
      await page.goto(RUTA);
      await elegir(page);
      await expect(r2(page)).toContainText('Nivel 1 · sin cargo');
      await principal(page).click();
      const aviso = r2(page).locator('.aviso-aviso');
      await expect(aviso).toContainText(titulo);
      await expect(aviso).toContainText(texto);
      await expect(aviso).toBeFocused();
      await expect(r2(page)).toContainText('Nivel 2 · con penalización');
      await expect(r2(page).getByRole('table', { name: 'Saldo' })).toContainText(nuevo.saldo.replace('.', ','));
      expect(confirmaciones).toHaveLength(1);
      await sinViolaciones(page);
      await principal(page).click();
      await expect(page).toHaveURL(/aviso=reserva-reprogramada/);
      expect(confirmaciones).toHaveLength(2);
      expect(confirmaciones[1].cuerpo).toEqual({ inicio: NUEVO, nivel_esperado: 2, total_esperado: nuevo.precio.total });
    });
  }

  for (const donde of ['simular', 'confirmar']) {
    test(`409 tramo_no_disponible al ${donde}: quita la elección, recarga la semana y enfoca R1`, async ({ page }) => {
      const choque = (r) => r.fulfill(errorApi(409, 'tramo_no_disponible'));
      const { semanas } = await montar(page, donde === 'simular' ? { simula: choque } : { confirma: choque });
      await page.goto(RUTA);
      await libre(page).click();
      if (donde === 'confirmar') {
        await expect(r2(page)).toBeVisible();
        await principal(page).click();
      }
      await expect(page.locator('[data-avisos] .aviso')).toContainText('Alguien reservó ese horario hace un momento. Elige otro.');
      await expect(r2(page)).toHaveCount(0);
      await expect(page.getByRole('heading', { name: /R1\s*Elige el nuevo horario/ })).toBeFocused();
      await expect(principal(page)).toHaveAttribute('aria-disabled', 'true');
      await expect(page.locator('bugalu-calendario button[aria-pressed="true"]')).toHaveCount(0);
      expect(new URL(page.url()).searchParams.has('inicio')).toBe(false);
      await expect.poll(() => semanas.length).toBeGreaterThan(1);
      await sinViolaciones(page);
    });
  }

  for (const detalles of [{ ...vistaR(2), nivel: 3 }, { nivel: 3 }]) {
    test(`409 nivel_cambiado con nivel 3 (${Object.keys(detalles).length > 1 ? 'con vista' : 'solo nivel'}) es "no permitida", nunca "sin costo"`, async ({ page }) => {
      await montar(page, { simula: json(200, vistaR(1)), confirma: (r) => r.fulfill(json(409, { error: { codigo: 'nivel_cambiado', mensaje: 'x', detalles } })) });
      await page.goto(RUTA);
      await elegir(page);
      await principal(page).click();
      await expect(page.locator('bugalu-calendario')).toHaveCount(0);
      await expect(page.locator('[data-salida] .aviso')).toContainText('Ya no puedes reprogramar esta reserva: faltan 24 h o menos para el inicio.');
      await expect(page.locator('body')).not.toContainText('sin costo');
    });
  }

  for (const [codigo, texto] of [
    ['reprogramacion_no_permitida', 'Ya no puedes reprogramar esta reserva: faltan 24 h o menos para el inicio.'],
    ['limite_reprogramaciones', 'Ya no puedes reprogramar esta reserva: usaste los cambios de horario que permite una reserva.'],
  ]) {
    for (const donde of ['simular', 'confirmar']) {
      test(`409 ${codigo} al ${donde}: sin calendario y con "Volver a la reserva"`, async ({ page }) => {
        const cierre = (r) => r.fulfill(errorApi(409, codigo));
        await montar(page, donde === 'simular' ? { simula: cierre } : { confirma: cierre });
        await page.goto(RUTA);
        await libre(page).click();
        if (donde === 'confirmar') {
          await expect(r2(page)).toBeVisible();
          await principal(page).click();
        }
        await expect(page.locator('bugalu-calendario')).toHaveCount(0);
        await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
        await expect(page.getByRole('link', { name: 'Volver a la reserva' })).toHaveAttribute('href', `/app/reservas/detalle?id=${ID}`);
        await expect(page.getByRole('heading', { name: /No se puede reprogramar/ })).toBeFocused();
        await sinViolaciones(page);
      });
    }
  }

  for (const [codigo, texto] of [
    ['fuera_de_franja', 'Ese horario ya no está publicado.'],
    ['anticipacion_insuficiente', 'Ese horario empieza demasiado pronto para reservarlo.'],
    ['anticipacion_excesiva', 'Ese horario aún no se puede reservar: está demasiado lejos.'],
  ]) {
    test(`422 ${codigo}: el texto va bajo el calendario, sin vista previa`, async ({ page }) => {
      await montar(page, { simula: (r) => r.fulfill(errorApi(422, codigo)) });
      await page.goto(RUTA);
      await libre(page).click();
      await expect(page.locator('[data-error-horario]')).toContainText(texto);
      await expect(r2(page)).toHaveCount(0);
      await expect(principal(page)).toHaveAttribute('aria-disabled', 'true');
      await sinViolaciones(page);
    });
  }

  test('un inicio donde no cabe la sesión se explica sin simular', async ({ page }) => {
    const { simulaciones } = await montar(page);
    await page.goto(RUTA);
    await libre(page, '2026-12-20T00:00:00.000Z').click(); // sáb 19, 19:00
    await expect(page.locator('[data-error-horario]')).toContainText('Tu sesión dura 2 h y desde las 19:00 solo caben 30 min. Elige otro inicio.');
    await expect(r2(page)).toHaveCount(0);
    expect(simulaciones).toHaveLength(0);
    await expect(principal(page)).toHaveAttribute('aria-disabled', 'true');
    await sinViolaciones(page);
  });

  test('elegir su propio horario actual se explica sin simular', async ({ page }) => {
    const { simulaciones } = await montar(page);
    await page.goto(RUTA);
    await libre(page, '2026-12-18T20:00:00.000Z').click(); // vie 18, 15:00
    await expect(page.locator('[data-error-horario]')).toContainText('Ese es tu horario actual. Elige otro.');
    expect(simulaciones).toHaveLength(0);
  });

  test('el Primario bloqueado no confirma y anuncia por qué', async ({ page }) => {
    const { confirmaciones } = await montar(page);
    await page.goto(RUTA);
    await principal(page).focus();
    await page.keyboard.press('Enter');
    await expect(anuncio(page)).toHaveText('Elige un horario para ver cómo queda.');
    expect(confirmaciones).toHaveLength(0);
  });

  test('simulando: R2 muestra "Calculando…" y el Primario sigue bloqueado', async ({ page }) => {
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await montar(page, { simula: async (r) => { await espera; await r.fulfill(json(200, vistaR(2))); } });
    await page.goto(RUTA);
    await libre(page).click();
    await expect(r2(page)).toContainText('Calculando cómo queda…');
    await expect(page.locator('[data-r2]')).toHaveAttribute('aria-busy', 'true');
    await expect(principal(page)).toHaveAttribute('aria-disabled', 'true');
    soltar();
    await expect(r2(page)).toContainText('Nivel 2');
  });

  test('teclado: elegir con Enter en la celda y confirmar con Enter en el Primario', async ({ page }) => {
    const { confirmaciones } = await montar(page, { confirma: json(200, reservaR({ inicio: NUEVO })) });
    await page.goto(RUTA);
    await libre(page).focus();
    await page.keyboard.press('Enter');
    await expect(r2(page)).toBeVisible();
    await expect(libre(page)).toBeFocused();
    await principal(page).focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/aviso=reserva-reprogramada/);
    expect(confirmaciones).toHaveLength(1);
  });

  test('un inicio en la URL se simula al cargar', async ({ page }) => {
    const { simulaciones } = await montar(page);
    await page.goto(`${RUTA}&inicio=${encodeURIComponent(NUEVO)}`);
    await expect(r2(page)).toContainText('Nivel 2');
    expect(simulaciones).toHaveLength(1);
  });

  // --- Sin costo (CA-13) ---
  for (const tm of tamanos) {
    test(`tras una cancelación del estudio: sin costo, sin penalización ni recálculo, a ${tm.nombre}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: tm.ancho, height: tm.alto });
      const { confirmaciones } = await montar(page, { reserva: delEstudio(), simula: json(200, vistaR(null)), confirma: json(200, reservaR({ inicio: NUEVO })) });
      await page.goto(RUTA);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Elige tu nuevo horario');
      await expect(page.locator('[data-sin-costo]')).toContainText('Sin costo: el estudio canceló tu sesión. Mantienes el precio y lo que pagaste.');
      await elegir(page);
      await expect(r2(page)).toContainText('Sin costo: el estudio canceló tu sesión');
      await expect(r2(page)).not.toContainText('Penalización');
      await expect(page.locator('[data-recalculo]')).toBeHidden();
      await expect(page.locator('[data-restantes]')).toBeHidden();
      await expect(r2(page).getByRole('table', { name: 'Saldo' })).toContainText('S/ 100,00');
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/rf18-reprogramar-sin-costo-${tm.nombre}.png`, fullPage: true });
      await principal(page).click();
      await expect(page).toHaveURL(/aviso=reserva-reprogramada/);
      expect(confirmaciones[0].cuerpo).toEqual({ inicio: NUEVO, nivel_esperado: null, total_esperado: '200.00' });
    });
  }

  test('el Administrador reprograma sin costo en nombre del cliente', async ({ page }) => {
    const { confirmaciones } = await montar(page, { rol: 'administrador', reserva: delEstudio(), simula: json(200, vistaR(null)), confirma: json(200, reservaR({ inicio: NUEVO })) });
    await page.goto(RUTA);
    await elegir(page);
    await principal(page).click();
    await expect(page).toHaveURL(/aviso=reserva-reprogramada/);
    expect(confirmaciones).toHaveLength(1);
  });

  test('una reserva que no es confirmada ni espera elección no se reprograma', async ({ page }) => {
    await montar(page, { reserva: reservaR({ estado: 'pre_reservada', vence_pago: '2026-11-16T10:00:00-05:00' }) });
    await page.goto(RUTA);
    await expect(page.locator('[data-salida] .aviso')).toContainText('Esta reserva ya no se puede reprogramar.');
    await expect(page.locator('bugalu-calendario')).toHaveCount(0);
    await sinViolaciones(page);
  });

  for (const [nombre, extra] of [['cancelada por el cliente', { estado: 'cancelada', motivo_cancelacion: 'cliente' }], ['del estudio con la elección ya hecha', { eleccion_estudio: 'devolucion' }], ['del estudio ya reprogramada', { eleccion_estudio: 'reprogramada' }]]) {
    test(`reserva ${nombre}: no se reprograma sin costo ni se ofrece el calendario`, async ({ page }) => {
      await montar(page, { reserva: delEstudio({ ...extra, ...(extra.estado ? { eleccion_estudio: undefined } : {}) }) });
      await page.goto(RUTA);
      await expect(page.locator('[data-salida] .aviso')).toContainText('Esta reserva ya no se puede reprogramar.');
      await expect(page.locator('bugalu-calendario')).toHaveCount(0);
      await expect(page.getByText('Elige tu nuevo horario')).toHaveCount(0);
    });
  }

  // --- Fallos ---
  test('un id inválido es 404', async ({ page }) => {
    await montar(page);
    await page.goto('/app/reservas/reprogramar?id=x');
    await expect(page.getByRole('heading', { name: /Reserva no encontrada/ })).toBeVisible();
    await sinViolaciones(page);
  });

  for (const [n, resp, texto, enlace] of [
    ['401', (r) => r.fulfill(errorApi(401, 'no_autenticado')), 'Tu sesión no es válida. Inicia sesión para ver tus reservas.', 'Ir al acceso'],
    ['403', (r) => r.fulfill(errorApi(403, 'sin_permiso')), 'Esta reserva no es tuya.', 'Volver a mis reservas'],
    ['404', (r) => r.fulfill(errorApi(404, 'no_encontrada')), 'No encontramos esta reserva.', 'Volver a mis reservas'],
    ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde. Inténtalo de nuevo en unos minutos.', null],
    ['red', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.', null],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<html>' }), 'Algo salió mal. Inténtalo de nuevo.', null],
  ]) {
    test(`carga con ${n}: estado propio, sin pantalla en blanco`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page);
      await simular(page, 'GET', `/reservas/${ID}`, resp);
      await page.goto(RUTA);
      await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
      if (enlace) await expect(page.getByRole('link', { name: enlace })).toBeVisible();
      else await expect(page.getByRole('button', { name: 'Reintentar' })).toBeVisible();
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  for (const [donde, n, resp, texto] of [
    ['simular', '503', (r) => r.fulfill(errorApi(503, 'x')), 'No pudimos calcular cómo queda: el servicio no responde'],
    ['simular', 'red', (r) => r.abort('connectionrefused'), 'Sin conexión'],
    ['simular', 'no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: 'x' }), 'No pudimos calcular cómo queda: algo salió mal'],
    ['confirmar', '503', (r) => r.fulfill(errorApi(503, 'x')), 'No pudimos reprogramar: el servicio no responde'],
    ['confirmar', 'red', (r) => r.abort('connectionrefused'), 'Sin conexión'],
    ['confirmar', 'no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: 'x' }), 'No pudimos reprogramar: algo salió mal'],
  ]) {
    test(`al ${donde} con ${n}: aviso de error y la elección sigue ahí, sin "Reintentar"`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await montar(page, donde === 'simular' ? { simula: resp } : { confirma: resp });
      await page.goto(RUTA);
      await libre(page).click();
      if (donde === 'confirmar') {
        await expect(r2(page)).toBeVisible();
        await principal(page).click();
      }
      const aviso = page.locator('[data-avisos] .aviso');
      await expect(aviso).toContainText(texto);
      await expect(aviso).toBeFocused();
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
      if (donde === 'confirmar') {
        await expect(r2(page)).toBeVisible();
        await expect(principal(page)).toBeEnabled();
      }
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  for (const [n, estado, texto] of [['401', 401, 'Tu sesión no es válida'], ['403', 403, 'Esta reserva no es tuya.'], ['404', 404, 'No encontramos esta reserva.']]) {
    for (const donde of ['simular', 'confirmar']) {
      test(`al ${donde} con ${n} sustituye la pantalla`, async ({ page }) => {
        const resp = (r) => r.fulfill(errorApi(estado, 'x'));
        await montar(page, donde === 'simular' ? { simula: resp } : { confirma: resp });
        await page.goto(RUTA);
        await libre(page).click();
        if (donde === 'confirmar') {
          await expect(r2(page)).toBeVisible();
          await principal(page).click();
        }
        await expect(page.locator('bugalu-calendario')).toHaveCount(0);
        await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
      });
    }
  }

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('explica que hace falta y no queda en "Cargando…"', async ({ page }) => {
      await page.goto(RUTA);
      expect(await page.content()).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('bugalu-reservas [data-salida]')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await expect(page.getByText('Cargando…')).toBeHidden();
    });
  });
});
