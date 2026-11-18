import { pedir } from './api.js';

// Contrato de RF-01 (Administrador): solicitudes de acceso y usuarios. `id` ya viene validado como UUID por la isla.
export const listarSolicitudes = (estado = 'pendiente') => pedir(`/api/v1/solicitudes-acceso?estado=${encodeURIComponent(estado)}`);

export const aprobarSolicitud = (id, { rol, especialidad }) =>
  pedir(`/api/v1/solicitudes-acceso/${encodeURIComponent(id)}/aprobar`, { method: 'POST', cuerpo: { rol, especialidad } });

export const rechazarSolicitud = (id, motivo) =>
  pedir(`/api/v1/solicitudes-acceso/${encodeURIComponent(id)}/rechazar`, { method: 'POST', cuerpo: { motivo } });

// `rol` vacio = todos; `documentoRepetido` (RF-17, decision 4) deja solo las cuentas que comparten documento.
export const listarUsuarios = (rol, documentoRepetido = false) => {
  const consulta = new URLSearchParams({ ...(rol && { rol }), ...(documentoRepetido && { documento_repetido: 'true' }) }).toString();
  return pedir(`/api/v1/usuarios${consulta ? `?${consulta}` : ''}`);
};

/**
 * Profesional artistico: solo `rol` (sus especialidades van en su ficha).
 * @param {string} id
 * @param {{rol: string, especialidad?: string | null}} cambios
 */
export const cambiarUsuario = (id, { rol, especialidad }) =>
  pedir(`/api/v1/usuarios/${encodeURIComponent(id)}`, { method: 'PATCH', cuerpo: { rol, especialidad } });
