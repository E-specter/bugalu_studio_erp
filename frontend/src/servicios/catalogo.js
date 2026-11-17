import { pedir } from './api.js';

// Contrato de RF-02 (catalogo). Montos como texto decimal ("125.50"). `id` y `fecha` se codifican aqui.
const ruta = (parte) => encodeURIComponent(parte);

export const listarServicios = () => pedir('/api/v1/servicios', { sinToken: true });
export const actualizarServicio = (id, cambios) => pedir(`/api/v1/servicios/${ruta(id)}`, { method: 'PATCH', cuerpo: cambios });

export const listarEspecialistas = () => pedir('/api/v1/especialistas', { sinToken: true });
export const actualizarEspecialista = (id, cambios) => pedir(`/api/v1/especialistas/${ruta(id)}`, { method: 'PATCH', cuerpo: cambios });

export const obtenerRecargos = () => pedir('/api/v1/recargos');
export const guardarRecargos = (recargos) => pedir('/api/v1/recargos', { method: 'PUT', cuerpo: recargos });

export const listarFeriados = (anio) => pedir(`/api/v1/feriados?anio=${ruta(anio)}`);
export const crearFeriado = (feriado) => pedir('/api/v1/feriados', { method: 'POST', cuerpo: feriado });
export const quitarFeriado = (fecha) => pedir(`/api/v1/feriados/${ruta(fecha)}`, { method: 'DELETE' });

// Publica: {id_sala, id_servicio, inicio, fin, especialistas: [id]} -> {lineas, recargos, total, anticipo}. La usa la reserva por pasos.
export const simular = (cuerpo) => pedir('/api/v1/simulaciones', { method: 'POST', cuerpo, sinToken: true });

// RF-20: impuestos (publico) y flujo con barreras de los cambios sensibles ({recurso, id_recurso?, cambios} -> vista previa con token).
export const obtenerImpuestos = () => pedir('/api/v1/impuestos', { sinToken: true });
export const previsualizarCambio = (peticion) => pedir('/api/v1/cambios-sensibles/previsualizar', { method: 'POST', cuerpo: peticion });
export const confirmarCambio = (cuerpo) => pedir('/api/v1/cambios-sensibles/confirmar', { method: 'POST', cuerpo });
// Registro de auditoria (Administrador): `filtros` {desde?, hasta?, recurso?} (solo lo que el usuario fijo) -> [CambioRegistrado], del mas reciente al mas antiguo.
export const listarCambios = (filtros = {}) => pedir(`/api/v1/registro-cambios${Object.keys(filtros).length ? `?${new URLSearchParams(filtros)}` : ''}`);
