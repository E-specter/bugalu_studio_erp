import { pedir } from './api.js';
import { soles, porcentaje } from './formatos.js';

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
// `excluirAsesoria` (reprogramar): la disponibilidad no cuenta esa asesoria si es del cliente.
export const obtenerDisponibilidadProfesional = ({ profesional, desde, hasta, anonimo = false, excluirAsesoria }) =>
  pedir(`/api/v1/profesionales/${r(profesional)}/disponibilidad?${q({ desde, hasta, ...(excluirAsesoria && { excluir_asesoria: excluirAsesoria }) })}`, { anonimo });

// --- Etapa B: agendar, mis asesorias, agenda y gestion. La politica de RF-18 (cancelar, reprogramar, eleccion, excepcion) usa las rutas de /reservas/{id} con el id de la asesoria (servicios/reservas.js). ---
// {id_profesional, inicio, duracion: 30|60, modalidad, version_condiciones}
export const crearAsesoria = (cuerpo) => pedir('/api/v1/asesorias', { method: 'POST', cuerpo });
export const listarMisAsesorias = () => pedir('/api/v1/asesorias/mias');
export const obtenerAsesoria = (id) => pedir(`/api/v1/asesorias/${r(id)}`);
// Profesional (solo las suyas) o Administrador. `filtros`: {estado?, desde?, hasta?, id_profesional?, por_cerrar?}; los vacios no se envian.
export const listarAsesorias = (filtros = {}) => {
  const consulta = q(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v != null)));
  return pedir(`/api/v1/asesorias${consulta ? `?${consulta}` : ''}`);
};
// {modalidad?, lugar?, enlace?}
export const actualizarEncuentro = (id, cuerpo) => pedir(`/api/v1/asesorias/${r(id)}/encuentro`, { method: 'PATCH', cuerpo });

// --- Formatos compartidos ---
export const ESTADOS_ASESORIA = { pre_reservada: ['Pendiente de pago', 'aviso'], confirmada: ['Confirmada', 'exito'], realizada: ['Realizada', 'exito'], cancelada: ['Cancelada', 'alerta'], no_asistio: ['No asistió', 'alerta'] };
export const MODALIDADES = { presencial: 'Presencial', virtual: 'Virtual (Google Meet)' };
// "30 min" · "1 h".
export const duracionTexto = (min) => (min >= 60 && min % 60 === 0 ? `${min / 60} h` : `${min} min`);
export const nombreMostrado = (p) => p.nombre_artistico || p.nombre || 'Profesional';
export const REDES = { instagram: 'Instagram', tiktok: 'TikTok', facebook: 'Facebook', youtube: 'YouTube', spotify: 'Spotify', otra: 'Otra' };
// "Precios en soles con IGV incluido (18 %)." segun `duraciones[0].igv`; sin duraciones, null.
export const notaIgv = (duraciones, porcentaje) => {
  const i = duraciones?.[0]?.igv;
  return i ? (i.incluido ? `Precios en soles con IGV incluido (${porcentaje(i.porcentaje)}).` : `Precios en soles; el IGV (${porcentaje(i.porcentaje)}) se suma al total.`) : null;
};

// Precio de una duracion para las casillas de agendar: con IGV incluido, "S/ 80,00 · Incluye IGV (18 %): S/ 12,20"; si no, "S/ 80,00 + IGV (18 %) S/ 14,40 = S/ 94,40". Solo formatea lo que manda la API.
export const textoPrecio = ({ precio, igv }) =>
  !igv ? soles(precio) : igv.incluido ? `${soles(precio)} · Incluye IGV (${porcentaje(igv.porcentaje)}): ${soles(igv.monto)}` : `${soles(igv.base)} + IGV (${porcentaje(igv.porcentaje)}) ${soles(igv.monto)} = ${soles(precio)}`;

// Partidas de una asesoria en una <Tabla variante="partidas"> de dos columnas (Concepto, Importe): una fila, y el pie con total e IGV (R2 de agendar, D2 del detalle).
export function pintarPartidasAsesoria(tabla, concepto, total, igv) {
  const celda = (texto) => Object.assign(document.createElement('td'), { textContent: texto, className: 'tabla-num' });
  const th = (texto) => Object.assign(document.createElement('th'), { scope: 'row', textContent: texto });
  const fila = (a, b, igvFila) => { const tr = document.createElement('tr'); tr.append(th(a), celda(b)); tr.classList.toggle("tabla-igv", Boolean(igvFila)); return tr; };
  const linea = igv && [`${igv.incluido ? 'Incluye IGV' : 'IGV'} (${porcentaje(igv.porcentaje)})`, soles(igv.monto), true];
  tabla.querySelector('tbody').replaceChildren(fila(concepto, soles(igv && !igv.incluido ? igv.base : total)));
  tabla.querySelector('tfoot').replaceChildren(...[...(igv && !igv.incluido ? [linea] : []), ['Total', soles(total)], ...(igv?.incluido ? [linea] : [])].map(([a, b, x]) => fila(a, b, x)));
}

// Cuota de una asesoria: la unica es "Pago unico"; la de nivel 2 al reprogramar es una penalizacion (`al_terminar`), con su porcentaje del total.
export const textoCuotaAsesoria = (c, total) =>
  c.hito === 'al_terminar' ? `Penalización por reprogramar${Number(total) > 0 ? ` · ${porcentaje(Math.round((Number(c.monto) / Number(total)) * 100))}` : ''}` : 'Pago único';
