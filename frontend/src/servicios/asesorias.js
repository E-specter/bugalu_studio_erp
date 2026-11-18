import { pedir } from './api.js';

// Contrato de RF-15 etapa A (profesionales, especialidades y horarios). Los ids vienen de la URL o de la API: se codifican aqui.
const r = (parte) => encodeURIComponent(parte);
const q = (parametros) => new URLSearchParams(parametros).toString();

// Vistas publicas (directorio, perfil): `anonimo` = sin token aunque haya sesion (la vista es la del cliente).
// `todas` y los listados del Administrador llevan token.
export const listarEspecialidades = ({ todas = false } = {}) => pedir(`/api/v1/especialidades-asesoria${todas ? '?todas=true' : ''}`, { anonimo: !todas });
export const crearEspecialidad = (nombre) => pedir('/api/v1/especialidades-asesoria', { method: 'POST', cuerpo: { nombre } });
export const actualizarEspecialidad = (id, cambios) => pedir(`/api/v1/especialidades-asesoria/${r(id)}`, { method: 'PATCH', cuerpo: cambios });

export const listarProfesionales = ({ especialidad = '', anonimo = true } = {}) => pedir(`/api/v1/profesionales${especialidad ? `?${q({ especialidad })}` : ''}`, { anonimo });
export const obtenerProfesional = (id, { anonimo = false } = {}) => pedir(`/api/v1/profesionales/${r(id)}`, { anonimo });
// Administrador (decision 8): ficha de un usuario con rol administrador.
export const crearProfesional = (idUsuario) => pedir('/api/v1/profesionales', { method: 'POST', cuerpo: { id_usuario: idUsuario } });
// {nombre_artistico?, presentacion?, redes?, especialidades?}; el Administrador suma {activo?, precios?: {"30"?, "60"?}}.
export const actualizarProfesional = (id, cambios) => pedir(`/api/v1/profesionales/${r(id)}`, { method: 'PATCH', cuerpo: cambios });
export const subirFoto = (id, archivo) => {
  const cuerpo = new FormData();
  cuerpo.append('archivo', archivo);
  return pedir(`/api/v1/profesionales/${r(id)}/foto`, { method: 'PUT', cuerpo });
};
export const quitarFoto = (id) => pedir(`/api/v1/profesionales/${r(id)}/foto`, { method: 'DELETE' });

export const obtenerSugerenciaHorarios = (id, semana) => pedir(`/api/v1/profesionales/${r(id)}/horarios/sugerencia?${q({ semana })}`);
export const publicarHorarios = (id, horarios) => pedir(`/api/v1/profesionales/${r(id)}/horarios`, { method: 'POST', cuerpo: { horarios } });
export const retirarHorario = (id, idHorario) => pedir(`/api/v1/profesionales/${r(id)}/horarios/${r(idHorario)}`, { method: 'DELETE' });
// `anonimo`: el calendario publico repite sin token si la sesion caduco.
export const obtenerDisponibilidadProfesional = ({ profesional, desde, hasta, anonimo = false }) =>
  pedir(`/api/v1/profesionales/${r(profesional)}/disponibilidad?${q({ desde, hasta })}`, { anonimo });

// --- Formatos compartidos ---
export const nombreMostrado = (p) => p.nombre_artistico || p.nombre || 'Profesional';
export const REDES = { instagram: 'Instagram', tiktok: 'TikTok', facebook: 'Facebook', youtube: 'YouTube', spotify: 'Spotify', otra: 'Otra' };
// "Precios en soles con IGV incluido (18 %)." segun `duraciones[0].igv`; sin duraciones, null.
export const notaIgv = (duraciones, porcentaje) => {
  const i = duraciones?.[0]?.igv;
  return i ? (i.incluido ? `Precios en soles con IGV incluido (${porcentaje(i.porcentaje)}).` : `Precios en soles; el IGV (${porcentaje(i.porcentaje)}) se suma al total.`) : null;
};
