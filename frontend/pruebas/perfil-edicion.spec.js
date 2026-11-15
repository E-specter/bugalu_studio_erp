// RF-01 (CA-06, CA-09, CA-12, CA-13): perfil editable, verificacion del correo, cerrar sesion y navegacion por rol.
import { test, expect } from '@playwright/test';
import { API, SB, json, errorApi, perfil, conSesion, simularAuth, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

// GET /perfil devuelve `datos`; PATCH y POST se delegan en `manejadores` y se registran en `llamadas`.
async function montar(page, datos = {}, manejadores = {}) {
  const llamadas = [];
  await page.route(`${API}/perfil**`, (r) => {
    const peticion = r.request();
    const ruta = new URL(peticion.url()).pathname.replace('/api/v1', '');
    let cuerpo = null;
    try { cuerpo = peticion.postDataJSON(); } catch {}
    llamadas.push({ metodo: peticion.method(), ruta, cuerpo });
    const manejador = manejadores[`${peticion.method()} ${ruta}`];
    if (manejador) return manejador(r, cuerpo);
    return r.fulfill(json(200, { id: 'u1', correo: 'ana@correo.com', correo_confirmado: true, nombre: 'Ana Pérez', telefono: '987654321', nombre_artistico: 'Ana Beats', rol: 'cliente', especialidad: null, ...datos }));
  });
  await conSesion(page);
  return llamadas;
}
const devolver = (extra) => (r, cuerpo) => r.fulfill(json(200, { id: 'u1', correo: 'ana@correo.com', correo_confirmado: true, nombre: 'Ana Pérez', telefono: '987654321', nombre_artistico: 'Ana Beats', rol: 'cliente', especialidad: null, ...cuerpo, ...extra }));
// La region viva oculta repite los textos: se busca fuera de ella.
const ver = (page, texto) => page.locator('bugalu-perfil :not([data-anuncio])').getByText(texto).first();
const guardar = (page) => page.getByRole('button', { name: 'Guardar cambios' });

test.describe('edicion (punto 1)', () => {
  test('muestra el formulario con los datos y la lista de solo lectura, sin axe', async ({ page }) => {
    const consola = vigilarConsola(page);
    await montar(page);
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toHaveValue('Ana Pérez');
    await expect(page.locator('[name="telefono"]')).toHaveValue('987654321');
    await expect(page.locator('[name="nombre_artistico"]')).toHaveValue('Ana Beats');
    const lista = page.locator('dl');
    await expect(lista).toContainText('ana@correo.com');
    await expect(lista).toContainText('CONFIRMADO');
    await expect(lista).toContainText('Cliente');
    await expect(ver(page, 'El rol y la especialidad los asigna el Administrador.')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2 })).toHaveText([/TUS DATOS|Tus datos/, /CUENTA|Cuenta/]);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });

  test('personal: sin nombre artistico y con especialidad en la lista', async ({ page }) => {
    await montar(page, { rol: 'personal', especialidad: 'Mezcla', nombre_artistico: null });
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await expect(page.locator('[name="nombre_artistico"]')).toHaveCount(0);
    await expect(page.locator('dl')).toContainText('Personal del estudio');
    await expect(page.locator('dl')).toContainText('Mezcla');
  });

  test('guardar envia solo lo editado por PATCH, muestra exito y deja el foco en el boton', async ({ page }) => {
    const llamadas = await montar(page, {}, { 'PATCH /perfil': devolver() });
    await page.goto('/app/perfil');
    await page.locator('[name="nombre"]').fill('Ana María');
    await page.locator('[name="telefono"]').fill('+51 987 654 321');
    await guardar(page).click();
    await expect(ver(page, 'Cambios guardados.')).toBeVisible();
    const patch = llamadas.find((l) => l.metodo === 'PATCH');
    expect(patch.cuerpo).toEqual({ nombre: 'Ana María', telefono: '+51987654321', nombre_artistico: 'Ana Beats' });
    await expect(guardar(page)).toBeFocused();
    await expect(page.locator('[name="nombre"]')).toHaveValue('Ana María');
    await sinViolaciones(page);
  });

  test('guardar anuncia una sola vez y el aviso clonado no lleva rol', async ({ page }) => {
    await montar(page, {}, { 'PATCH /perfil': devolver() });
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await page.evaluate(() => {
      window.__anuncios = [];
      const vivo = document.querySelector('[data-anuncio]');
      new MutationObserver(() => vivo.textContent && window.__anuncios.push(vivo.textContent)).observe(vivo, { childList: true, characterData: true });
    });
    await guardar(page).click();
    await expect(ver(page, 'Cambios guardados.').first()).toBeVisible();
    expect(await page.evaluate(() => window.__anuncios)).toEqual(['Cambios guardados.']);
    await expect(page.locator('bugalu-perfil [data-avisos] [role]')).toHaveCount(0);
  });

  test('nombre vacio y telefono invalido: errores bajo el campo, resumen enfocado y sin PATCH', async ({ page }) => {
    const llamadas = await montar(page);
    await page.goto('/app/perfil');
    await page.locator('[name="nombre"]').fill('');
    await page.locator('[name="telefono"]').fill('12345');
    await guardar(page).click();
    await expect(ver(page, 'Escribe tu nombre.')).toBeVisible();
    await expect(ver(page, 'Escribe entre 9 y 15 dígitos; puedes empezar con +.')).toBeVisible();
    await expect(ver(page, 'Revisa 2 campos')).toBeVisible();
    await expect(page.locator('[data-avisos] .aviso')).toBeFocused();
    await expect(page.locator('[name="nombre"]')).toHaveAttribute('aria-invalid', 'true');
    expect(llamadas.some((l) => l.metodo === 'PATCH')).toBe(false);
    await sinViolaciones(page);
    // Corregir y guardar quita los errores.
    await page.locator('[name="nombre"]').fill('Ana');
    await page.locator('[name="telefono"]').fill('987654321');
    await guardar(page).click();
    await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
  });

  for (const [codigo, mensaje] of [
    ['datos_invalidos', 'El nombre no puede tener más de 80 caracteres.'],
    ['campo_no_permitido', 'Solo un cliente tiene nombre artístico.'],
  ]) {
    test(`422 ${codigo}: aviso con el mensaje del servidor y datos conservados`, async ({ page }) => {
      await montar(page, {}, { 'PATCH /perfil': (r) => r.fulfill(errorApi(422, codigo, mensaje)) });
      await page.goto('/app/perfil');
      await page.locator('[name="nombre"]').fill('Otro nombre');
      await guardar(page).click();
      await expect(page.locator('[data-avisos]').getByText(mensaje)).toBeVisible();
      await expect(page.locator('[name="nombre"]')).toHaveValue('Otro nombre');
      await expect(guardar(page)).toBeEnabled();
      await sinViolaciones(page);
    });
  }

  test('401 al guardar: sesion caducada con enlace al acceso y volver', async ({ page }) => {
    await montar(page, {}, { 'PATCH /perfil': (r) => r.fulfill(errorApi(401, 'no_autenticado')) });
    await page.goto('/app/perfil');
    await guardar(page).click();
    await expect(ver(page, 'Tu sesión caducó. Inicia sesión y vuelve a guardar.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', '/acceso?volver=%2Fapp%2Fperfil');
  });

  for (const [nombre, ruta, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'autenticacion_no_disponible')), 'El servicio de acceso no responde'],
    ['red caida', (r) => r.abort('connectionrefused'), 'No hay conexión con el servidor'],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>x</h1>' }), 'Algo salió mal'],
  ]) {
    test(`guardar con ${nombre}: aviso sin Reintentar y botones disponibles`, async ({ page }) => {
      await montar(page, {}, { 'PATCH /perfil': ruta });
      await page.goto('/app/perfil');
      await guardar(page).click();
      await expect(page.locator('[data-avisos]').getByText(texto)).toBeVisible();
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
      await expect(guardar(page)).toBeEnabled();
      await expect(page.locator('[name="nombre"]')).toHaveValue('Ana Pérez');
    });
  }

  test('Guardando…: el boton se desactiva mientras tarda', async ({ page }) => {
    let soltar;
    const espera = new Promise((ok) => (soltar = ok));
    await montar(page, {}, { 'PATCH /perfil': async (r, c) => { await espera; await devolver()(r, c); } });
    await page.goto('/app/perfil');
    await guardar(page).click().catch(() => {});
    await expect(page.getByRole('button', { name: 'Guardando…' })).toBeDisabled();
    soltar();
    await expect(ver(page, 'Cambios guardados.').first()).toBeVisible();
  });
});

