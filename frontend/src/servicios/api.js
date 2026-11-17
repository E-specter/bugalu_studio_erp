import { obtenerToken } from './sesion.js';

const base = (import.meta.env.PUBLIC_URL_API ?? '').replace(/\/$/, '');

// Formato unico de error del backend: {"error": {"codigo", "mensaje"}}. estado 0 = sin respuesta.
export class ErrorApi extends Error {
  constructor(estado, codigo, mensaje, detalles) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado;
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.detalles = detalles; // opcional: datos que la interfaz necesita (p. ej. las reservas de un 409)
  }
}

// `cuerpo` (opcional) se envia como JSON; un FormData va tal cual (multipart: el navegador pone el boundary, no se fuerza Content-Type). `sinToken`: consulta publica; si el token (caducado o ajeno) recibe 401, se repite una vez sin token.
export async function pedir(ruta, { cuerpo, headers, sinToken = false, ...opciones } = {}) {
  const token = await obtenerToken();
  let respuesta = await enviar(ruta, { cuerpo, headers, token, opciones });
  if (respuesta.status === 401 && sinToken && token) respuesta = await enviar(ruta, { cuerpo, headers, token: null, opciones });
  return leer(respuesta);
}

async function enviar(ruta, { cuerpo, headers, token, opciones }) {
  try {
    return await fetch(base + ruta, {
      ...opciones,
      headers: {
        Accept: 'application/json',
        ...(cuerpo !== undefined && !(cuerpo instanceof FormData) && { 'Content-Type': 'application/json' }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      body: cuerpo === undefined || cuerpo instanceof FormData ? cuerpo : JSON.stringify(cuerpo),
    });
  } catch {
    // Red caida, DNS o CORS rechazado: el navegador no distingue las causas.
    throw new ErrorApi(0, 'sin_conexion', 'No hay conexión con el servidor.');
  }
}

// `descargar`: archivo (p. ej. un CSV) que pide el token; devuelve el Blob. Los errores llegan como en `pedir`.
export async function descargar(ruta, tipo) {
  const respuesta = await enviar(ruta, { token: await obtenerToken(), headers: { Accept: tipo }, opciones: {} });
  return leer(respuesta, 'blob');
}

async function leer(respuesta, forma = 'json') {
  if (!respuesta.ok) {
    const { error } = await respuesta.json().catch(() => ({}));
    throw new ErrorApi(respuesta.status, error?.codigo ?? 'error_desconocido', error?.mensaje ?? 'El servidor devolvió un error.', error?.detalles);
  }
  return respuesta.status === 204 ? null : respuesta[forma]();
}

export const obtenerPerfil = () => pedir('/api/v1/perfil');
// Contrato de RF-01: PATCH /perfil {nombre?, telefono?, nombre_artistico?} y POST /perfil/verificar-correo; ambos devuelven el Perfil.
export const actualizarPerfil = (cambios) => pedir('/api/v1/perfil', { method: 'PATCH', cuerpo: cambios });
export const verificarCorreo = () => pedir('/api/v1/perfil/verificar-correo', { method: 'POST' });
