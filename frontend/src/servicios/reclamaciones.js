import { pedir, descargar } from './api.js';
import { obtenerToken } from './sesion.js';

// Contrato de RF-16. Los ids vienen de la URL o de la API: se codifican al ir en la ruta.
const id = encodeURIComponent;
const consulta = (filtros) => {
  const texto = new URLSearchParams(Object.entries(filtros).filter(([, v]) => v)).toString();
  return texto ? `?${texto}` : '';
};

// Publico (con sesion opcional). `datos`: FormData con `datos` (JSON de NuevaHoja) y `adjuntos`. Un 401 por un token vencido se repite una vez sin token
// (precision 3: este endpoint no responde 401). Devuelve {hoja, conCuenta, sesionVencida}: `conCuenta` es si la peticion que respondio llevaba token,
// es decir, si la hoja quedo vinculada a la cuenta.
export async function registrarHoja(datos) {
  const ruta = '/api/v1/reclamaciones';
  const token = await obtenerToken();
  try {
    return { hoja: await pedir(ruta, { method: 'POST', cuerpo: datos }), conCuenta: Boolean(token), sesionVencida: false };
  } catch (error) {
    if (error.estado !== 401 || !token) throw error;
    return { hoja: await pedir(ruta, { method: 'POST', cuerpo: datos, anonimo: true }), conCuenta: false, sesionVencida: true };
  }
}
export const listarMias = () => pedir('/api/v1/reclamaciones/mias');
// Dueño o Administrador.
export const obtenerHoja = (idHoja) => pedir(`/api/v1/reclamaciones/${id(idHoja)}`);

// Administrador.
export const listarHojas = (filtros = {}) => pedir(`/api/v1/reclamaciones${consulta(filtros)}`);
export const responderHoja = (idHoja, cuerpo) => pedir(`/api/v1/reclamaciones/${id(idHoja)}/respuesta`, { method: 'POST', cuerpo });
export const transcribirHoja = (datos) => pedir('/api/v1/reclamaciones/transcripcion', { method: 'POST', cuerpo: datos });
export const obtenerAdjunto = (idHoja, n) => pedir(`/api/v1/reclamaciones/${id(idHoja)}/adjuntos/${Number(n)}`);
export const exportarHojas = (desde, hasta) => descargar(`/api/v1/reclamaciones/exportar${consulta({ desde, hasta })}`, 'text/csv');