test.describe('verificacion del correo (punto 2)', () => {
  test('sin confirmar: aviso con accion, etiqueta SIN CONFIRMAR y axe', async ({ page }) => {
    await montar(page, { correo_confirmado: false });
    await page.goto('/app/perfil');
    await expect(ver(page, 'Confirma tu correo')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Verificar mi correo' })).toBeVisible();
    await expect(page.locator('dl')).toContainText('SIN CONFIRMAR');
    await sinViolaciones(page);
  });

  test('confirmado: no hay aviso de confirmacion', async ({ page }) => {
    await montar(page);
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await expect(ver(page, 'Confirma tu correo')).toHaveCount(0);
  });

  test('Verificar mi correo pide el enlace con signInWithOtp y redireccion a ?verificar=1', async ({ page }) => {
    await montar(page, { correo_confirmado: false });
    let redireccion = null;
    const auth = await simularAuth(page, { '/otp': (r) => { redireccion = new URL(r.request().url()).searchParams.get('redirect_to'); return r.fulfill(json(200, {})); } });
    await page.goto('/app/perfil');
    await page.getByRole('button', { name: 'Verificar mi correo' }).click();
    await expect(ver(page, 'Te enviamos otro correo a ana@correo.com. Abre el enlace para confirmarlo.')).toBeVisible();
    const otp = auth.find((l) => l.ruta === '/otp');
    expect(otp.cuerpo.email).toBe('ana@correo.com');
    expect(otp.cuerpo.create_user).toBe(false);
    expect(redireccion).toBe('http://localhost:4321/app/perfil?verificar=1');
    await sinViolaciones(page);
  });

  for (const [nombre, respuesta, texto] of [
    ['429', (r) => r.fulfill(json(429, { code: 429, error_code: 'over_email_send_rate_limit', msg: 'x' })), 'Ya te enviamos uno hace poco. Espera unos minutos antes de pedir otro.'],
    ['5xx', (r) => r.fulfill(json(500, { code: 500, error_code: 'unexpected_failure', msg: 'x' })), 'No pudimos enviar el correo. Inténtalo de nuevo en unos minutos.'],
    ['red caida', (r) => r.abort('connectionrefused'), 'No pudimos enviar el correo. Inténtalo de nuevo en unos minutos.'],
  ]) {
    test(`pedir enlace con ${nombre}: texto del caso`, async ({ page }) => {
      await montar(page, { correo_confirmado: false });
      await simularAuth(page, { '/otp': respuesta });
      await page.goto('/app/perfil');
      await page.getByRole('button', { name: 'Verificar mi correo' }).click();
      await expect(page.locator('[data-avisos], [data-salida]').getByText(texto).first()).toBeVisible();
      await expect(page.getByRole('button', { name: 'Verificar mi correo' })).toBeEnabled();
    });
  }

  test('?verificar=1: llama a verificar-correo, muestra exito, actualiza la etiqueta y quita el parametro', async ({ page }) => {
    const llamadas = await montar(page, { correo_confirmado: false }, { 'POST /perfil/verificar-correo': devolver({ correo_confirmado: true }) });
    await page.goto('/app/perfil?verificar=1');
    await expect(ver(page, 'Correo verificado.').first()).toBeVisible();
    await expect(page.locator('dl')).toContainText('CONFIRMADO');
    await expect(page.locator('dl')).not.toContainText('SIN CONFIRMAR');
    await expect(ver(page, 'Confirma tu correo')).toHaveCount(0);
    expect(llamadas.filter((l) => l.metodo === 'POST')).toHaveLength(1);
    expect(page.url()).not.toContain('verificar');
    await sinViolaciones(page);
  });

  test('?verificar=1 con 409 verificacion_no_valida: error y se conserva la accion de pedir otro enlace', async ({ page }) => {
    await montar(page, { correo_confirmado: false }, { 'POST /perfil/verificar-correo': (r) => r.fulfill(errorApi(409, 'verificacion_no_valida')) });
    await page.goto('/app/perfil?verificar=1');
    await expect(page.locator('[data-avisos]').getByText('No pudimos verificar tu correo')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Verificar mi correo' })).toBeVisible();
    expect(page.url()).not.toContain('verificar');
    await sinViolaciones(page);
  });

  test('?aviso=cuenta-creada y contrasena-cambiada muestran su aviso; una clave ajena, nada', async ({ page }) => {
    await montar(page);
    await page.goto('/app/perfil?aviso=cuenta-creada');
    await expect(ver(page, 'Cuenta creada. Ya puedes reservar.')).toBeVisible();
    expect(page.url()).not.toContain('aviso');
    await page.goto('/app/perfil?aviso=contrasena-cambiada');
    await expect(ver(page, 'Contraseña actualizada. Usa la nueva la próxima vez que inicies sesión.')).toBeVisible();
    await page.goto('/app/perfil?aviso=<b>x</b>');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await expect(page.locator('[data-avisos] .aviso')).toHaveCount(0);
  });
});

test.describe('cerrar sesion (punto 3)', () => {
  test('cliente: cerrar sesion borra la sesion y va a /acceso con aviso', async ({ page }) => {
    await montar(page);
    await simularAuth(page, { '/logout': (r) => r.fulfill({ status: 204 }) });
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await page.locator('.cabecera-menu > summary').click();
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await page.waitForURL('**/acceso?aviso=sesion-cerrada');
    expect(await page.evaluate(() => localStorage.getItem('bugalu-sesion'))).toBeNull();
  });

  test('personal: va al acceso interno', async ({ page }) => {
    await montar(page, { rol: 'personal', nombre_artistico: null });
    await simularAuth(page, { '/logout': (r) => r.fulfill({ status: 204 }) });
    await page.goto('/app/perfil');
    await expect(page.locator('[name="nombre"]')).toBeVisible();
    await page.locator('.cabecera-menu > summary').click();
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await page.waitForURL('**/acceso/interno?aviso=sesion-cerrada');
  });

  test('con la sesion cerrada, /app/perfil muestra sesion no valida', async ({ page }) => {
    await page.route(`${API}/perfil`, (r) => r.fulfill(r.request().headers().authorization ? json(200, { id: 'u1', correo: 'a@b.c', correo_confirmado: true, nombre: 'Ana', telefono: null, nombre_artistico: null, rol: 'cliente', especialidad: null }) : errorApi(401, 'no_autenticado')));
    await page.goto('/app/perfil');
    await expect(ver(page, 'Tu sesión no es válida')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ir al acceso' })).toHaveAttribute('href', '/acceso?volver=%2Fapp%2Fperfil');
  });
});

test.describe('navegacion por rol (punto 4)', () => {
  const destinosVisibles = (page) => page.locator('.lateral-destino:visible, .tactil-destino:visible').allTextContents();

  for (const { nombre, ancho, alto } of tamanos) {
    test.describe(nombre, () => {
      test.use({ viewport: { width: ancho, height: alto } });

      test('administrador ve Solicitud y Usuarios con enlaces; el resto, no', async ({ page }) => {
        await montar(page, { rol: 'administrador', nombre_artistico: null });
        await page.goto('/app/');
        const solicitudes = page.getByRole('navigation', { name: 'Principal' }).locator('a:visible', { hasText: 'Solicitud' });
        await expect(solicitudes).toHaveAttribute('href', '/app/solicitudes/');
        await expect(page.getByRole('navigation', { name: 'Principal' }).locator('a:visible', { hasText: 'Usuarios' })).toHaveAttribute('href', '/app/usuarios/');
        for (const e of await page.locator('.tactil-etiqueta, .lateral-etiqueta').allTextContents()) expect(e.trim().length, e).toBeLessThanOrEqual(9);
        await sinViolaciones(page);
        await page.screenshot({ path: `pruebas/capturas/perfil-nav-admin-${nombre}.png` });
      });

      for (const rol of ['personal', 'cliente']) {
        test(`${rol} no ve los destinos del Administrador`, async ({ page }) => {
          await montar(page, { rol, nombre_artistico: null });
          await page.goto('/app/perfil');
          await expect(page.locator('[name="nombre"]')).toBeVisible();
          const visibles = (await destinosVisibles(page)).join(' ');
          expect(visibles).toContain('Inicio');
          expect(visibles).not.toContain('Solicitud');
          expect(visibles).not.toContain('Usuarios');
        });
      }
    });
  }

  test('escritorio: variante Estudio para personal y administrador, Portal para cliente', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const [rol, seccion] of [['cliente', 'Portal'], ['personal', 'Estudio'], ['administrador', 'Estudio']]) {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await montar(page, { rol, nombre_artistico: null });
      await page.goto('/app/perfil');
      await expect(page.locator('[name="nombre"]')).toBeVisible();
      await expect(page.locator('.lateral-seccion')).toHaveText(seccion);
    }
  });

  test('sin sesion: no se piden datos y no aparecen los destinos del Administrador', async ({ page }) => {
    const llamadas = [];
    await page.route(`${API}/**`, (r) => { llamadas.push(r.request().url()); return r.fulfill(errorApi(401, 'no_autenticado')); });
    await page.goto('/app/');
    await expect(page.locator('.lateral-destino').first()).toBeAttached();
    expect(llamadas).toEqual([]);
    await expect(page.locator('a:visible', { hasText: 'Usuarios' })).toHaveCount(0);
  });
});

test.describe('capturas y sin JS (punto 5)', () => {
  for (const { nombre, ancho, alto } of tamanos) {
    test(`capturas del perfil a ${nombre} px`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: alto });
      await montar(page, { correo_confirmado: false });
      await page.goto('/app/perfil?aviso=cuenta-creada');
      await expect(ver(page, 'Confirma tu correo')).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/perfil-edicion-${nombre}.png`, fullPage: true });
      await page.locator('[name="nombre"]').fill('');
      await guardar(page).click();
      await expect(ver(page, 'Revisa 1 campo')).toBeVisible();
      await sinViolaciones(page);
      await page.screenshot({ path: `pruebas/capturas/perfil-errores-${nombre}.png`, fullPage: true });
    });
  }

  test.describe('sin JavaScript', () => {
    test.use({ javaScriptEnabled: false });
    test('avisa de que necesita JavaScript y no muestra controles que no funcionan', async ({ page }) => {
      await page.goto('/app/perfil');
      expect(await page.content()).toContain('Esta página necesita JavaScript');
      await expect(page.getByRole('button', { name: 'Cerrar sesión' })).toBeHidden();
      await expect(page.getByRole('button', { name: 'Guardar cambios' })).toHaveCount(0);
      await expect(page.locator('a:visible', { hasText: 'Usuarios' })).toHaveCount(0);
    });
  });
});
