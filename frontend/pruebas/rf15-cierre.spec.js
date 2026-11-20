// RF-15 etapa C: cerrar la asesoria (realizada / no asistio), notas internas y constancia (spec RF-15-cierre). La API se simula con page.route; "hoy" es el domingo 15 nov 2026, 10:00 en Lima.
import { test, expect } from '@playwright/test';
import { json, errorApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { AID, confirmada, asesoria, comoCliente, dentroDe, paraAdmin, paraProfesional, CLIENTE } from './ayudas-rf15b.js';

const sinDesborde = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const URL_DETALLE = `/app/asesorias/detalle?id=${AID}`;
const URL_CONSTANCIA = `/app/asesorias/constancia?id=${AID}`;
const ver = async (page, a, consulta = '') => {
  await simular(page, 'GET', `/asesorias/${AID}`, json(200, a));
  await page.goto(URL_DETALLE + consulta);
};
const aviso = (page) => page.locator('[data-avisos] .aviso');
const avisoNotas = (page) => page.locator('[data-notas-aviso] .aviso');
// Confirmada con inicio y fin a tantos minutos de "ahora" (negativos: ya empezó).
const cita = (inicio, fin, extra = {}) => confirmada({ inicio: dentroDe(inicio), fin: dentroDe(fin), ...extra });
const realizadaDe = (a) => ({ ...a, estado: 'realizada', realizada_en: dentroDe(0), constancia_disponible: true });
const panelRealizada = (page) => page.getByRole('region', { name: /Marcar realizada · A-2026-00001/ });
const panelNA = (page) => page.getByRole('region', { name: /Marcar inasistencia · A-2026-00001/ });
const botonRealizada = (page) => page.getByRole('button', { name: 'Marcar realizada', exact: true });
const botonNA = (page) => page.getByRole('button', { name: 'Marcar no asistió', exact: true });

test.describe('cerrar: ventanas de tiempo con reloj fijo', () => {
  test('antes del inicio: los dos botones deshabilitados, enfocables y con su ayuda', async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(180, 240)));
    await expect(botonRealizada(page)).toHaveAttribute('aria-disabled', 'true');
    await expect(botonNA(page)).toHaveAttribute('aria-disabled', 'true');
    await expect(page.getByText('Podrás marcarla desde las 13:00, cuando empiece.')).toBeVisible();
    await expect(page.getByText('Podrás marcarlo desde las 13:15, 15 minutos después del inicio.')).toBeVisible();
    await botonRealizada(page).focus();
    await expect(botonRealizada(page)).toBeFocused();
    await expect(botonRealizada(page)).toHaveAccessibleDescription(/cuando empiece/);
    // Pulsado: no abre el panel.
    await botonRealizada(page).click({ force: true }); // aria-disabled: Playwright lo cree deshabilitado
    await expect(panelRealizada(page)).toBeHidden();
    await expect(page.locator('#reservas-ayuda-realizada')).toHaveText('La asesoría aún no empieza. Podrás marcarla desde las 13:00.');
    await botonNA(page).click({ force: true });
    await expect(panelNA(page)).toBeHidden();
    await expect(page.locator('#reservas-ayuda-inasistencia')).toHaveText('Aún no pasaron 15 minutos desde el inicio. Podrás marcarlo desde las 13:15.');
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });

  test('entre el inicio y la tolerancia: realizada habilitada y no asistió deshabilitado; barra EN HORARIO', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-5, 55)));
    await expect(page.locator('.indicador-texto')).toHaveText('En horario de la asesoría');
    await expect(botonRealizada(page)).not.toHaveAttribute('aria-disabled', 'true');
    await expect(botonNA(page)).toHaveAttribute('aria-disabled', 'true');
    await expect(page.getByText('Podrás marcarlo desde las 10:10, 15 minutos después del inicio.')).toBeVisible();
    await expect(page.getByText(/cuando empiece/)).toBeHidden();
    await sinViolaciones(page);
  });

  test('pasada la tolerancia y tras el fin: los dos habilitados; POR CERRAR; sin límite posterior', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-30, 30)));
    await expect(botonRealizada(page)).not.toHaveAttribute('aria-disabled', 'true');
    await expect(botonNA(page)).not.toHaveAttribute('aria-disabled', 'true');
    await ver(page, paraProfesional(cita(-120 * 24, -119 * 24)));
    await expect(page.locator('.indicador-texto')).toHaveText('Por cerrar');
    await expect(page.locator('.indicador-dato')).toHaveText('Marca si se realizó o si el cliente no asistió.');
    await expect(botonRealizada(page)).not.toHaveAttribute('aria-disabled', 'true');
    await expect(botonNA(page)).not.toHaveAttribute('aria-disabled', 'true');
  });

  test('pendiente de pago: solo no asistió, y no hay "Marcar realizada"', async ({ page }) => {
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(asesoria({ inicio: dentroDe(-60), fin: dentroDe(0), vence_pago: dentroDe(60) })));
    await expect(botonRealizada(page)).toHaveCount(0);
    await expect(botonNA(page)).toBeVisible();
  });

  test('cancelada y realizada: sin botones de cierre', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60, { estado: 'cancelada' })));
    await expect(botonRealizada(page)).toHaveCount(0);
    await expect(botonNA(page)).toHaveCount(0);
    await ver(page, paraProfesional(realizadaDe(cita(-120, -60))));
    await expect(botonRealizada(page)).toHaveCount(0);
    await expect(botonNA(page)).toHaveCount(0);
  });
});

