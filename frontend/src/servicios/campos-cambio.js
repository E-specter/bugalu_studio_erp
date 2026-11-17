// Campos sensibles del contrato de RF-20 -> [etiqueta, formato]. Los comparten la revision con barreras y el registro de cambios.
// `anterior` y `nuevo` llegan como texto: aqui solo se formatean; un campo o valor desconocido se muestra tal cual.
import { soles, porcentaje } from './formatos.js';

const unidad = (singular, plural) => (v) => `${v} ${Number(v) === 1 ? singular : plural}`;
const sinFormato = (v) => v;

export const CAMPOS = {
  tarifa_hora: ['TARIFA POR HORA', soles],
  monto_fijo: ['MONTO FIJO', soles],
  monto_variable: ['MONTO VARIABLE', soles],
  unidad: ['UNIDAD', (v) => ({ hora: 'Por hora', lapso_30: 'Por media hora' })[v] ?? v],
  'noche.porcentaje': ['NOCHE (%)', porcentaje],
  'noche.desde': ['NOCHE DESDE', sinFormato],
  'noche.hasta': ['NOCHE HASTA', sinFormato],
  'fin_de_semana.porcentaje': ['FIN DE SEMANA (%)', porcentaje],
  'feriado.porcentaje': ['FERIADO (%)', porcentaje],
  porcentaje_igv: ['PORCENTAJE DE IGV', porcentaje],
  precios_incluyen_igv: ['LOS PRECIOS INCLUYEN IGV', (v) => (String(v) === 'true' ? 'Sí' : 'No')],
  dias_limite_pago: ['DÍAS ANTES DEL INICIO', unidad('día', 'días')],
  horas_limite_pago: ['HORAS DESDE LA SOLICITUD', (v) => `${v} h`],
  horas_nivel_1: ['LÍMITE DEL NIVEL 1', (v) => `${v} h`],
  horas_nivel_2: ['LÍMITE DEL NIVEL 2', (v) => `${v} h`],
  porcentaje_adelanto: ['ADELANTO PARA CONFIRMAR', porcentaje],
  porcentaje_penalizacion_nivel_2: ['PENALIZACIÓN DEL NIVEL 2', porcentaje],
  minutos_tolerancia_inasistencia: ['TOLERANCIA DE INASISTENCIA', (v) => `${v} min`],
  dias_vigencia_credito: ['VIGENCIA DEL CRÉDITO', unidad('día', 'días')],
  reprogramaciones_nivel_1: ['REPROGRAMACIONES DEL NIVEL 1', sinFormato],
  reprogramaciones_nivel_2: ['REPROGRAMACIONES DEL NIVEL 2', sinFormato],
};

// [etiqueta, valor formateado] de un cambio {campo, anterior, nuevo}.
export function formatearCambio({ campo, anterior, nuevo }) {
  const [etiqueta, dar] = CAMPOS[campo] ?? [campo.toUpperCase(), sinFormato];
  return { etiqueta, anterior: dar(anterior), nuevo: dar(nuevo) };
}
