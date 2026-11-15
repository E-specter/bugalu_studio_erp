import { test, expect } from '@playwright/test';
import { SB, json, errorAuth, usuario, sesion, simularAuth, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const EXITO = 'Si hay una cuenta con ese correo, te enviamos un enlace para crear una contraseña nueva. Revisa también la carpeta de spam.';
const HASH_RECUPERACION = '#access_token=token-recuperacion&expires_in=3600&refresh_token=refresco&token_type=bearer&type=recovery';
const HASH_CADUCADO = '#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired';
const CLAVE = 'Nueva1!clave';

test.beforeEach(async ({ page }) => silenciarApi(page));

test.describe('recuperar: pedir el enlace (CA-05)', () => {
  test('estructura y redireccion a nueva-contrasena', async ({ page }) => {
    const urls = [];
    await page.route(`${SB}/recover*`, (r) => (urls.push(r.request().url()), r.fulfill(json(200, {}))));
    await page.goto('/acceso/recuperar');
    await expect(page).toHaveTitle('Recuperar contraseña · Bugalú Studio');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Recuperar contraseña');
    await expect(page.getByRole('link', { name: 'Volver a iniciar sesión' })).toHaveAttribute('href', '/acceso');
    await page.getByLabel('Correo', { exact: true }).fill('ana@correo.com');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.locator('.aviso-exito')).toContainText(EXITO);
    expect(new URL(urls[0]).searchParams.get('redirect_to')).toBe('http://localhost:4321/acceso/nueva-contrasena');
  });

  test('origen=interno: conserva el origen en la redireccion y en el enlace de vuelta', async ({ page }) => {
    const urls = [];
    await page.route(`${SB}/recover*`, (r) => (urls.push(r.request().url()), r.fulfill(json(200, {}))));
    await page.goto('/acceso/recuperar?origen=interno');
    await expect(page.getByRole('link', { name: 'Volver a iniciar sesión' })).toHaveAttribute('href', '/acceso/interno');
    await expect(page.locator('[data-marca="interno"]').first()).toBeVisible();
    await expect(page.locator('[data-marca="artistas"]').first()).toBeHidden();
    await page.getByLabel('Correo', { exact: true }).fill('ana@correo.com');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.locator('.aviso-exito')).toBeVisible();
    expect(new URL(urls[0]).searchParams.get('redirect_to')).toBe('http://localhost:4321/acceso/nueva-contrasena?origen=interno');
    await sinViolaciones(page);
  });

  test('origen desconocido se ignora', async ({ page }) => {
    await page.goto('/acceso/recuperar?origen=%3Cx%3E');
    await expect(page.getByRole('link', { name: 'Volver a iniciar sesión' })).toHaveAttribute('href', '/acceso');
  });

  for (const [n, r] of [
    ['correo inexistente (user_not_found)', errorAuth(400, 'user_not_found')],
    ['correo rechazado por el servicio', errorAuth(400, 'email_address_invalid')],
    ['validation_failed', errorAuth(422, 'validation_failed')],
  ]) {
    test(`misma respuesta que si existiera: ${n}`, async ({ page }) => {
      await simularAuth(page, { '/recover': r });
      await page.goto('/acceso/recuperar');
      await page.getByLabel('Correo', { exact: true }).fill('nadie@correo.com');
      await page.getByRole('button', { name: 'Enviar enlace' }).click();
      await expect(page.locator('.aviso-exito')).toContainText(EXITO);
      await expect(page.locator('.aviso-error')).toHaveCount(0);
    });
  }

  for (const [n, r, texto] of [
    ['429', errorAuth(429, 'over_email_send_rate_limit'), 'Demasiados intentos. Espera unos minutos y vuelve a intentarlo.'],
    ['5xx', errorAuth(500, 'unexpected_failure'), 'El servicio de acceso no responde. Inténtalo de nuevo en unos minutos.'],
    ['red caida', (r) => r.abort('connectionrefused'), 'Sin conexión. Revisa tu red y vuelve a intentarlo.'],
  ]) {
    test(`${n}: aviso de error y el correo se conserva`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await simularAuth(page, { '/recover': r });
      await page.goto('/acceso/recuperar');
      await page.getByLabel('Correo', { exact: true }).fill('ana@correo.com');
      await page.getByRole('button', { name: 'Enviar enlace' }).click();
      const aviso = page.locator('.aviso-error');
      await expect(aviso).toContainText(texto);
      await expect(aviso).toBeFocused();
      await expect(page.getByLabel('Correo', { exact: true })).toHaveValue('ana@correo.com');
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('correo vacio o con formato invalido: error del campo y sin llamar', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/recover': json(200, {}) });
    await page.goto('/acceso/recuperar');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.locator('#campo-correo-error')).toContainText('Escribe tu correo.');
    await page.getByLabel('Correo', { exact: true }).fill('ana@');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.locator('#campo-correo-error')).toContainText('Escribe un correo válido, como nombre@dominio.com.');
    expect(llamadas).toEqual([]);
  });

  test('tras enviar: foco al aviso y "Pedir otro enlace" vuelve al formulario con el correo y foco en el campo', async ({ page }) => {
    await simularAuth(page, { '/recover': json(200, {}) });
    await page.goto('/acceso/recuperar');
    await page.getByLabel('Correo', { exact: true }).fill('ana@correo.com');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.locator('.aviso-exito')).toBeFocused();
    await expect(page.locator('form')).toBeHidden();
    await sinViolaciones(page);
    await page.getByRole('button', { name: '¿No llegó? Pedir otro enlace' }).click();
    await expect(page.getByLabel('Correo', { exact: true })).toBeFocused();
    await expect(page.getByLabel('Correo', { exact: true })).toHaveValue('ana@correo.com');
  });

  test('enviando: boton en carga', async ({ page }) => {
    let soltar;
    const llega = new Promise((ok) => (soltar = ok));
    await simularAuth(page, { '/recover': async (r) => { await llega; await r.fulfill(json(200, {})); } });
    await page.goto('/acceso/recuperar');
    await page.getByLabel('Correo', { exact: true }).fill('ana@correo.com');
    await page.getByRole('button', { name: 'Enviar enlace' }).click();
    await expect(page.getByRole('button', { name: 'Enviando enlace…' })).toBeDisabled();
    soltar();
    await expect(page.locator('.aviso-exito')).toBeVisible();
  });
});