test.describe('marcar realizada', () => {
  test('flujo completo con teclado: panel, consecuencias, envío, aviso, constancia', async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60)));
    const envios = await simular(page, 'POST', `/asesorias/${AID}/realizada`, json(200, paraProfesional(realizadaDe(cita(-120, -60)))));
    await botonRealizada(page).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { name: /Marcar realizada · A-2026-00001/ })).toBeFocused();
    await expect(panelRealizada(page)).toContainText('Lu Beats tuvo su asesoría de 1 h el 15 nov, a las 08:00.');
    await expect(panelRealizada(page)).toContainText('Se emite la constancia de asistencia y se la enviamos a Lu Beats por correo. No se puede deshacer.');
    await sinViolaciones(page);
    // Escape cierra y devuelve el foco al botón.
    await page.keyboard.press('Escape');
    await expect(panelRealizada(page)).toBeHidden();
    await expect(botonRealizada(page)).toBeFocused();
    await page.keyboard.press('Enter');
    await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
    await expect(aviso(page)).toContainText('Asesoría marcada como realizada. Enviamos la constancia a Lu Beats.');
    await expect(aviso(page)).toBeFocused();
    expect(envios).toHaveLength(1);
    await expect(page.locator('.indicador-texto')).toHaveText('Realizada');
    await expect(botonRealizada(page)).toHaveCount(0);
    // Ver constancia: Secundario para quien la cerró.
    const enlace = page.getByRole('link', { name: 'Ver constancia' });
    await expect(enlace).toHaveAttribute('href', URL_CONSTANCIA);
    await expect(enlace).toHaveClass(/boton-secundario/);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: 'pruebas/capturas/rf15-cierre-realizada.png', fullPage: true });
  });

  test('?accion=cerrar lleva el foco a "Marcar realizada" y limpia la URL', async ({ page }) => {
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(cita(-120, -60)), '&accion=cerrar');
    await expect(botonRealizada(page)).toBeFocused();
    expect(new URL(page.url()).searchParams.has('accion')).toBe(false);
  });

  test('409 antes_del_inicio: el texto queda bajo el botón', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-5, 55)));
    await simular(page, 'POST', `/asesorias/${AID}/realizada`, errorApi(409, 'antes_del_inicio'));
    await botonRealizada(page).click();
    await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
    await expect(botonRealizada(page)).toBeFocused();
    await expect(page.locator('#reservas-ayuda-realizada')).toHaveText('La asesoría aún no empieza. Podrás marcarla desde las 09:55.');
    await sinViolaciones(page);
  });

  test('409 no_aplicable: se recarga y avisa del estado', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60)));
    await expect(botonRealizada(page)).toBeVisible(); // la página ya leyó la asesoría antes de cambiar la respuesta
    await simular(page, 'POST', `/asesorias/${AID}/realizada`, errorApi(409, 'no_aplicable'));
    await simular(page, 'GET', `/asesorias/${AID}`, json(200, paraProfesional(realizadaDe(cita(-120, -60)))));
    await botonRealizada(page).click();
    await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
    await expect(aviso(page)).toContainText('Esta asesoría ya está cerrada: está realizada.');
    await expect(botonRealizada(page)).toHaveCount(0);
    await sinViolaciones(page);
  });

  for (const [nombre, resp, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde'],
    ['red caída', (r) => r.abort('connectionrefused'), 'Sin conexión'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: 'no' }), 'Algo salió mal'],
  ]) {
    test(`error ${nombre}: aviso, el panel sigue abierto y se puede reintentar`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await comoCliente(page, 'profesional');
      await ver(page, paraProfesional(cita(-120, -60)));
      await simular(page, 'POST', `/asesorias/${AID}/realizada`, resp);
      await botonRealizada(page).click();
      await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
      await expect(aviso(page)).toContainText(texto);
      await expect(panelRealizada(page).getByRole('button', { name: 'Marcar realizada' })).toBeEnabled();
      await expect(panelRealizada(page).getByRole('button', { name: 'Volver a la asesoría' })).toBeEnabled();
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('envío en curso: "Marcando…" y Volver deshabilitado', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60)));
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await simular(page, 'POST', `/asesorias/${AID}/realizada`, async (r) => { await espera; await r.fulfill(json(200, paraProfesional(realizadaDe(cita(-120, -60))))); });
    await botonRealizada(page).click();
    await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
    await expect(panelRealizada(page).getByRole('button', { name: 'Marcando…' })).toHaveAttribute('aria-busy', 'true');
    await expect(panelRealizada(page).getByRole('button', { name: 'Volver a la asesoría' })).toBeDisabled();
    soltar();
    await expect(aviso(page)).toContainText('Asesoría marcada como realizada');
  });

  for (const [estado, cuerpo, titulo] of [[401, errorApi(401, 'no_autenticado'), 'Tu sesión no es válida'], [403, errorApi(403, 'sin_permiso'), 'Esta sección es para artistas.']]) {
    test(`${estado} al enviar sustituye la vista`, async ({ page }) => {
      await comoCliente(page, 'profesional');
      await ver(page, paraProfesional(cita(-120, -60)));
      await simular(page, 'POST', `/asesorias/${AID}/realizada`, cuerpo);
      await botonRealizada(page).click();
      await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
      await expect(page.locator('.aviso-titulo', { hasText: titulo })).toBeVisible();
    });
  }

  test('404 al enviar: asesoría no encontrada', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60)));
    await simular(page, 'POST', `/asesorias/${AID}/realizada`, errorApi(404, 'no_encontrada'));
    await botonRealizada(page).click();
    await panelRealizada(page).getByRole('button', { name: 'Marcar realizada' }).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'No encontramos esta asesoría.' })).toBeVisible();
  });
});

