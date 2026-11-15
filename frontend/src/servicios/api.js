import { obtenerToken } from './sesion.js';

const base = (import.meta.env.PUBLIC_URL_API ?? '').replace(/\/$/, '');

// Formato unico de error del backend: {"error": {"codigo", "mensaje"}}. estado 0 = sin respuesta.
export class ErrorApi extends Error {
  constructor(estado, codigo, mensaje) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado;
    this.codigo = codigo;
    this.mensaje = mensaje;
  }
}

// `cuerpo` (opcional) se envia como JSON.
export async function pedir(ruta, { cuerpo, headers, ...opciones } = {}) {
  const token = await obtenerToken();
  let respuesta;
  try {
    respuesta = await fetch(base + ruta, {
      ...opciones,
      headers: {
        Accept: 'application/json',
        ...(cuerpo !== undefined && { 'Content-Type': 'application/json' }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch {
    // Red caida, DNS o CORS rechazado: el navegador no distingue las causas.
    throw new ErrorApi(0, 'sin_conexion', 'No hay conexión con el servidor.');
  }
  if (!respuesta.ok) {
    const { error } = await respuesta.json().catch(() => ({}));
    throw new ErrorApi(respuesta.status, error?.codigo ?? 'error_desconocido', error?.mensaje ?? 'El servidor devolvió un error.');
  }
  return respuesta.status === 204 ? null : respuesta.json();
}

export const obtenerPerfil = () => pedir('/api/v1/perfil');
// Contrato de RF-01: PATCH /perfil {nombre?, telefono?, nombre_artistico?} y POST /perfil/verificar-correo; ambos devuelven el Perfil.
export const actualizarPerfil = (cambios) => pedir('/api/v1/perfil', { method: 'PATCH', cuerpo: cambios });
export const verificarCorreo = () => pedir('/api/v1/perfil/verificar-correo', { method: 'POST' });
