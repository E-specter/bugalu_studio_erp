import { pedir } from './api.js';

// Contratos de RF-03 (publicos) y RF-04 (reservas). Los ids vienen de la URL o de la API: se codifican al ir en la ruta o la consulta.
const q = (parametros) => new URLSearchParams(parametros).toString();

export const listarSalas = () => pedir('/api/v1/salas');

// `desde` y `hasta`: ISO con zona. Con token de personal o administrador, `ocupados[].detalle` trae cliente, servicio y estado.
export const obtenerDisponibilidad = ({ sala, desde, hasta }) => pedir(`/api/v1/disponibilidad?${q({ sala, desde, hasta })}`);

// `reserva`: {id_sala, id_servicio, inicio, fin, especialistas: [id], detalle?}
export const crearReserva = (reserva) => pedir('/api/v1/reservas', { method: 'POST', cuerpo: reserva });

export const listarMisReservas = () => pedir('/api/v1/reservas/mias');

export const obtenerReserva = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}`);

export const cancelarReserva = (id) => pedir(`/api/v1/reservas/${encodeURIComponent(id)}/cancelar`, { method: 'POST' });

// Personal y administrador.
export const listarReservas = ({ desde, hasta }) => pedir(`/api/v1/reservas?${q({ desde, hasta })}`);
