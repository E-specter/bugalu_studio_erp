// RF-01 de punta a punta contra el Supabase local, el backend y Mailpit reales: sin page.route.
// Se ejecuta con `npm run test:e2e:real` (no con `npm run test:e2e`). Necesita el stack de montaje-local.md.
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '@playwright/test';

const SUPABASE = 'http://127.0.0.1:45621';
const MAILPIT = process.env.URL_MAILPIT ?? 'http://127.0.0.1:45624';
const BACKEND = resolve(import.meta.dirname, '../../../backend');
const LIMPIAR = resolve(import.meta.dirname, 'limpiar.py');
const CAPTURAS = 'pruebas/capturas/real-rf01';

const marca = Date.now().toString(36);
const CLAVE = 'Clave-Segura-123!';
const cliente = { nombre: 'Cora Real', telefono: '+51 987 654 321', artistico: 'Los Reales', correo: `rf01-${marca}-cliente@prueba.bugalu.pe` };
const interno = { nombre: 'Ines Interna', telefono: '987654322', especialidad: 'Ingeniería de mezcla', correo: `rf01-${marca}-interno@prueba.bugalu.pe` };
const admin = { nombre: 'Aldo Admin', telefono: '987654323', artistico: 'Aldo', correo: `rf01-${marca}-admin@prueba.bugalu.pe` };
const correos = [cliente.correo, interno.correo, admin.correo];

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ browser }) => {
  try {
    const [auth, mail] = await Promise.all([fetch(`${SUPABASE}/auth/v1/health`), fetch(`${MAILPIT}/api/v1/info`)]);
    if (!auth.ok || !mail.ok) throw new Error(`Auth ${auth.status}, Mailpit ${mail.status}`);
  } catch (error) {
    const motivo = `Falta el stack local (npx supabase start; Supabase ${SUPABASE}, Mailpit ${MAILPIT}): ${error.message}`;
    if (process.env.EXIGIR_INTEGRACION) throw new Error(motivo);
    test.skip(true, motivo);
  }
  // Calienta astro dev: la primera carga optimiza dependencias y recarga la página en pleno envío de un formulario.
  const p = await browser.newPage();
  for (const ruta of ['/acceso/registro', '/acceso/interno/registro', '/acceso/interno', '/app/perfil', '/app/solicitudes/']) {
    await p.goto(ruta);
    await p.waitForLoadState('networkidle');
  }
  await p.close();
});

test.afterAll(() => {
  // Siempre: aunque falle un paso, no quedan usuarios ni huérfanos.
  console.log(execFileSync('uv', ['run', 'python', LIMPIAR, ...correos], { cwd: BACKEND, encoding: 'utf8' }).trim());
});

