import { pedir } from './api.js';
import { fechaDe, horaDe, diaMes, diaMesAnio, soles } from './formatos.js';

// Contrato de RF-18 (creditos y devoluciones). Los ids vienen de la URL o de la API: se codifican al ir en la ruta.
const id = encodeURIComponent;

// Cliente (los suyos); el Administrador pasa `idCliente`.
export const listarCreditos = (idCliente) => pedir(`/api/v1/creditos${idCliente ? `?${new URLSearchParams({ id_cliente: idCliente })}` : ''}`);
// Cliente. `cuerpo`: {monto, id_credito?}; devuelve la Reserva.
export const usarCredito = (idCuota, cuerpo) => pedir(`/api/v1/cuotas/${id(idCuota)}/credito`, { method: 'POST', cuerpo });
export const pedirDevolucion = (idCredito, motivo) => pedir(`/api/v1/creditos/${id(idCredito)}/devolucion`, { method: 'POST', cuerpo: { motivo } });
// Administrador.
export const listarDevoluciones = (estado) => pedir(`/api/v1/devoluciones${estado ? `?${new URLSearchParams({ estado })}` : ''}`);
export const obtenerDevolucion = (idDevolucion) => pedir(`/api/v1/devoluciones/${id(idDevolucion)}`);
// `cuerpo`: {decision: 'total'|'parcial'|'rechazo', monto?, motivo?}
export const decidirDevolucion = (idDevolucion, cuerpo) => pedir(`/api/v1/devoluciones/${id(idDevolucion)}/decidir`, { method: 'POST', cuerpo });
export const marcarRealizada = (idDevolucion, nota) => pedir(`/api/v1/devoluciones/${id(idDevolucion)}/realizada`, { method: 'POST', cuerpo: { nota } });

export const TIPOS_CREDITO = { nivel_1: 'Cancelación (nivel 1)', nivel_2: 'Cancelación (nivel 2)', reprogramacion: 'Diferencia al reprogramar', excepcion: 'Caso excepcional' };
const DIA = 864e5;
const centimos = (monto) => Math.round(Number(monto) * 100);

// Lo que se puede usar al pagar: saldo de los vigentes sin devolucion pendiente. Suma en centimos, solo para mostrar (la API valida al aplicar).
export const disponible = (creditos) => {
  const total = creditos.filter((c) => c.estado === 'vigente' && c.devolucion?.estado !== 'pendiente').reduce((suma, c) => suma + centimos(c.saldo), 0);
  return (total / 100).toFixed(2);
};

// Vence en 7 dias o menos (y sigue vigente): VENCE PRONTO.
export const vencePronto = (c) => c.estado === 'vigente' && Date.parse(c.vence) - Date.now() <= 7 * DIA;

// Texto de la devolucion de un credito, en una frase (spec RF-18-creditos, Estados). null sin devolucion.
export function textoDevolucion(d) {
  if (!d) return null;
  const dia = (iso) => diaMes(fechaDe(iso));
  if (d.estado === 'pendiente') return `Devolución pedida el ${dia(d.solicitada_en)}. Mientras la revisamos, este crédito no se usa ni vence.`;
  if (d.estado === 'aprobada') return `Devolución aprobada: ${soles(d.monto_aprobado)}. Te la enviamos fuera de la app.${Number(d.monto_aprobado) < Number(d.monto_solicitado) ? ' El resto sigue como crédito.' : ''}`;
  if (d.estado === 'rechazada') return `Devolución rechazada: «${d.motivo_decision}».`;
  if (d.estado === 'realizada') return `Devolución hecha el ${dia(d.realizada_en)}: ${d.nota_realizada}`;
  return null;
}

// Fecha de vencimiento "17 dic 2026" y fecha con hora "18 nov, 14:30" (Lima).
export const fechaVence = (iso) => diaMesAnio(fechaDe(iso));
export const fechaHora = (iso) => `${diaMes(fechaDe(iso))}, ${horaDe(iso)}`;