test.describe('marcar no asistió', () => {
  test('profesional: copia sin cifras, envío por /reservas/{id}/inasistencia y aviso', async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-30, 30)));
    const envios = await simular(page, 'POST', `/reservas/${AID}/inasistencia`, json(200, paraProfesional(cita(-30, 30, { estado: 'no_asistio' }))));
    await botonNA(page).click();
    await expect(panelNA(page)).toContainText('Lu Beats no llegó en los primeros 15 minutos.');
    await expect(panelNA(page)).toContainText('La asesoría queda como No asistió y lo pagado no se devuelve. Avisamos a Lu Beats por correo. No se puede deshacer.');
    await expect(panelNA(page)).not.toContainText('S/');
    await sinViolaciones(page);
    await panelNA(page).getByRole('button', { name: 'Marcar no asistió' }).click();
    await expect(aviso(page)).toContainText('Inasistencia registrada. Avisamos a Lu Beats por correo.');
    expect(envios).toHaveLength(1);
    await expect(page.locator('.indicador-texto')).toHaveText('No asistió');
    expect(consola).toEqual([]);
    await page.screenshot({ path: 'pruebas/capturas/rf15-cierre-no-asistio.png', fullPage: true });
  });

  test('Administrador: suma "Solo tú puedes tratarla después como nivel 1."', async ({ page }) => {
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(cita(-30, 30)));
    await botonNA(page).click();
    await expect(panelNA(page)).toContainText('Solo tú puedes tratarla después como nivel 1.');
  });

  test('409 tolerancia_no_cumplida: la ayuda dice desde cuándo', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-30, 30)));
    await simular(page, 'POST', `/reservas/${AID}/inasistencia`, errorApi(409, 'tolerancia_no_cumplida'));
    await botonNA(page).click();
    await panelNA(page).getByRole('button', { name: 'Marcar no asistió' }).click();
    await expect(page.locator('#reservas-ayuda-inasistencia')).toHaveText('Aún no pasaron 15 minutos desde el inicio. Podrás marcarlo desde las 09:45.');
    await expect(botonNA(page)).toBeFocused();
  });

  test('409 no_aplicable: avisa de que ya está cerrada', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-30, 30)));
    await expect(botonNA(page)).toBeVisible();
    await simular(page, 'POST', `/reservas/${AID}/inasistencia`, errorApi(409, 'no_aplicable'));
    await simular(page, 'GET', `/asesorias/${AID}`, json(200, paraProfesional(realizadaDe(cita(-30, 30)))));
    await botonNA(page).click();
    await panelNA(page).getByRole('button', { name: 'Marcar no asistió' }).click();
    await expect(aviso(page)).toContainText('Esta asesoría ya está cerrada: está realizada.');
  });
});

