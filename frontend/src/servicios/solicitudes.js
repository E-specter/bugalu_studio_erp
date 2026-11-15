import { pedir } from './api.js';

// Contrato de RF-01: POST /solicitudes-acceso {especialidad, mensaje?} y GET /solicitudes-acceso/mia.
export const enviarSolicitud = ({ especialidad, mensaje }) =>
  pedir('/api/v1/solicitudes-acceso', { method: 'POST', cuerpo: { especialidad, ...(mensaje && { mensaje }) } });

export const obtenerMiSolicitud = () => pedir('/api/v1/solicitudes-acceso/mia');
