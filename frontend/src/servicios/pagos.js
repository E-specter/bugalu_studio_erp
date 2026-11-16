import { pedir } from './api.js';

// Contrato de RF-05. Los ids vienen de la URL o de la API: se codifican al ir en la ruta.
const id = encodeURIComponent;

// Cliente. `datos`: FormData multipart con id_cuota, metodo, monto, numero_operacion y captura.
export const registrarPago = (datos) => pedir('/api/v1/pagos', { method: 'POST', cuerpo: datos });
export const obtenerInstrucciones = () => pedir('/api/v1/instrucciones-pago');
export const obtenerContacto = () => pedir('/api/v1/contacto-estudio');

// Administrador.
export const guardarInstrucciones = (instrucciones) => pedir('/api/v1/instrucciones-pago', { method: 'PUT', cuerpo: instrucciones });
export const guardarContacto = (texto) => pedir('/api/v1/contacto-estudio', { method: 'PUT', cuerpo: { texto } });
export const listarPagos = (estado) => pedir(`/api/v1/pagos${estado ? `?${new URLSearchParams({ estado })}` : ''}`);
// Dueño o Administrador.
export const obtenerPago = (idPago) => pedir(`/api/v1/pagos/${id(idPago)}`);
export const obtenerCaptura = (idPago) => pedir(`/api/v1/pagos/${id(idPago)}/captura`);
export const aprobarPago = (idPago) => pedir(`/api/v1/pagos/${id(idPago)}/aprobar`, { method: 'POST' });
export const rechazarPago = (idPago, motivo) => pedir(`/api/v1/pagos/${id(idPago)}/rechazar`, { method: 'POST', cuerpo: { motivo } });
