import { test, expect } from '@playwright/test';
import { API, json, errorApi, errorAuth, sesion, usuario, perfil, simularAuth, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';

const rellenarIniciar = async (page, correo = 'ana@correo.com', clave = 'Secreta1!') => {
  await page.getByLabel('Correo', { exact: true }).fill(correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(clave);
};
const rellenarRegistro = async (page, extra = {}) => {
  const d = { nombre: 'Ana Pérez', telefono: '+51 987 654 321', artistico: 'Los Sónicos', correo: 'ana@correo.com', clave: 'Secreta1!x', ...extra };
  await page.getByLabel('Nombre', { exact: true }).fill(d.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(d.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(d.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(d.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(d.clave);
};
const solicitudPendiente = { estado: 'pendiente', especialidad: 'x', mensaje: null, motivo: null, creada_en: '2026-11-10T10:00:00Z', revisada_en: null };

test.beforeEach(async ({ page }) => silenciarApi(page));

test.describe('acceso de artistas: iniciar sesion', () => {
  test('estructura, titulo, enlaces y sin Google por defecto (CA-04)', async ({ page }) => {
    await page.goto('/acceso');
    await expect(page).toHaveTitle('Iniciar sesión · Bugalú Studio');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Iniciar sesión');
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('link', { name: '¿Olvidaste tu contraseña?' })).toHaveAttribute('href', '/acceso/recuperar');
    await expect(page.getByRole('link', { name: 'Crear cuenta de artista' })).toHaveAttribute('href', '/acceso/registro');
    await expect(page.getByRole('link', { name: /Acceso interno/ })).toHaveAttribute('href', '/acceso/interno');
    await expect(page.getByRole('button', { name: 'Entrar al portal' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Google/ })).toHaveCount(0);
    await expect(page.getByLabel('Contraseña', { exact: true })).toHaveAttribute('autocomplete', 'current-password');
    await expect(page.locator('[data-nivel]')).toHaveCount(0); // sin medidor al iniciar sesion
  });

  test('conserva volver en el enlace a registro', async ({ page }) => {
    await page.goto('/acceso?volver=/app/perfil');
    await expect(page.getByRole('link', { name: 'Crear cuenta de artista' })).toHaveAttribute('href', '/acceso/registro?volver=%2Fapp%2Fperfil');
  });

  test('exito: va a /app/ y llama a Supabase con el correo y la clave', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/token': json(200, sesion()) });
    await page.goto('/acceso');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar al portal' }).click();
    await page.waitForURL('**/app/');
    expect(llamadas[0].cuerpo).toMatchObject({ email: 'ana@correo.com', password: 'Secreta1!' });
  });

  test('exito con volver propio va a esa ruta', async ({ page }) => {
    await simularAuth(page, { '/token': json(200, sesion()) });
    await page.goto('/acceso?volver=/app/perfil');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar al portal' }).click();
    await page.waitForURL('**/app/perfil');
  });

  for (const malicioso of ['//evil.com', 'https://evil.com/x', '/\\evil.com', '\\evil.com', '/a\\b', 'javascript:alert(1)', '/\t/evil.com', '/\n/evil.com', 'evil.com', '']) {
    test(`volver malicioso se ignora: ${JSON.stringify(malicioso)}`, async ({ page }) => {
      await simularAuth(page, { '/token': json(200, sesion()) });
      await page.goto('/acceso?volver=' + encodeURIComponent(malicioso));
      await rellenarIniciar(page);
      await page.getByRole('button', { name: 'Entrar al portal' }).click();
      await page.waitForURL('**/app/');
      expect(new URL(page.url()).origin).toBe('http://localhost:4321');
    });
  }

  test('invalid_credentials: aviso generico, foco al aviso, conserva el correo y vacia la contrasena (CA-03)', async ({ page }) => {
    await simularAuth(page, { '/token': errorAuth(400, 'invalid_credentials', 'Invalid login credentials') });
    await page.goto('/acceso');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar al portal' }).click();
    const aviso = page.locator('[data-avisos] .aviso-error');
    await expect(aviso).toContainText('Correo o contraseña incorrectos. Revísalos o recupera tu contraseña.');
    await expect(aviso).toBeFocused();
    await expect(page.getByLabel('Correo', { exact: true })).toHaveValue('ana@correo.com');
    await expect(page.getByLabel('Contraseña', { exact: true })).toHaveValue('');
    await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Entrar al portal' })).toBeEnabled();
    await sinViolaciones(page);
  });

  const fallas = [
    { n: 'limite', r: errorAuth(429, 'over_request_rate_limit'), texto: 'Demasiados intentos. Espera unos minutos y vuelve a intentarlo.' },
    { n: 'servicio 500', r: errorAuth(500, 'unexpected_failure'), texto: 'El servicio de acceso no responde. Inténtalo de nuevo en unos minutos.' },
    { n: 'servicio 503 sin JSON', r: { status: 503, contentType: 'text/html', body: '<h1>503</h1>' }, texto: 'El servicio de acceso no responde. Inténtalo de nuevo en unos minutos.' },
    { n: 'red caida', r: (ruta) => ruta.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.' },
    // supabase-js trata una respuesta que no es JSON como fallo de transporte (reintentable).
    { n: 'no JSON', r: { status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }, texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.' },
    { n: 'error desconocido', r: errorAuth(400, 'codigo_raro'), texto: 'Algo salió mal. Inténtalo de nuevo.' },
  ];
  for (const f of fallas) {
    test(`falla de Supabase: ${f.n}`, async ({ page }) => {
      const consola = vigilarConsola(page);
      await simularAuth(page, { '/token': f.r });
      await page.goto('/acceso');
      await rellenarIniciar(page);
      await page.getByRole('button', { name: 'Entrar al portal' }).click();
      const aviso = page.locator('[data-avisos] .aviso-error');
      await expect(aviso).toContainText(f.texto);
      await expect(aviso).toBeFocused();
      await expect(page.getByLabel('Correo', { exact: true })).toHaveValue('ana@correo.com'); // datos conservados
      await sinViolaciones(page);
      expect(consola).toEqual([]);
    });
  }

  test('campos vacios: aviso resumen con enlaces, errores bajo los campos, sin llamar a Supabase', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/token': json(200, sesion()) });
    await page.goto('/acceso');
    await page.getByRole('button', { name: 'Entrar al portal' }).click();
    const aviso = page.locator('[data-avisos] .aviso-error');
    await expect(aviso).toContainText('Revisa 2 campos');
    await expect(aviso).toBeFocused();
    await expect(aviso.getByRole('link', { name: 'Correo' })).toHaveAttribute('href', '#campo-correo');
    await expect(aviso.getByRole('link', { name: 'Contraseña' })).toBeVisible();
    await expect(page.getByText('Escribe tu correo.').first()).toBeVisible();
    await expect(page.getByText('Escribe una contraseña.').first()).toBeVisible();
    await expect(page.getByLabel('Correo', { exact: true })).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Correo', { exact: true })).toHaveAttribute('aria-describedby', /campo-correo-error/);
    expect(llamadas).toEqual([]);
    await sinViolaciones(page);
    await aviso.getByRole('link', { name: 'Correo' }).click();
    await expect(page.getByLabel('Correo', { exact: true })).toBeFocused();
  });

  test('correo invalido: se avisa al salir del campo y se corrige al escribir bien', async ({ page }) => {
    await page.goto('/acceso');
    const correo = page.getByLabel('Correo', { exact: true });
    await correo.fill('ana@');
    await page.getByLabel('Contraseña', { exact: true }).focus();
    await expect(page.getByText('Escribe un correo válido, como nombre@dominio.com.')).toBeVisible();
    await correo.fill('ana@correo.com');
    await page.getByLabel('Contraseña', { exact: true }).focus();
    await expect(page.getByText('Escribe un correo válido')).toHaveCount(0);
    await expect(correo).not.toHaveAttribute('aria-invalid', 'true');
  });

  test('enviando: boton en carga, sin doble envio', async ({ page }) => {
    let soltar;
    const llega = new Promise((ok) => (soltar = ok));
    let envios = 0;
    await simularAuth(page, { '/token': async (r) => { envios++; await llega; await r.fulfill(json(200, sesion())); } });
    await page.goto('/acceso');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar al portal' }).click();
    const boton = page.getByRole('button', { name: 'Entrando…' });
    await expect(boton).toBeDisabled();
    await expect(boton).toHaveAttribute('aria-busy', 'true');
    await sinViolaciones(page);
    soltar();
    await page.waitForURL('**/app/');
    expect(envios).toBe(1);
  });

  test('avisos por URL: solo la lista cerrada, y se quitan de la URL', async ({ page }) => {
    await page.goto('/acceso?aviso=sesion-cerrada');
    await expect(page.locator('[data-avisos]').getByText('Cerraste sesión.')).toBeVisible();
    await expect(page.locator('[data-avisos] .aviso')).toHaveAttribute('role', 'status');
    await expect(page).toHaveURL(/\/acceso$/);
    await sinViolaciones(page);
    await page.goto('/acceso?aviso=%3Cb%3Ehola%3C%2Fb%3E');
    await expect(page.locator('[data-avisos] .aviso')).toHaveCount(0);
    await page.goto('/acceso?aviso=Texto+libre+de+un+atacante');
    await expect(page.getByText('Texto libre de un atacante')).toHaveCount(0);
    await expect(page.locator('[data-avisos] .aviso')).toHaveCount(0);
  });

  test('?error=google: aviso de error', async ({ page }) => {
    await page.goto('/acceso?error=google');
    await expect(page.locator('[data-avisos] .aviso-error')).toContainText('No pudimos entrar con Google. Inténtalo de nuevo o usa tu correo.');
    await sinViolaciones(page);
  });

  test('teclado: foco en orden visual', async ({ page }) => {
    await page.goto('/acceso');
    const orden = [];
    for (let i = 0; i < 9; i++) {
      await page.keyboard.press('Tab');
      orden.push(await page.evaluate(() => (document.activeElement?.getAttribute('aria-label') ?? document.activeElement?.textContent ?? '').trim().slice(0, 30)));
    }
    const i = (t) => orden.findIndex((o) => o.includes(t));
    expect(i('Saltar')).toBe(0);
    expect(i('Mostrar')).toBeGreaterThan(-1);
    expect(i('Mostrar')).toBeLessThan(i('Olvidaste'));
    expect(i('Olvidaste')).toBeLessThan(i('Entrar al portal'));
  });
});

test.describe('acceso de artistas: registro', () => {
  test('campos, autocomplete y medidor (CA-01, CA-02)', async ({ page }) => {
    await page.goto('/acceso/registro');
    await expect(page).toHaveTitle('Registro artístico · Bugalú Studio');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Registro artístico');
    await expect(page.getByLabel('Nombre', { exact: true })).toHaveAttribute('autocomplete', 'name');
    await expect(page.getByLabel('Teléfono', { exact: true })).toHaveAttribute('type', 'tel');
    await expect(page.getByLabel('Teléfono', { exact: true })).toHaveAttribute('autocomplete', 'tel');
    await expect(page.getByLabel('Contraseña', { exact: true })).toHaveAttribute('autocomplete', 'new-password');
    await expect(page.getByRole('button', { name: 'Crear cuenta de artista' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Inicia sesión' })).toHaveAttribute('href', '/acceso');
    await expect(page.locator('[data-nivel]')).toBeVisible();
  });

  test('exito: signUp con metadatos, telefono sin espacios, y aviso cuenta-creada (CA-01)', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await page.waitForURL('**/app/perfil?aviso=cuenta-creada');
    const c = llamadas[0].cuerpo;
    expect(c.email).toBe('ana@correo.com');
    expect(c.password).toBe('Secreta1!x');
    expect(c.data).toEqual({ nombre: 'Ana Pérez', telefono: '+51987654321', nombre_artistico: 'Los Sónicos' });
  });

  test('con volver va a esa ruta con el aviso', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.goto('/acceso/registro?volver=/app/');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await page.waitForURL('**/app/?aviso=cuenta-creada');
  });

  for (const malo of ['123', '12345678', '+1234567890123456', 'abc123456', '987-654-321+', '+']) {
    test(`telefono invalido ${JSON.stringify(malo)}: error accesible y no se llama a signUp (criterio 4)`, async ({ page }) => {
      const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
      await page.goto('/acceso/registro');
      await rellenarRegistro(page, { telefono: malo });
      await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
      const campo = page.getByLabel('Teléfono', { exact: true });
      await expect(campo).toHaveAttribute('aria-invalid', 'true');
      await expect(page.locator('#campo-telefono-error')).toContainText('Escribe entre 9 y 15 dígitos; puedes empezar con +.');
      await expect(campo).toHaveAttribute('aria-describedby', /campo-telefono-error/);
      await expect(page.locator('[data-avisos] .aviso-error')).toContainText('Revisa 1 campo');
      expect(llamadas).toEqual([]);
    });
  }

  test('contrasena debil: error con lo que falta y no se llama a signUp', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page, { clave: 'abcdefgh' });
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('#campo-contrasena-error')).toContainText('Falta una mayúscula, un número y un símbolo.');
    expect(llamadas).toEqual([]);
    await sinViolaciones(page);
  });

  test('campos vacios: cinco errores', async ({ page }) => {
    await page.goto('/acceso/registro');
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('[data-avisos] .aviso-error')).toContainText('Revisa 5 campos');
    for (const t of ['Escribe tu nombre.', 'Escribe entre 9 y 15 dígitos; puedes empezar con +.', 'Escribe tu nombre artístico o el de tu proyecto.', 'Escribe tu correo.', 'Escribe una contraseña.'])
      await expect(page.locator('.mensaje-error', { hasText: t })).toBeVisible();
    await sinViolaciones(page);
  });

  test('user_already_exists: error en el correo, datos conservados', async ({ page }) => {
    await simularAuth(page, { '/signup': errorAuth(422, 'user_already_exists') });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('#campo-correo-error')).toContainText('Ya hay una cuenta con este correo. Inicia sesión o recupera tu contraseña.');
    await expect(page.getByLabel('Correo', { exact: true })).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Nombre', { exact: true })).toHaveValue('Ana Pérez');
    await expect(page.getByLabel('Correo', { exact: true })).toBeFocused();
  });

  test('correo ya registrado sin error (identities vacias): tambien se avisa', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, { ...usuario, identities: [] }) });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('#campo-correo-error')).toContainText('Ya hay una cuenta con este correo.');
  });

  test('weak_password del servicio: error en la contrasena', async ({ page }) => {
    await simularAuth(page, { '/signup': errorAuth(422, 'weak_password') });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('#campo-contrasena-error')).toBeVisible();
    await expect(page.getByLabel('Contraseña', { exact: true })).toHaveAttribute('aria-invalid', 'true');
  });

  test('cuenta creada sin sesion: aviso de informacion y formulario oculto', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, { ...usuario }) });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('[data-avisos] .aviso-informacion')).toContainText('Cuenta creada. Confirma tu correo con el enlace que te enviamos y luego inicia sesión.');
    await expect(page.locator('form')).toBeHidden();
    await sinViolaciones(page);
  });

  test('falla de red al registrar: aviso y datos conservados', async ({ page }) => {
    await simularAuth(page, { '/signup': (r) => r.abort('connectionrefused') });
    await page.goto('/acceso/registro');
    await rellenarRegistro(page);
    await page.getByRole('button', { name: 'Crear cuenta de artista' }).click();
    await expect(page.locator('[data-avisos] .aviso-error')).toContainText('Sin conexión. Revisa tu red y vuelve a intentarlo.');
    await expect(page.getByLabel('Teléfono', { exact: true })).toHaveValue('+51 987 654 321');
  });
});

