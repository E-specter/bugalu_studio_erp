// Formatos de las pantallas del Administrador: fechas de Lima (UTC-5, sin horario de verano) e importes como texto decimal.
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const DIA_MS = 864e5;
const LIMA_MS = 5 * 3600e3;

// Una fecha de Lima "AAAA-MM-DD" se maneja como medianoche UTC; un instante ISO, desplazado a la hora de Lima.
const aFecha = (fecha) => new Date(`${fecha}T00:00:00Z`);
const deLima = (iso) => new Date(Date.parse(iso) - LIMA_MS);

export const hoyLima = () => new Date(Date.now() - LIMA_MS).toISOString().slice(0, 10);
export const fechaDe = (iso) => deLima(iso).toISOString().slice(0, 10);
export const horaDe = (iso) => deLima(iso).toISOString().slice(11, 16);
export const instante = (fecha, hora) => `${fecha}T${hora}:00-05:00`;
export const sumarDias = (fecha, n) => new Date(aFecha(fecha).getTime() + n * DIA_MS).toISOString().slice(0, 10);
export const esFecha = (texto) => /^\d{4}-\d{2}-\d{2}$/.test(texto ?? '') && aFecha(texto).toISOString().startsWith(texto);

// Lunes (AAAA-MM-DD) de una semana ISO AAAA-Www; null si no es valida.
export function lunesDe(semana) {
  const m = /^(\d{4})-W(\d{2})$/.exec(semana ?? '');
  if (!m || +m[2] < 1 || +m[2] > 53) return null;
  const enero4 = aFecha(`${m[1]}-01-04`);
  const lunes = new Date(enero4.getTime() - ((enero4.getUTCDay() || 7) - 1) * DIA_MS + (+m[2] - 1) * 7 * DIA_MS);
  return lunes.toISOString().slice(0, 10);
}

// Semana ISO (AAAA-Www) de una fecha: la del jueves de esa semana.
export function semanaDe(fecha) {
  const f = aFecha(fecha);
  const jueves = new Date(f.getTime() + (4 - (f.getUTCDay() || 7)) * DIA_MS);
  const anio = jueves.getUTCFullYear();
  const semana = Math.ceil(((jueves - Date.UTC(anio, 0, 1)) / DIA_MS + 1) / 7);
  return `${anio}-W${String(semana).padStart(2, '0')}`;
}

const partes = (fecha) => {
  const f = aFecha(fecha);
  return { dia: DIAS[f.getUTCDay()], numero: f.getUTCDate(), mes: MESES[f.getUTCMonth()], anio: f.getUTCFullYear() };
};
export const nombreDia = (fecha) => partes(fecha).dia;
export const diaCorto = (fecha) => { const p = partes(fecha); return `${p.dia.slice(0, 3)} ${p.numero} ${p.mes}`.toUpperCase(); }; // MAR 18 NOV
export const diaLargo = (fecha) => { const p = partes(fecha); return `${p.dia} ${p.numero} ${p.mes}`.toUpperCase(); }; // LUNES 16 NOV
export const diaMes = (fecha) => { const p = partes(fecha); return `${p.numero} ${p.mes}`; }; // 25 dic
export const diaMesAnio = (fecha) => `${diaMes(fecha)} ${partes(fecha).anio}`; // 25 dic 2026
// "SEMANA DEL 16 AL 22 NOV 2026"; si cruza mes o año, cada extremo lleva lo suyo ("28 DIC 2026 AL 3 ENE 2027").
export function rangoSemana(lunes) {
  const a = partes(lunes);
  const b = partes(sumarDias(lunes, 6));
  const desde = a.anio === b.anio ? `${a.numero}${a.mes === b.mes ? '' : ` ${a.mes}`}` : `${a.numero} ${a.mes} ${a.anio}`;
  return `SEMANA DEL ${desde} AL ${b.numero} ${b.mes} ${b.anio}`.toUpperCase();
}

// --- Importes: el campo acepta coma o punto; a la API va "125.50" ---
const DECIMAL = /^\d+([.,]\d{1,2})?$/;
// "125,5" -> "125.50"; null si esta vacio, es negativo o tiene mas de dos decimales.
export function leerImporte(texto) {
  const t = String(texto ?? '').trim();
  if (!DECIMAL.test(t)) return null;
  const [entero, decimales = ''] = t.replace(',', '.').split('.');
  return `${entero.replace(/^0+(?=\d)/, '')}.${decimales.padEnd(2, '0')}`;
}
// "125.5" -> "125,50" (para el campo).
export const mostrarImporte = (monto) => (leerImporte(monto) ?? String(monto ?? '')).replace('.', ',');
// "1250.00" -> "S/ 1 250,00" (miles con espacio no separable); el campo usa mostrarImporte, sin agrupar.
export const soles = (monto) => {
  const [entero, decimales] = mostrarImporte(monto).split(',');
  return `S/ ${entero.replace(/\B(?=(\d{3})+$)/g, ' ')}${decimales === undefined ? '' : `,${decimales}`}`;
};

// --- Partidas de precio (reservar y mis reservas comparten este formato) ---
const RECARGOS = { noche: 'Recargo de noche', fin_de_semana: 'Recargo de fin de semana', feriado: 'Recargo de feriado' };
// 150 -> "2 h 30 min", 30 -> "30 min", 120 -> "2 h".
export const duracionReserva = (min) => [Math.floor(min / 60) && `${Math.floor(min / 60)} h`, min % 60 && `${min % 60} min`].filter(Boolean).join(' ') || '0 min';
const cantidadPartida = (cantidad, unidad) =>
  unidad === 'hora' ? duracionReserva(Math.round(Number(cantidad) * 60))
  : unidad === 'lapso_30' ? `${Number(cantidad)} × 30 min`
  : unidad === 'fijo' ? '1'
  : String(Number(cantidad));
// Simulacion -> { filas: [[concepto, cantidad, importe]], pie: [[etiqueta, importe]] }; solo formatea, nunca suma.
export function partidasPrecio(precio) {
  return {
    filas: [
      ...precio.lineas.map((l) => [l.concepto, cantidadPartida(l.cantidad, l.unidad), soles(l.monto)]),
      ...precio.recargos.map((r) => [RECARGOS[r.tipo] ?? 'Recargo', `${r.bloques} × 30 min`, soles(r.monto)]),
    ],
    pie: [['Total', soles(precio.total)], ['Anticipo 50 %', soles(precio.anticipo)]],
  };
}
// Pinta las partidas en una <Tabla variante="partidas"> ya renderizada (<tbody> y <tfoot>).
export function pintarPartidas(tabla, precio) {
  const { filas, pie } = partidasPrecio(precio);
  const celda = (etiqueta, texto) => {
    const td = Object.assign(document.createElement('td'), { textContent: texto, className: 'tabla-num' });
    td.dataset.etiqueta = etiqueta;
    return td;
  };
  const th = (texto, extra = {}) => Object.assign(document.createElement('th'), { scope: 'row', textContent: texto, ...extra });
  const fila = (...nodos) => { const tr = document.createElement('tr'); tr.append(...nodos); return tr; };
  tabla.querySelector('tbody').replaceChildren(...filas.map(([c, q, i]) => fila(th(c), celda('Cantidad', q), celda('Importe', i))));
  tabla.querySelector('tfoot').replaceChildren(...pie.map(([e, i]) => fila(th(e, { colSpan: 2 }), celda('Importe', i))));
}
