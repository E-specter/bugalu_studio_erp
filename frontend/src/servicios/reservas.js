import { pedir } from './api.js';
import { fechaDe, horaDe, diaMes } from './formatos.js';

// Contratos de RF-03 (publicos) y RF-04 (reservas). Los ids vienen de la URL o de la API: se codifican al ir en la ruta o la consulta.
const q = (parametros) => new URLSearchParams(parametros).toString();

export const listarSalas = () => pedir('/api/v1/salas', { sinToken: true });

// `desde` y `hasta`: ISO con zona. Con token de personal o administrador, `ocupados[].detalle` trae cliente, servicio y estado.
// `excluirReserva` (RF-18, reprogramar): la disponibilidad no cuenta esa reserva si es del cliente; el backend la ignora si no.
export const obtenerDisponibilidad = ({ sala, desde, hasta, excluirReserva }) => pedir(`/api/v1/disponibilidad?${q({ sala, desde, hasta, ...(excluirReserva && { excluir_reserva: excluirReserva }) })}`, { sinToken: true });

// `reserva`: {id_sala, id_servicio, inicio, fin, especialistas: [id], detalle?}
export const crearReserva = (reserva) => pedir('/api/v1/reservas', { method: 'POST', cuerpo: reserva });

export const listarMisReservas = () => pedir('/api/v1/reservas/mias');

export const obtenerReserva = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}`);

// RF-18: `cuerpo` {nivel_esperado?, nota?, por?, aviso_en?}; sin campos no se manda cuerpo (cancelar sin pagos).
export const cancelarReserva = (id, cuerpo = {}) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/cancelar`, { method: 'POST', ...(Object.keys(cuerpo).length && { cuerpo }) });
// Vista previa de la cancelacion; solo el Administrador pasa `avisoEn` (ISO con zona).
export const verCancelacion = (id, avisoEn) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/cancelacion${avisoEn ? `?${q({ aviso_en: avisoEn })}` : ''}`);
// RF-18: vista previa y reprogramacion (`inicio` ISO con zona; `nivel_esperado` null tras una cancelacion del estudio) y eleccion del cliente tras ella.
export const simularReprogramacion = (id, inicio) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/reprogramar/simular`, { method: 'POST', cuerpo: { inicio } });
export const reprogramarReserva = (id, cuerpo) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/reprogramar`, { method: 'POST', cuerpo });
export const elegirDevolucionEstudio = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/eleccion-estudio`, { method: 'POST', cuerpo: { opcion: 'devolucion' } });
// Personal y Administrador.
export const marcarInasistencia = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/inasistencia`, { method: 'POST' });
// Administrador: tratar como nivel 1.
export const aplicarExcepcion = (id, motivo) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/excepcion`, { method: 'POST', cuerpo: { motivo } });

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