test.describe('acceso interno', () => {
  test('estructura y sin Google (CA-04)', async ({ page }) => {
    await page.goto('/acceso/interno');
    await expect(page).toHaveTitle('Sala técnica · Bugalú Studio');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Sala técnica');
    await expect(page.getByRole('button', { name: 'Entrar a la sala' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Google/ })).toHaveCount(0);
    await expect(page.getByRole('link', { name: '¿Olvidaste tu contraseña?' })).toHaveAttribute('href', '/acceso/recuperar?origen=interno');
    await expect(page.getByRole('link', { name: 'Solicitar acceso' })).toHaveAttribute('href', '/acceso/interno/registro');
  });

  test('personal entra a /app/', async ({ page }) => {
    await simularAuth(page, { '/token': json(200, sesion()) });
    await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'personal' })));
    await page.goto('/acceso/interno');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar a la sala' }).click();
    await page.waitForURL('**/app/');
  });

  test('administrador con volver propio va a volver', async ({ page }) => {
    await simularAuth(page, { '/token': json(200, sesion()) });
    await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'administrador' })));
    await page.goto('/acceso/interno?volver=/app/perfil');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar a la sala' }).click();
    await page.waitForURL('**/app/perfil');
  });

  test('cliente va al estado de su solicitud (CA-07)', async ({ page }) => {
    await simularAuth(page, { '/token': json(200, sesion()) });
    await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'cliente' })));
    await page.route(`${API}/solicitudes-acceso/mia`, (r) => r.fulfill(json(200, solicitudPendiente)));
    await page.goto('/acceso/interno?volver=/app/perfil');
    await rellenarIniciar(page);
    await page.getByRole('button', { name: 'Entrar a la sala' }).click();
    await page.waitForURL('**/acceso/interno/solicitud');
  });

  const textoPerfil = 'Entraste, pero no pudimos cargar tu perfil. Inténtalo de nuevo.';
  for (const [n, ruta, texto] of [
    ['503', (r) => r.fulfill(errorApi(503, 'autenticacion_no_disponible')), textoPerfil],
    ['red caida', (r) => r.abort('connectionrefused'), textoPerfil],
    ['no JSON', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>x</h1>' }), textoPerfil],
    ['404', (r) => r.fulfill(errorApi(404, 'perfil_no_encontrado')), 'No encontramos tu perfil. Pide al estudio que lo cree.'],
  ]) {
    test(`GET /perfil ${n}: aviso y Reintentar repite solo el perfil`, async ({ page }) => {
      const llamadas = await simularAuth(page, { '/token': json(200, sesion()) });
      let perfiles = 0;
      await page.route(`${API}/perfil`, (r) => (++perfiles === 1 ? ruta(r) : r.fulfill(perfil({ rol: 'personal' }))));
      await page.goto('/acceso/interno');
      await rellenarIniciar(page);
      await page.getByRole('button', { name: 'Entrar a la sala' }).click();
      const aviso = page.locator('[data-avisos] .aviso-error');
      await expect(aviso).toContainText(texto);
      await expect(aviso).toBeFocused();
      await sinViolaciones(page);
      if (n === '404') return expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await page.waitForURL('**/app/');
      expect(llamadas.filter((l) => l.ruta === '/token')).toHaveLength(1);
      // /app/ pide el perfil una vez más para la navegación por rol.
      expect(perfiles).toBeGreaterThanOrEqual(2);
    });
  }

  test('sesion cerrada: aviso por URL', async ({ page }) => {
    await page.goto('/acceso/interno?aviso=sesion-cerrada');
    await expect(page.getByText('Cerraste sesión.')).toBeVisible();
  });
});