test.describe('nueva contraseña', () => {
  const usuarioRuta = { '/user': json(200, usuario) };

  test('llegada directa sin sesion de recuperacion: enlace caducado con Pedir otro enlace', async ({ page }) => {
    await page.goto('/acceso/nueva-contrasena');
    const aviso = page.locator('.aviso-error');
    await expect(aviso).toContainText('El enlace caducó o ya se usó.');
    await expect(aviso.getByRole('link', { name: 'Pedir otro enlace' })).toHaveAttribute('href', '/acceso/recuperar');
    await expect(page.locator('form')).toBeHidden();
    await expect(page.locator('[aria-busy]')).toHaveCount(0);
    await sinViolaciones(page);
  });

  test('con origen=interno, Pedir otro enlace conserva el origen', async ({ page }) => {
    await page.goto('/acceso/nueva-contrasena?origen=interno');
    await expect(page.getByRole('link', { name: 'Pedir otro enlace' })).toHaveAttribute('href', '/acceso/recuperar?origen=interno');
  });

  test('error otp_expired en el fragmento de la URL: enlace caducado', async ({ page }) => {
    await page.goto('/acceso/nueva-contrasena' + HASH_CADUCADO);
    await expect(page.locator('.aviso-error')).toContainText('El enlace caducó o ya se usó.');
  });

  test('comprobando el enlace: bloque con aria-busy', async ({ page }) => {
    let soltar;
    const llega = new Promise((ok) => (soltar = ok));
    await simularAuth(page, { '/user': async (r) => { await llega; await r.fulfill(json(200, usuario)); } });
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await expect(page.locator('[aria-busy="true"]')).toBeVisible();
    await expect(page.getByText('Comprobando el enlace…')).toBeVisible();
    await sinViolaciones(page);
    await page.screenshot({ path: 'pruebas/capturas/restablecer-comprobando-1440.png', fullPage: true });
    soltar();
    await expect(page.getByLabel('Contraseña', { exact: true })).toBeVisible();
  });

  test('enlace valido: formulario con medidor y guardado correcto va al perfil', async ({ page }) => {
    const llamadas = await simularAuth(page, usuarioRuta);
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Nueva contraseña');
    await expect(page.locator('[data-nivel]')).toBeVisible();
    await expect(page.getByLabel('Contraseña', { exact: true })).toHaveAttribute('autocomplete', 'new-password');
    await expect(page.getByRole('link', { name: 'Volver a iniciar sesión' })).toHaveAttribute('href', '/acceso');
    await sinViolaciones(page);
    await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await page.waitForURL('**/app/perfil?aviso=contrasena-cambiada');
    const put = llamadas.find((l) => l.ruta === '/user' && l.cuerpo);
    expect(put.cuerpo).toMatchObject({ password: CLAVE });
  });

  test('contrasena debil: error con lo que falta y no se llama al servicio', async ({ page }) => {
    const llamadas = await simularAuth(page, usuarioRuta);
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByLabel('Contraseña', { exact: true }).fill('abcdefgh1');
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.locator('#campo-contrasena-error')).toContainText('Falta una mayúscula y un símbolo.');
    expect(llamadas.filter((l) => l.cuerpo?.password)).toEqual([]);
  });

  test('vacia: Escribe una contraseña.', async ({ page }) => {
    await simularAuth(page, usuarioRuta);
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.locator('#campo-contrasena-error')).toContainText('Escribe una contraseña.');
    await expect(page.locator('.aviso-error')).toBeFocused();
  });

  test('same_password: error bajo el campo', async ({ page }) => {
    await simularAuth(page, { ...usuarioRuta, '/user': (r) => (r.request().method() === 'PUT' ? r.fulfill(errorAuth(422, 'same_password')) : r.fulfill(json(200, usuario))) });
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.locator('#campo-contrasena-error')).toContainText('Elige una contraseña distinta de la anterior.');
    await expect(page.getByLabel('Contraseña', { exact: true })).toBeFocused();
  });

  test('weak_password del servicio: error bajo el campo', async ({ page }) => {
    await simularAuth(page, { '/user': (r) => (r.request().method() === 'PUT' ? r.fulfill(errorAuth(422, 'weak_password')) : r.fulfill(json(200, usuario))) });
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.locator('#campo-contrasena-error')).toBeVisible();
  });

  test('sesion caducada al guardar (401): como enlace caducado', async ({ page }) => {
    await simularAuth(page, { '/user': (r) => (r.request().method() === 'PUT' ? r.fulfill(errorAuth(401, 'bad_jwt')) : r.fulfill(json(200, usuario))) });
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.locator('.aviso-error')).toContainText('El enlace caducó o ya se usó.');
  });

  for (const [n, r, texto] of [
    ['429', errorAuth(429, 'over_request_rate_limit'), 'Demasiados intentos.'],
    ['500', errorAuth(500, 'unexpected_failure'), 'El servicio de acceso no responde.'],
    ['red caida', (ruta) => ruta.abort('connectionrefused'), 'Sin conexión.'],
  ]) {
    test(`guardar con ${n}: aviso y contraseña conservada`, async ({ page }) => {
      await simularAuth(page, { '/user': (ruta) => (ruta.request().method() === 'PUT' ? (typeof r === 'function' ? r(ruta) : ruta.fulfill(r)) : ruta.fulfill(json(200, usuario))) });
      await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
      await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
      await page.getByRole('button', { name: 'Guardar contraseña' }).click();
      await expect(page.locator('.aviso-error')).toContainText(texto);
      await expect(page.getByLabel('Contraseña', { exact: true })).toHaveValue(CLAVE);
    });
  }

  test('guardando: boton en carga', async ({ page }) => {
    let soltar;
    const llega = new Promise((ok) => (soltar = ok));
    await simularAuth(page, { '/user': async (r) => { if (r.request().method() === 'PUT') await llega; await r.fulfill(json(200, usuario)); } });
    await page.goto('/acceso/nueva-contrasena' + HASH_RECUPERACION);
    await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
    await page.getByRole('button', { name: 'Guardar contraseña' }).click();
    await expect(page.getByRole('button', { name: 'Guardando contraseña…' })).toBeDisabled();
    soltar();
    await page.waitForURL('**/app/perfil?aviso=contrasena-cambiada');
  });
});

