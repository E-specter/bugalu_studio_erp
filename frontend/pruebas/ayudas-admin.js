// Ayudas de las pruebas de las pantallas del Administrador (franjas, tarifas): la API se simula con page.route.
import { expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi } from './ayudas-acceso.js';

// Responde `metodo` + `camino` (sin query); lo demas cae en silenciarApi (401). Devuelve las peticiones vistas.
export async function simular(page, metodo, camino, resp) {
  const vistas = [];
  await page.route((u) => u.pathname === `/api/v1${camino}`, (r) => {
    if (r.request().method() !== metodo) return r.fallback();
    let cuerpo = null;
    try { cuerpo = r.request().postDataJSON(); } catch {}
    vistas.push({ url: new URL(r.request().url()), cuerpo });
    return typeof resp === 'function' ? resp(r) : r.fulfill(resp);
  });
  return vistas;
}

// Sesion de Administrador con la API muda salvo lo que cada prueba simule.
export async function comoAdministrador(page) {
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol: 'administrador' })));
}

// Fallos de carga comunes (estados-sistema): 401, 403, 503, red caida y respuesta que no es JSON.
export const fallos = [
  { n: '401', r: (r) => r.fulfill(errorApi(401, 'no_autenticado')), texto: 'Tu sesión no es válida. Inicia sesión para continuar.', enlace: ['Ir al acceso interno', (ruta) => `/acceso/interno?volver=${encodeURIComponent(ruta)}`] },
  { n: '403', r: (r) => r.fulfill(errorApi(403, 'sin_permiso')), texto: 'Esta sección es solo para el Administrador.', extra: '[403]', enlace: ['Volver al inicio', () => '/app/'] },
  { n: '503', r: (r) => r.fulfill(errorApi(503, 'servicio_no_disponible')), texto: 'El servicio no responde. Inténtalo de nuevo en unos minutos.', reintentar: true },
  { n: 'red', r: (r) => r.abort('connectionrefused'), texto: 'Sin conexión. Revisa tu red y vuelve a intentarlo.', reintentar: true },
  { n: 'no-json', r: (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Boom</h1>' }), texto: 'Algo salió mal. Inténtalo de nuevo.', reintentar: true },
];

export { json, errorApi, expect };