test.describe('solicitar acceso interno', () => {
  const rellenar = async (page) => {
    await page.getByLabel('Nombre completo', { exact: true }).fill('Luis Mora');
    await page.getByLabel('Teléfono', { exact: true }).fill('987654321');
    await page.getByLabel('Correo', { exact: true }).fill('luis@correo.com');
    await page.getByLabel('Especialidad', { exact: true }).fill('Ingeniería de mezcla');
    await page.getByLabel('Mensaje (opcional)', { exact: true }).fill('Me invitó Ana.');
    await page.getByLabel('Contraseña', { exact: true }).fill('Secreta1!x');
  };

  test('estructura', async ({ page }) => {
    await page.goto('/acceso/interno/registro');
    await expect(page).toHaveTitle('Solicitar acceso · Bugalú Studio');
    await expect(page.getByText('Creamos tu cuenta y enviamos tu solicitud al Administrador. Podrás entrar al panel cuando la apruebe.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Enviar solicitud' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Inicia sesión' })).toHaveAttribute('href', '/acceso/interno');
    await expect(page.getByRole('button', { name: /Google/ })).toHaveCount(0);
    await expect(page.locator('[data-nivel]')).toBeVisible();
  });

  test('exito: signUp con nombre y telefono, POST de la solicitud y va al estado', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
    let cuerpo, auth;
    await page.route(`${API}/solicitudes-acceso`, (r) => {
      cuerpo = r.request().postDataJSON();
      auth = r.request().headers().authorization;
      return r.fulfill(json(201, { estado: 'pendiente' }));
    });
    await page.route(`${API}/solicitudes-acceso/mia`, (r) => r.fulfill(json(200, solicitudPendiente)));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await page.waitForURL('**/acceso/interno/solicitud*');
    expect(llamadas[0].cuerpo.data).toEqual({ nombre: 'Luis Mora', telefono: '987654321' });
    expect(cuerpo).toEqual({ especialidad: 'Ingeniería de mezcla', mensaje: 'Me invitó Ana.' });
    expect(auth).toBe('Bearer token-de-prueba');
    await expect(page.getByText('Solicitud enviada. El Administrador la revisará; vuelve aquí para ver su estado.')).toBeVisible();
  });

  test('mensaje vacio no se envia', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, sesion()) });
    let cuerpo;
    await page.route(`${API}/solicitudes-acceso`, (r) => ((cuerpo = r.request().postDataJSON()), r.fulfill(json(201, { estado: 'pendiente' }))));
    await page.route(`${API}/solicitudes-acceso/mia`, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByLabel('Mensaje (opcional)', { exact: true }).fill('');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await page.waitForURL('**/acceso/interno/solicitud*');
    expect(cuerpo).toEqual({ especialidad: 'Ingeniería de mezcla' });
  });

  test('telefono invalido: no se llama a signUp', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByLabel('Teléfono', { exact: true }).fill('12ab');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(page.locator('#campo-telefono-error')).toBeVisible();
    expect(llamadas).toEqual([]);
  });

  test('user_already_exists: error en el correo con enlace a iniciar sesion', async ({ page }) => {
    await simularAuth(page, { '/signup': errorAuth(422, 'user_already_exists') });
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    const error = page.locator('#campo-correo-error');
    await expect(error).toContainText('Ya hay una cuenta con este correo. Inicia sesión aquí para enviar tu solicitud.');
    await expect(error.getByRole('link', { name: 'Inicia sesión aquí' })).toHaveAttribute('href', '/acceso/interno');
  });

  test('POST falla: aviso, datos de cuenta bloqueados y Reintentar envio repite solo el POST', async ({ page }) => {
    const llamadas = await simularAuth(page, { '/signup': json(200, sesion()) });
    let posts = 0;
    await page.route(`${API}/solicitudes-acceso`, (r) => (++posts === 1 ? r.fulfill(errorApi(503, 'autenticacion_no_disponible')) : r.fulfill(json(201, { estado: 'pendiente' }))));
    await page.route(`${API}/solicitudes-acceso/mia`, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    const aviso = page.locator('[data-avisos] .aviso-error');
    await expect(aviso).toContainText('Tu cuenta se creó, pero la solicitud no se envió.');
    await expect(aviso).toBeFocused();
    for (const e of ['Nombre completo', 'Teléfono', 'Correo', 'Contraseña']) await expect(page.getByLabel(e, { exact: true })).toHaveAttribute('readonly', '');
    await sinViolaciones(page);
    await page.getByRole('button', { name: 'Reintentar envío' }).click();
    await page.waitForURL('**/acceso/interno/solicitud*');
    expect(llamadas.filter((l) => l.ruta === '/signup')).toHaveLength(1);
    expect(posts).toBe(2);
  });

  test('409 conflicto: va al estado', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.route(`${API}/solicitudes-acceso`, (r) => r.fulfill(errorApi(409, 'conflicto')));
    await page.route(`${API}/solicitudes-acceso/mia`, (r) => r.fulfill(errorApi(404, 'no_encontrado')));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await page.waitForURL('**/acceso/interno/solicitud');
  });

  test('422: error bajo la especialidad', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, sesion()) });
    await page.route(`${API}/solicitudes-acceso`, (r) => r.fulfill(errorApi(422, 'datos_invalidos')));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(page.locator('#campo-especialidad-error')).toContainText('Escribe tu especialidad, por ejemplo Ingeniería de mezcla.');
    await expect(page.getByLabel('Especialidad', { exact: true })).toBeFocused();
  });

  test('cuenta creada sin sesion: informacion y sin POST', async ({ page }) => {
    await simularAuth(page, { '/signup': json(200, usuario) });
    let posts = 0;
    await page.route(`${API}/solicitudes-acceso`, (r) => (posts++, r.fulfill(json(201, {}))));
    await page.goto('/acceso/interno/registro');
    await rellenar(page);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(page.locator('[data-avisos] .aviso-informacion')).toContainText('Cuenta creada. Confirma tu correo');
    expect(posts).toBe(0);
  });
});

