import { pedir } from './api.js';
import { fechaDe, horaDe, diaMes } from './formatos.js';

// Contratos de RF-03 (publicos) y RF-04 (reservas). Los ids vienen de la URL o de la API: se codifican al ir en la ruta o la consulta.
const q = (parametros) => new URLSearchParams(parametros).toString();

export const listarSalas = () => pedir('/api/v1/salas', { sinToken: true });

// `desde` y `hasta`: ISO con zona. Con token de personal o administrador, `ocupados[].detalle` trae cliente, servicio y estado.
export const obtenerDisponibilidad = ({ sala, desde, hasta }) => pedir(`/api/v1/disponibilidad?${q({ sala, desde, hasta })}`, { sinToken: true });

// `reserva`: {id_sala, id_servicio, inicio, fin, especialistas: [id], detalle?}
export const crearReserva = (reserva) => pedir('/api/v1/reservas', { method: 'POST', cuerpo: reserva });

export const listarMisReservas = () => pedir('/api/v1/reservas/mias');

export const obtenerReserva = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}`);

// `nota` (RF-06): obligatoria para el Administrador si hay pagos; sin ella no se manda cuerpo.
export const cancelarReserva = (id, nota) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/cancelar`, { method: 'POST', ...(nota && { cuerpo: { nota } }) });

// Personal y administrador.
export const listarReservas = ({ desde, hasta }) => pedir(`/api/v1/reservas?${q({ desde, hasta })}`);

// --- Formatos de reserva y cuotas compartidos por mis reservas y registrar pago ---
const MINUTO = 60e3;
export const HITOS = { al_reservar: 'Al reservar', al_terminar: 'Al terminar la sesión', al_encargar: 'Al encargar', al_aprobar_version: 'Al aprobar la versión' };
// "18 nov, 14:30" (hora de Lima).
export const absoluta = (iso) => `${diaMes(fechaDe(iso))}, ${horaDe(iso)}`;
// "faltan 2 d 3 h" (>= 1 dia), "faltan 1 h 5 min", "faltan 59 min".
export const faltan = (ms) => {
  const min = Math.floor(ms / MINUTO);
  const partes = min >= 1440 ? [[Math.floor(min / 1440), 'd'], [Math.floor((min % 1440) / 60), 'h']] : min >= 60 ? [[Math.floor(min / 60), 'h'], [min % 60, 'min']] : [[min, 'min']];
  return `faltan ${partes.filter(([n]) => n).map(([n, u]) => `${n} ${u}`).join(' ')}`;
};
// "Al reservar · 50 %".
export const textoCuota = (c, total) => `${HITOS[c.hito] ?? c.hito}${Number(total) > 0 ? ` · ${Math.round((Number(c.monto) / Number(total)) * 100)} %` : ''}`;
// Ultimo pago de la cuota si fue rechazado y la cuota sigue pendiente; si no, null.
export const ultimoRechazo = (c) => {
  if (c.estado !== 'pendiente') return null;
  const ultimo = [...(c.pagos ?? [])].sort((a, b) => Date.parse(b.registrado_en) - Date.parse(a.registrado_en))[0];
  return ultimo?.estado === 'rechazado' ? ultimo : null;
};
// Lo que cuenta `tiene_pagos` (ADR-010): algun pago en validacion o aprobado.
export const tienePagos = (r) => (r.cuotas ?? []).some((c) => (c.pagos ?? []).some((p) => p.estado === 'pendiente_validacion' || p.estado === 'aprobado'));
