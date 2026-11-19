import { pedir } from './api.js';

// Contrato de RF-03 (Administrador): franjas, cierres y parametros. Fechas ISO con zona; la semana es AAAA-Www.
const ruta = (parte) => encodeURIComponent(parte);
const consulta = (datos) => new URLSearchParams(datos).toString();

export const obtenerSugerencia = (sala, semana) => pedir(`/api/v1/franjas/sugerencia?${consulta({ sala, semana })}`);
export const publicarFranjas = (id_sala, franjas) => pedir('/api/v1/franjas', { method: 'POST', cuerpo: { id_sala, franjas } });
export const retirarFranja = (id) => pedir(`/api/v1/franjas/${ruta(id)}`, { method: 'DELETE' });
export const registrarCierre = (cierre) => pedir('/api/v1/cierres', { method: 'POST', cuerpo: cierre });
export const quitarCierre = (id) => pedir(`/api/v1/cierres/${ruta(id)}`, { method: 'DELETE' });
export const obtenerParametros = () => pedir('/api/v1/parametros');
export const guardarParametros = (parametros) => pedir('/api/v1/parametros', { method: 'PATCH', cuerpo: parametros });
// RF-20 CA-12: tarifa por hora de gestion (texto decimal) y tope de horas de sala; publico, lo lee el pie de las condiciones.
export const obtenerParametrosDanos = () => pedir('/api/v1/parametros/danos', { sinToken: true });
