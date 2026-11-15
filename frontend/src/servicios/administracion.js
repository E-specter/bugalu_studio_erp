import { pedir } from './api.js';

// Contrato de RF-01 (Administrador): solicitudes de acceso y usuarios. `id` ya viene validado como UUID por la isla.
export const listarSolicitudes = (estado = 'pendiente') => pedir(`/api/v1/solicitudes-acceso?estado=${encodeURIComponent(estado)}`);

export const aprobarSolicitud = (id, { rol, especialidad }) =>
  pedir(`/api/v1/solicitudes-acceso/${encodeURIComponent(id)}/aprobar`, { method: 'POST', cuerpo: { rol, especialidad } });

export const rechazarSolicitud = (id, motivo) =>
  pedir(`/api/v1/solicitudes-acceso/${encodeURIComponent(id)}/rechazar`, { method: 'POST', cuerpo: { motivo } });

// `rol` vacio = todos.
export const listarUsuarios = (rol) => pedir(`/api/v1/usuarios${rol ? `?rol=${encodeURIComponent(rol)}` : ''}`);

export const cambiarUsuario = (id, { rol, especialidad }) =>
  pedir(`/api/v1/usuarios/${encodeURIComponent(id)}`, { method: 'PATCH', cuerpo: { rol, especialidad } });