const entrar = async (page, ruta, persona, boton) => {
  await page.goto(ruta);
  await page.getByLabel('Correo', { exact: true }).fill(persona.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByRole('button', { name: boton }).click();
};
const registrarArtista = async (page, p) => {
  await page.goto('/acceso/registro');
  await page.getByLabel('Nombre', { exact: true }).fill(p.nombre);
  await page.getByLabel('Teléfono', { exact: true }).fill(p.telefono);
  await page.getByLabel('Nombre artístico o proyecto', { exact: true }).fill(p.artistico);
  await page.getByLabel('Correo', { exact: true }).fill(p.correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  return page;
};
const nuevaPagina = async (browser) => (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const captura = (page, nombre) => page.screenshot({ path: `${CAPTURAS}-${nombre}.png` });
const nav = (page) => page.getByRole('navigation', { name: 'Principal' }).locator('a:visible');

async function enlaceDelCorreo(correo) {
  for (let i = 0; i < 100; i++) {
    const { messages } = await (await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${correo}`)}`)).json();
    if (messages.length) {
      const m = await (await fetch(`${MAILPIT}/api/v1/message/${messages[0].ID}`)).json();
      const enlace = (m.HTML + m.Text).match(/https?:\/\/[^\s"<>]+\/verify\?[^\s"<>]+/);
      if (enlace) return enlace[0].replaceAll('&amp;', '&');
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`No llegó el correo a ${correo}`);
}

let artista, interna; // páginas que sobreviven entre pasos

test('a. registro de cliente: entra y el perfil muestra sus datos sin verificar', async ({ browser }) => {
  artista = await registrarArtista(await nuevaPagina(browser), cliente);
  await expect(artista.getByText('Robustez: fuerte')).toBeVisible();
  await artista.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await artista.waitForURL('**/app/perfil?aviso=cuenta-creada');
  await expect(artista.locator('[name="nombre"]')).toHaveValue(cliente.nombre);
  await expect(artista.locator('dl')).toContainText(cliente.correo);
  await expect(artista.locator('dl')).toContainText('SIN VERIFICAR');
  await captura(artista, 'a-perfil-sin-verificar');
});

test('b. verificar el correo con el enlace de Mailpit', async () => {
  await artista.getByRole('button', { name: 'Verificar mi correo' }).click();
  const enlace = await enlaceDelCorreo(cliente.correo);
  await artista.goto(enlace);
  await expect(artista.locator('dl')).toContainText('VERIFICADO');
  await expect(artista.locator('dl')).not.toContainText('SIN VERIFICAR');
  await captura(artista, 'b-perfil-verificado');
});

test('c. editar teléfono y nombre artístico persiste al recargar', async () => {
  await artista.goto('/app/perfil');
  await artista.locator('[name="telefono"]').fill('+51 911 222 333');
  await artista.locator('[name="nombre_artistico"]').fill('Los Reales Reloaded');
  await artista.getByRole('button', { name: 'Guardar cambios' }).click();
  await expect(artista.getByText('Cambios guardados.').first()).toBeVisible();
  await artista.reload();
  await expect(artista.locator('[name="telefono"]')).toHaveValue('+51911222333');
  await expect(artista.locator('[name="nombre_artistico"]')).toHaveValue('Los Reales Reloaded');
  await captura(artista, 'c-perfil-editado');
});

test('d. solicitud interna: queda pendiente y no entra al panel del estudio', async ({ browser }) => {
  interna = await nuevaPagina(browser);
  await interna.goto('/acceso/interno/registro');
  await interna.getByLabel('Nombre completo', { exact: true }).fill(interno.nombre);
  await interna.getByLabel('Teléfono', { exact: true }).fill(interno.telefono);
  await interna.getByLabel('Correo', { exact: true }).fill(interno.correo);
  await interna.getByLabel('Especialidad', { exact: true }).fill(interno.especialidad);
  await interna.getByLabel('Mensaje (opcional)', { exact: true }).fill('Prueba real de RF-01.');
  await interna.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await interna.getByRole('button', { name: 'Enviar solicitud' }).click();
  await interna.waitForURL('**/acceso/interno/solicitud*');
  await expect(interna.getByRole('heading', { level: 1 })).toHaveText('Tu solicitud');
  await expect(interna.getByText(/pendiente/i).first()).toBeVisible();
  await captura(interna, 'd-solicitud-pendiente');
  // Sin rol de estudio, la bandeja del Administrador le responde 403 y no ve destinos de administración.
  await interna.goto('/app/solicitudes/');
  await expect(interna.getByRole('table')).toHaveCount(0);
  await expect(nav(interna).filter({ hasText: 'Usuarios' })).toHaveCount(0);
  await captura(interna, 'd-sin-acceso-al-panel');
});

test('e. el Administrador aprueba la solicitud como personal con especialidad', async ({ browser }) => {
  const p = await registrarArtista(await nuevaPagina(browser), admin);
  await p.getByRole('button', { name: 'Crear cuenta de artista' }).click();
  await p.waitForURL('**/app/perfil?aviso=cuenta-creada');
  execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.crear_administrador', admin.correo], { cwd: BACKEND });
  await p.evaluate(() => localStorage.clear());
  await entrar(p, '/acceso/interno', admin, 'Entrar a la sala');
  await p.waitForURL('**/app/');
  await expect(nav(p).filter({ hasText: 'Accesos' })).toBeVisible();
  await expect(nav(p).filter({ hasText: 'Usuarios' })).toBeVisible();
  await captura(p, 'e-panel-administrador');
  await p.goto('/app/solicitudes/');
  await p.getByRole('link', { name: `Revisar solicitud de ${interno.nombre}` }).click();
  await p.getByRole('radio', { name: /Personal del estudio/ }).check();
  await p.getByLabel('Especialidad').fill(interno.especialidad);
  await captura(p, 'e-revisar-solicitud');
  await p.getByRole('button', { name: 'Aprobar acceso' }).click();
  await expect(p.getByRole('main')).toContainText(/aprobada|aprobado|aprobaste/i);
  await captura(p, 'e-solicitud-aprobada');
});

test('f. la persona aprobada entra y ve Estudio sin destinos del Administrador', async () => {
  await interna.evaluate(() => localStorage.clear());
  await entrar(interna, '/acceso/interno', interno, 'Entrar a la sala');
  await interna.waitForURL('**/app/');
  await expect(interna.locator('[data-seccion]:visible').first()).toHaveText('Estudio');
  await expect(nav(interna).filter({ hasText: 'Inicio' })).toBeVisible();
  await expect(nav(interna).filter({ hasText: 'Usuarios' })).toHaveCount(0);
  await expect(nav(interna).filter({ hasText: 'Accesos' })).toHaveCount(0);
  await captura(interna, 'f-estudio-personal');
});

test('g. cerrar sesión vuelve al acceso y el perfil queda sin sesión', async () => {
  await interna.getByText('Menú', { exact: true }).click();
  await interna.getByRole('button', { name: 'Cerrar sesión' }).click();
  await interna.waitForURL('**/acceso**');
  await interna.goto('/app/perfil');
  await expect(interna.getByText('Tu sesión no es válida').first()).toBeVisible();
  await captura(interna, 'g-sesion-no-valida');
});
