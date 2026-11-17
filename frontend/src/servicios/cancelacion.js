// Textos de la politica de cancelacion por niveles (spec RF-18-cancelar, Copy). Los plazos salen de `Reserva.politica`; sin ellos el texto va sin cifra.
import { soles, porcentaje, diaMesAnio, fechaDe } from './formatos.js';

export const nivelTexto = (nivel, p) => {
  if (nivel === 1) return p?.horas_nivel_1 ? `Nivel 1: avisas con más de ${p.horas_nivel_1} h.` : 'Nivel 1: avisas con tiempo.';
  if (nivel === 2) return p?.horas_nivel_2 ? `Nivel 2: avisas entre ${p.horas_nivel_2} y ${p.horas_nivel_1} h antes.` : 'Nivel 2: avisas con poco tiempo.';
  if (nivel === 3) return p?.horas_nivel_2 ? `Nivel 3: avisas con ${p.horas_nivel_2} h o menos.` : 'Nivel 3: avisas a última hora.';
  return 'Sin pagos: cancelas gratis.';
};

const FIN = 'El horario se libera al momento y la cancelación no se puede deshacer.';
export const consecuenciaCancelar = (nivel, p) =>
  nivel === 1 ? `Todo lo que pagaste pasa a crédito para otra reserva tuya. Si prefieres el dinero, puedes pedir la devolución desde Mis créditos. ${FIN}`
  : nivel === 2 ? `Se retiene una penalización${p?.porcentaje_penalizacion_nivel_2 ? ` del ${porcentaje(p.porcentaje_penalizacion_nivel_2)} del total` : ''}. El resto pasa a crédito para otra reserva tuya, sin devolución. ${FIN}`
  : nivel === 3 ? `Se retiene todo lo que pagaste y no hay crédito. ${FIN}`
  : 'El horario se libera al momento y no se te cobra nada. No se puede deshacer: si quieres ese horario otra vez, tendrás que reservarlo de nuevo si sigue libre.';

export const avisoValidacion = (nivel, enValidacion) =>
  Number(enValidacion) > 0 && nivel
    ? `Tienes ${soles(enValidacion)} en validación. Si el estudio lo aprueba, ${nivel === 3 ? 'también se retendrá' : 'se sumará a tu crédito'}.`
    : null;

// Filas del <dl> de la vista previa: [etiqueta, valor]. En validacion solo si > 0; el vencimiento solo con credito.
export const filasVista = (v) => [
  ['Pagado', soles(v.pagado)],
  ...(Number(v.en_validacion) > 0 ? [['En validación', soles(v.en_validacion)]] : []),
  ['Se retiene', soles(v.retenido)],
  ['Pasa a crédito', soles(v.credito)],
  ...(Number(v.credito) > 0 && v.credito_vence ? [['El crédito vence', diaMesAnio(fechaDe(v.credito_vence))]] : []),
];

// "Faltan 1 d 6 h para tu sesión." desde las horas de anticipacion de la API (`de`: "tu" o "la").
export function anticipacionTexto(horas, de = 'tu') {
  const min = Math.floor(Number(horas) * 60);
  const partes = min >= 1440 ? [[Math.floor(min / 1440), 'd'], [Math.floor((min % 1440) / 60), 'h']] : min >= 60 ? [[Math.floor(min / 60), 'h'], [min % 60, 'min']] : [[min, 'min']];
  const t = partes.filter(([n]) => n).map(([n, u]) => `${n} ${u}`).join(' ');
  return `${t ? `Faltan ${t}` : 'Falta menos de 1 min'} para ${de} sesión.`;
}

// RF-18, lateral del detalle: lo que se dice de "Reprogramar". `v` (VistaCancelacion) es null si la vista previa fallo: se ofrece y decide la API.
export function entradaReprogramar(v, p) {
  if (!v) return { puede: true, ayuda: '' };
  if (v.puede_reprogramar) {
    const n = Number(v.reprogramaciones_restantes);
    const cambios = n === 1 ? 'Te queda 1 cambio de horario.' : `Te quedan ${n} cambios de horario.`;
    const aviso = v.nivel === 2 ? ` Faltan ${p?.horas_nivel_1 ?? 'pocas'} h o menos: reprogramar tiene una penalización${p?.porcentaje_penalizacion_nivel_2 ? ` del ${porcentaje(p.porcentaje_penalizacion_nivel_2)}` : ''}.` : '';
    return { puede: true, ayuda: cambios + aviso };
  }
  if (v.nivel === 3) return { puede: false, ayuda: p?.horas_nivel_2 ? `Ya no puedes reprogramarla: faltan ${p.horas_nivel_2} h o menos para el inicio.` : 'Ya no puedes reprogramarla: falta muy poco para el inicio.' };
  if (Number(v.reprogramaciones_restantes) === 0) return { puede: false, ayuda: 'Ya no puedes reprogramarla: usaste los cambios de horario que permite una reserva.' };
  if (v.nivel === 2) return { puede: false, ayuda: 'Ya la reprogramaste una vez con poco tiempo de aviso, que es el máximo en el nivel 2.' };
  return { puede: false, ayuda: 'Ya no puedes reprogramarla.' };
}

// Pantalla de reprogramar: el nivel en palabras y lo que dice un 409 que la deja sin calendario.
export const nivelReprogramacion = (nivel) => (nivel === 1 ? 'Nivel 1 · sin cargo' : nivel === 2 ? 'Nivel 2 · con penalización' : 'Sin costo: el estudio canceló tu sesión');
export const sinReprogramar = (codigo, p) =>
  codigo === 'limite_reprogramaciones'
    ? 'Ya no puedes reprogramar esta reserva: usaste los cambios de horario que permite una reserva.'
    : `Ya no puedes reprogramar esta reserva: ${p?.horas_nivel_2 ? `faltan ${p.horas_nivel_2} h o menos para el inicio` : 'falta muy poco para el inicio'}.`;
export const FRANJA = {
  fuera_de_franja: 'Ese horario ya no está publicado.',
  anticipacion_insuficiente: 'Ese horario empieza demasiado pronto para reservarlo.',
  anticipacion_excesiva: 'Ese horario aún no se puede reservar: está demasiado lejos.',
};
