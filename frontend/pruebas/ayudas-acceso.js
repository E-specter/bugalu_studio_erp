// Utilidades comunes de las pruebas de RF-01 (acceso): respuestas simuladas de Supabase Auth y de la API.
import AxeBuilder from '@axe-core/playwright';
import { expect } from '@playwright/test';

export const SB = 'http://supabase.prueba/auth/v1';
export const API = 'http://api.prueba/api/v1';
export const etiquetasWcag = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

export const json = (estado, cuerpo) => ({ status: estado, contentType: 'application/json', body: JSON.stringify(cuerpo) });
export const errorApi = (estado, codigo, mensaje = 'x') => json(estado, { error: { codigo, mensaje } });
// Formato de error de Supabase Auth (GoTrue).
export const errorAuth = (estado, codigo, msg = 'x') => json(estado, { code: estado, error_code: codigo, msg });
export const usuario = { id: 'u1', aud: 'authenticated', email: 'ana@correo.com', app_metadata: {}, user_metadata: {}, created_at: '2026-01-01T00:00:00Z', identities: [{ id: 'i1' }] };
export const sesion = () => ({
  access_token: 'token-de-prueba',
  token_type: 'bearer',
  expires_in: 3600,
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  refresh_token: 'refresco',
  user: usuario,
});
export const perfil = (extra = {}) => json(200, { id: 'u1', correo: 'ana@correo.com', correo_confirmado: true, nombre: 'Ana Pérez', telefono: null, nombre_artistico: null, rol: 'cliente', especialidad: null, ...extra });
export const solicitud = (extra = {}) =>
  json(200, { id: 's1', id_usuario: 'u1', nombre: 'Ana Pérez', correo: 'ana@correo.com', especialidad: 'Ingeniería de mezcla', mensaje: 'Me invitó Luis.', estado: 'pendiente', motivo: null, creada_en: '2026-11-10T10:00:00Z', revisada_en: null, ...extra });

// Simula las rutas de Supabase Auth que se pasan; registra las llamadas en `llamadas` ({ruta, cuerpo}).
export async function simularAuth(page, rutas = {}) {
  const llamadas = [];
  await page.route(`${SB}/**`, (r) => {
    const url = new URL(r.request().url());
    const clave = Object.keys(rutas).find((k) => url.pathname.endsWith(k));
    let cuerpo = null;
    try { cuerpo = r.request().postDataJSON(); } catch {}
    llamadas.push({ ruta: url.pathname.replace('/auth/v1', ''), cuerpo });
    if (!clave) return r.fulfill(errorAuth(404, 'no_simulada'));
    const respuesta = rutas[clave];
    return typeof respuesta === 'function' ? respuesta(r, cuerpo) : r.fulfill(respuesta);
  });
  return llamadas;
}
// La API en /app/ y destinos no probados responde 401 para no generar ruido.
export const silenciarApi = (page) => page.route(`${API}/**`, (r) => r.fulfill(errorApi(401, 'no_autenticado')));

export const conSesion = (page) =>
  // Solo una vez por pestaña: el script corre en cada carga y reabriria la sesion tras cerrarla.
  page.addInitScript((s) => {
    if (sessionStorage.getItem('__sesion_puesta')) return;
    sessionStorage.setItem('__sesion_puesta', '1');
    localStorage.setItem('bugalu-sesion', JSON.stringify(s));
  }, sesion());

export async function sinViolaciones(page) {
  const { violations } = await new AxeBuilder({ page }).withTags(etiquetasWcag).analyze();
  expect(violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(' | ')}`)).toEqual([]);
}

// Errores de JS no controlados; los 4xx/5xx simulados los registra el navegador como "Failed to load resource".
export function vigilarConsola(page) {
  const consola = [];
  page.on('pageerror', (x) => consola.push(x.message));
  page.on('console', (m) => m.type() === 'error' && !m.text().includes('Failed to load resource') && consola.push(m.text()));
  return consola;
}

export const tamanos = [
  { nombre: '1440', ancho: 1440, alto: 900 },
  { nombre: '390', ancho: 390, alto: 844 },
];