const paginas = [
  ['recuperar', '/acceso/recuperar', null],
  ['nueva-contrasena', '/acceso/nueva-contrasena' + HASH_RECUPERACION, usuarioRutaPara],
  ['nueva-contrasena-caducada', '/acceso/nueva-contrasena', null],
];
function usuarioRutaPara(page) {
  return simularAuth(page, { '/user': json(200, usuario) });
}
for (const [nombre, ruta, preparar] of paginas) {
  for (const t of tamanos) {
    test(`${nombre} a ${t.nombre}: axe, sin desbordes y captura`, async ({ page }) => {
      if (preparar) await preparar(page);
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await page.goto(ruta);
      await expect(page.locator('main [aria-busy]')).toHaveCount(0);
      await sinViolaciones(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: `pruebas/capturas/restablecer-${nombre}-${t.nombre}.png`, fullPage: true });
    });
  }
}

for (const [nombre, ruta] of [['recuperar', '/acceso/recuperar'], ['nueva-contrasena', '/acceso/nueva-contrasena']]) {
  test.describe(`${nombre} sin JavaScript`, () => {
    test.use({ javaScriptEnabled: false });
    test('explica que hace falta JS', async ({ page }) => {
      await page.goto(ruta);
      const html = await page.content();
      expect(html).toContain('Recuperar la contraseña necesita JavaScript');
      expect(html).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('form')).toBeHidden();
      await expect(page.locator('[aria-busy]')).toBeHidden();
      await page.screenshot({ path: `pruebas/capturas/restablecer-${nombre}-sin-js.png`, fullPage: true });
    });
  });
}