test.describe('quién ve qué', () => {
  test('el cliente nunca ve botones de cierre ni notas, ni siquiera con notas en la respuesta', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await ver(page, { ...cita(-120, -60), notas: 'secreto interno' });
    await expect(page.locator('.indicador-texto')).toHaveText('Terminó');
    await expect(botonRealizada(page)).toHaveCount(0);
    await expect(botonNA(page)).toHaveCount(0);
    await expect(page.getByRole('region', { name: /Notas internas/i })).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Notas' })).toBeHidden();
    expect(await page.content()).not.toContain('secreto interno');
    await sinViolaciones(page);
  });

  test('el cliente con la asesoría realizada ve "Ver constancia" como Primario', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await ver(page, realizadaDe(cita(-120, -60)));
    await expect(page.locator('.indicador-texto')).toHaveText('Realizada');
    const enlace = page.getByRole('link', { name: 'Ver constancia' });
    await expect(enlace).toHaveAttribute('href', URL_CONSTANCIA);
    await expect(enlace).toHaveClass(/boton-primario/);
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/rf15-cierre-cliente-realizada.png', fullPage: true });
  });

  test('sin constancia disponible no hay enlace', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await ver(page, { ...realizadaDe(cita(-120, -60)), constancia_disponible: false });
    await expect(page.getByRole('link', { name: 'Ver constancia' })).toHaveCount(0);
  });
});