const paginas = [
  ['acceso', '/acceso'],
  ['registro', '/acceso/registro'],
  ['interno', '/acceso/interno'],
  ['interno-registro', '/acceso/interno/registro'],
];

for (const [nombre, ruta] of paginas) {
  for (const t of tamanos) {
    test(`${nombre} a ${t.nombre}: axe, sin desbordes y captura`, async ({ page }) => {
      await page.setViewportSize({ width: t.ancho, height: t.alto });
      await page.goto(ruta);
      await sinViolaciones(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if (t.ancho < 1024) await expect(page.locator('aside')).toBeHidden();
      else await expect(page.locator('aside')).toBeVisible();
      await page.screenshot({ path: `pruebas/capturas/acceso-${nombre}-${t.nombre}.png`, fullPage: true });
    });
  }

  test.describe(`${nombre} sin JavaScript`, () => {
    test.use({ javaScriptEnabled: false });
    test('explica que hace falta JS y oculta el formulario', async ({ page }) => {
      await page.goto(ruta);
      const html = await page.content();
      expect(html).toContain('El acceso necesita JavaScript');
      expect(html).toContain('Actívalo en tu navegador y recarga la página.');
      await expect(page.locator('form')).toBeHidden();
      await expect(page.locator('noscript .aviso-informacion').first()).toBeVisible();
      await page.screenshot({ path: `pruebas/capturas/acceso-${nombre}-sin-js.png`, fullPage: true });
    });
  });
}

test('zoom: con letra de 20 px nada se desborda en el formulario de registro', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/acceso/registro');
  await page.addStyleTag({ content: 'html{font-size:20px}' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