for (const t of [...tamanos, { nombre: '320', ancho: 320, alto: 700 }]) {
  test(`detalle de cierre y notas del profesional a ${t.nombre}: sin desborde`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(-120, -60, { notas: 'Quiere un EP de cuatro temas.' })));
    await expect(botonRealizada(page)).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Notas' })).toHaveValue('Quiere un EP de cuatro temas.');
    expect(await sinDesborde(page)).toBe(true);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf15-cierre-detalle-${t.nombre}.png`, fullPage: true });
  });
}

test.describe('notas internas', () => {
  const notas = (page) => page.getByRole('textbox', { name: 'Notas' });
  const guardar = (page) => page.getByRole('button', { name: 'Guardar notas' });

  test('el profesional y el Administrador las ven; el texto de ayuda y el contador', async ({ page }) => {
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(cita(180, 240, { notas: 'Hola' })));
    const n1 = page.getByRole('region', { name: /N1 Notas internas/i });
    await expect(n1).toContainText('Solo las ven Ana Beat y el Administrador. Lu Beats nunca las ve. Útiles para la cotización: qué necesita, qué acordaron.');
    await expect(notas(page)).toHaveAttribute('maxlength', '5000');
    await expect(page.getByText('4 / 5000')).toBeVisible();
    await sinViolaciones(page);
  });

  test('contador: visible en cada tecla; el anuncio al lector solo cada 500 caracteres y al pasar 4500', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(180, 240)));
    const vivo = page.locator('[data-contador-vivo]');
    await expect(vivo).toHaveAttribute('aria-live', 'polite');
    await notas(page).fill('a'.repeat(10));
    await expect(page.getByText('10 / 5000')).toBeVisible();
    await expect(vivo).toHaveText('');
    await notas(page).fill('a'.repeat(500));
    await expect(vivo).toHaveText('500 de 5000 caracteres.');
    await notas(page).fill('a'.repeat(4600));
    await expect(vivo).toHaveText('4600 de 5000 caracteres.');
    await notas(page).fill('a'.repeat(4700));
    await expect(vivo).toHaveText('4600 de 5000 caracteres.');
    await notas(page).fill('a'.repeat(5000));
    await expect(page.getByText('5000 / 5000')).toBeVisible();
    await expect(vivo).toHaveText('5000 de 5000 caracteres.');
  });

  test('guardar: envía el texto, muestra "Guardando…" y "Notas guardadas." en N1', async ({ page }) => {
    const consola = vigilarConsola(page);
    await comoCliente(page, 'profesional');
    const base = cita(180, 240);
    await ver(page, paraProfesional(base));
    const envios = await simular(page, 'PUT', `/asesorias/${AID}/notas`, json(200, paraProfesional({ ...base, notas: 'Quiere un EP' })));
    await notas(page).fill('Quiere un EP');
    await guardar(page).click();
    await expect(avisoNotas(page)).toContainText('Notas guardadas.');
    expect(envios[0].cuerpo).toEqual({ texto: 'Quiere un EP' });
    await expect(notas(page)).toHaveValue('Quiere un EP');
    await expect(guardar(page)).toBeEnabled();
    await sinViolaciones(page);
    expect(consola).toEqual([]);
    await page.screenshot({ path: 'pruebas/capturas/rf15-cierre-notas.png', fullPage: true });
  });

  test('texto vacío borra las notas', async ({ page }) => {
    await comoCliente(page, 'profesional');
    const base = cita(180, 240);
    await ver(page, paraProfesional({ ...base, notas: 'algo' }));
    const envios = await simular(page, 'PUT', `/asesorias/${AID}/notas`, json(200, paraProfesional(base)));
    await notas(page).fill('');
    await guardar(page).click();
    await expect(avisoNotas(page)).toContainText('Notas guardadas.');
    expect(envios[0].cuerpo).toEqual({ texto: '' });
  });

  test('"Guardando…" mientras viaja', async ({ page }) => {
    await comoCliente(page, 'profesional');
    const base = cita(180, 240);
    await ver(page, paraProfesional(base));
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await simular(page, 'PUT', `/asesorias/${AID}/notas`, async (r) => { await espera; await r.fulfill(json(200, paraProfesional(base))); });
    await notas(page).fill('x');
    await guardar(page).click();
    await expect(page.getByRole('button', { name: 'Guardando…' })).toHaveAttribute('aria-busy', 'true');
    soltar();
    await expect(avisoNotas(page)).toContainText('Notas guardadas.');
  });

  test('422: error de campo con su mensaje', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(180, 240)));
    await simular(page, 'PUT', `/asesorias/${AID}/notas`, errorApi(422, 'datos_invalidos'));
    await notas(page).fill('x');
    await guardar(page).click();
    await expect(page.getByText('Las notas admiten hasta 5000 caracteres.').first()).toBeVisible();
    await expect(notas(page)).toHaveAttribute('aria-invalid', 'true');
    await expect(notas(page)).toHaveValue('x');
  });

  test('409 no_editable: aviso Información, texto conservado y sin guardar', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(180, 240)));
    await simular(page, 'PUT', `/asesorias/${AID}/notas`, errorApi(409, 'no_editable'));
    await notas(page).fill('mis notas');
    await guardar(page).click();
    await expect(avisoNotas(page)).toContainText('Ya no se pueden editar las notas de esta asesoría.');
    await expect(notas(page)).toHaveValue('mis notas');
    await expect(notas(page)).toHaveJSProperty('readOnly', true);
    await expect(guardar(page)).toBeHidden();
    await sinViolaciones(page);
  });

  test('cancelada: notas solo lectura desde el inicio', async ({ page }) => {
    await comoCliente(page, 'administrador');
    await ver(page, paraAdmin(cita(-120, -60, { estado: 'cancelada', notas: 'Se canceló' })));
    await expect(notas(page)).toHaveValue('Se canceló');
    await expect(notas(page)).toHaveJSProperty('readOnly', true);
    await expect(avisoNotas(page)).toContainText('Ya no se pueden editar las notas de esta asesoría.');
  });

  for (const [nombre, resp, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), 'El servicio no responde'],
    ['red caída', (r) => r.abort('connectionrefused'), 'Sin conexión'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: 'no' }), 'Algo salió mal'],
  ]) {
    test(`error ${nombre}: "Tus notas siguen aquí" y el texto no se pierde`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await comoCliente(page, 'profesional');
      await ver(page, paraProfesional(cita(180, 240)));
      await simular(page, 'PUT', `/asesorias/${AID}/notas`, resp);
      await notas(page).fill('mis notas');
      await guardar(page).click();
      await expect(avisoNotas(page)).toContainText(texto);
      await expect(avisoNotas(page)).toContainText('Tus notas siguen aquí; inténtalo de nuevo.');
      await expect(notas(page)).toHaveValue('mis notas');
      await expect(guardar(page)).toBeEnabled();
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('401 al guardar sustituye la vista', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await ver(page, paraProfesional(cita(180, 240)));
    await simular(page, 'PUT', `/asesorias/${AID}/notas`, errorApi(401, 'no_autenticado'));
    await notas(page).fill('x');
    await guardar(page).click();
    await expect(page.locator('.aviso-titulo', { hasText: 'Tu sesión no es válida' })).toBeVisible();
  });
});

const CONSTANCIA = {
  folio: 'A-2026-00001',
  cliente: { nombre: CLIENTE.nombre, nombre_artistico: CLIENTE.nombre_artistico },
  profesional: { nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat', especialidades: ['Producción', 'Coros'] },
  inicio: '2026-11-10T10:00:00-05:00', fin: '2026-11-10T11:00:00-05:00', duracion: 60, modalidad: 'virtual', emitida_en: '2026-11-10T11:05:00-05:00',
};
const verConstancia = async (page, resp = json(200, CONSTANCIA)) => {
  await simular(page, 'GET', `/asesorias/${AID}/constancia`, resp);
  await page.goto(URL_CONSTANCIA);
};

test.describe('constancia', () => {
  for (const t of [...tamanos, { nombre: '320', ancho: 320, alto: 700 }]) {
    test(`vista del cliente a ${t.nombre}: datos, folio, ruta y acciones`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await comoCliente(page, 'cliente');
      await verConstancia(page);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Constancia A-2026-00001');
      const panel = page.getByRole('region', { name: 'Constancia de asistencia' });
      await expect(panel).toContainText('N.º A-2026-00001');
      await expect(panel).toContainText('Bugalú Studio deja constancia de que Lu Beats (Luis Mora) asistió a una asesoría artística con Ana Beat (Ana Pérez).');
      for (const [dt, dd] of [['Cliente', 'Lu Beats (Luis Mora)'], ['Profesional', 'Ana Beat (Ana Pérez)'], ['Especialidades', 'Producción, Coros'], ['Fecha', '10 nov 2026'], ['Horario', '10:00–11:00'], ['Duración', '1 h'], ['Modalidad', 'Virtual (Google Meet)'], ['Emitida el', '10 nov 2026, 11:05']]) {
        await expect(panel.locator('dt', { hasText: new RegExp(`^${dt}$`) }).locator('xpath=following-sibling::dd[1]')).toHaveText(dd);
      }
      await expect(page.locator('.encabezado-ruta a')).toHaveText(['Inicio', 'Asesorías', 'A-2026-00001']);
      await expect(page.locator('.encabezado-ruta a').nth(1)).toHaveAttribute('href', '/app/asesorias/mias');
      await expect(page.getByRole('button', { name: 'Imprimir o guardar en PDF' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Volver a la asesoría' })).toHaveAttribute('href', URL_DETALLE);
      await expect(page.locator('bugalu-constancia input, bugalu-constancia textarea')).toHaveCount(0);
      expect(await sinDesborde(page)).toBe(true);
      await sinViolaciones(page);
      expect(consola).toEqual([]);
      await page.screenshot({ path: `pruebas/capturas/rf15-constancia-${t.nombre}.png`, fullPage: true });
    });
  }

  test('el profesional vuelve a su agenda; sin nombre artístico se muestra solo el nombre', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await verConstancia(page, json(200, { ...CONSTANCIA, cliente: { nombre: 'Luis Mora' } }));
    await expect(page.getByText('constancia de que Luis Mora asistió')).toBeVisible();
    await expect(page.locator('.encabezado-ruta a').nth(1)).toHaveAttribute('href', '/app/asesorias/agenda');
  });

  test('impresión: se imprime solo el panel, con pie; el botón llama a window.print', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await verConstancia(page);
    await page.evaluate(() => { window.__imprimio = 0; window.print = () => window.__imprimio++; });
    await page.getByRole('button', { name: 'Imprimir o guardar en PDF' }).click();
    expect(await page.evaluate(() => window.__imprimio)).toBe(1);
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
    await page.emulateMedia({ media: 'print' });
    const panel = page.getByRole('region', { name: 'Constancia de asistencia' });
    await expect(panel).toBeVisible();
    await expect(page.locator('.encabezado')).toBeHidden();
    await expect(page.locator('.cabecera')).toBeHidden();
    await expect(page.getByRole('button', { name: 'Imprimir o guardar en PDF' })).toBeHidden();
    await expect(page.getByRole('link', { name: 'Volver a la asesoría' })).toBeHidden();
    await expect(panel.locator('[data-pie]')).toHaveText('Constancia impresa desde la plataforma de Bugalú Studio el 15 nov 2026, 10:00');
    await expect(panel.locator('dl')).toHaveCSS('break-inside', 'avoid');
    await page.screenshot({ path: 'pruebas/capturas/rf15-constancia-impresion.png', fullPage: true });
  });

  test('409 constancia_no_disponible: aviso Información según quién mira', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await verConstancia(page, errorApi(409, 'constancia_no_disponible'));
    await expect(page.getByText('La constancia estará lista cuando el profesional marque la asesoría como realizada.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Volver a la asesoría' })).toHaveAttribute('href', URL_DETALLE);
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/rf15-constancia-no-disponible.png', fullPage: true });
  });

  test('409 constancia_no_disponible para el profesional: "tú"', async ({ page }) => {
    await comoCliente(page, 'profesional');
    await verConstancia(page, errorApi(409, 'constancia_no_disponible'));
    await expect(page.getByText('La constancia estará lista cuando tú marques la asesoría como realizada.')).toBeVisible();
  });

  test('carga: panel con aria-busy mientras llega', async ({ page }) => {
    await comoCliente(page, 'cliente');
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await simular(page, 'GET', `/asesorias/${AID}/constancia`, async (r) => { await espera; await r.fulfill(json(200, CONSTANCIA)); });
    await page.goto(URL_CONSTANCIA);
    await expect(page.getByText('Cargando…')).toBeVisible();
    await expect(page.locator('[data-salida] [aria-busy="true"]')).toHaveCount(1);
    soltar();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Constancia A-2026-00001');
  });

  test('404: no encontrada, con salida', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await verConstancia(page, errorApi(404, 'no_encontrada'));
    await expect(page.locator('[data-salida] .aviso')).toContainText('No encontramos esta constancia.');
    await expect(page.getByRole('link', { name: 'Volver a mis asesorías' })).toHaveAttribute('href', '/app/asesorias/mias');
    await sinViolaciones(page);
  });

  test('id que no es un UUID: no encontrada sin pedir nada', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await page.goto('/app/asesorias/constancia?id=hola');
    await expect(page.locator('[data-salida] .aviso')).toContainText('No encontramos esta constancia.');
  });

  test('401: sesión no válida con enlace al acceso', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await verConstancia(page, errorApi(401, 'no_autenticado'));
    await expect(page.locator('[data-salida] .aviso')).toContainText('Tu sesión no es válida');
    await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', /^\/acceso\?volver=/);
    await sinViolaciones(page);
  });

  test('403: sin permiso', async ({ page }) => {
    await comoCliente(page, 'cliente');
    await verConstancia(page, errorApi(403, 'sin_permiso'));
    await expect(page.locator('[data-salida] .aviso')).toContainText('Esta constancia no es tuya.');
    await sinViolaciones(page);
  });

  for (const [nombre, resp, texto] of [
    ['503', errorApi(503, 'servicio_no_disponible'), 'El servicio no responde'],
    ['red caída', (r) => r.abort('connectionrefused'), 'Sin conexión'],
    ['no JSON', { status: 200, contentType: 'text/html', body: 'no' }, 'Algo salió mal'],
  ]) {
    test(`${nombre}: error con Reintentar`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await comoCliente(page, 'cliente');
      await verConstancia(page, resp);
      await expect(page.locator('[data-salida] .aviso')).toContainText(texto);
      await simular(page, 'GET', `/asesorias/${AID}/constancia`, json(200, CONSTANCIA));
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Constancia A-2026-00001');
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('el contenido estático avisa de que necesita JavaScript', async ({ page }) => {
      await page.goto(URL_CONSTANCIA);
      expect(await page.content()).toContain('Esta sección necesita JavaScript');
      await expect(page.locator('bugalu-constancia noscript .aviso-titulo')).toBeVisible();
    });
  });
});
