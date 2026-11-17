// Datos comunes de las pruebas de RF-18 (cancelacion por niveles, creditos, devoluciones, inasistencia). La API se simula con page.route.
export const ID = '11111111-1111-4111-8111-111111111111';
export const C1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
export const C2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
export const CR1 = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
export const CR2 = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
export const DV1 = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee';
export const DV2 = 'ffffffff-ffff-4fff-8fff-ffffffffffff';
export const AHORA = new Date('2026-11-15T15:00:00Z'); // domingo 15 nov 2026, 10:00 en Lima
export const dentroDe = (min) => new Date(AHORA.getTime() + min * 60e3).toISOString();
export const POLITICA = { horas_nivel_1: 48, horas_nivel_2: 24, porcentaje_penalizacion_nivel_2: 25, minutos_tolerancia_inasistencia: 15, dias_vigencia_credito: 30, reprogramaciones_nivel_1: 2, reprogramaciones_nivel_2: 1 };
export const PRECIO = { lineas: [{ concepto: 'Sala de grabación', cantidad: '2.00', unidad: 'hora', monto: '200.00' }], recargos: [], total: '200.00', anticipo: '100.00', porcentaje_adelanto: 50 };

export const pago = (extra = {}) => ({ id: 'p1', estado: 'aprobado', metodo: 'yape', monto: '100.00', numero_operacion: 'OP1234', motivo_rechazo: null, registrado_en: '2026-11-10T12:00:00Z', ...extra });
// Adelanto pagado (100.00) y saldo pendiente: lo que tiene una reserva confirmada con el adelanto pagado.
export const cuotasPagadas = (a = {}, b = {}) => [
  { id: C1, hito: 'al_reservar', monto: '100.00', estado: 'pagada', pagable: false, pagado: '100.00', pagos: [pago()], ...a },
  { id: C2, hito: 'al_terminar', monto: '100.00', estado: 'pendiente', pagable: false, pagado: '0.00', pagos: [], ...b },
];
export const cuotasSinPagos = () => [
  { id: C1, hito: 'al_reservar', monto: '100.00', estado: 'pendiente', pagable: true, pagado: '0.00', pagos: [] },
  { id: C2, hito: 'al_terminar', monto: '100.00', estado: 'pendiente', pagable: false, pagado: '0.00', pagos: [] },
];
export const reserva = (extra = {}) => ({
  id: ID, folio: 'R-2026-00001', estado: 'confirmada', motivo_cancelacion: null, nota_cancelacion: null, pago_por_validar: false,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T17:00:00-05:00', sala: 'Sala principal', servicio: 'Grabación de voces', especialistas: [],
  precio: PRECIO, vence_pago: null, cuotas: cuotasPagadas(), pagado: '100.00', politica: POLITICA, ...extra,
});

// VistaCancelacion de CA-02: total 200.00, adelanto pagado 100.00.
const POR_NIVEL = { 1: ['0.00', '100.00'], 2: ['50.00', '50.00'], 3: ['100.00', '0.00'] };
export const vista = (nivel, extra = {}) => {
  const [retenido, credito] = nivel ? POR_NIVEL[nivel] : ['0.00', '0.00'];
  return {
    nivel, anticipacion_horas: nivel === 1 ? 54 : nivel === 2 ? 30 : 10, pagado: nivel ? '100.00' : '0.00', en_validacion: '0.00', retenido, credito,
    credito_vence: Number(credito) > 0 ? '2026-12-15T23:59:59-05:00' : null, puede_reprogramar: nivel !== 3, reprogramaciones_restantes: nivel === 3 ? 0 : 2, ...extra,
  };
};
// Reserva ya cancelada con la politica aplicada.
export const cancelada = (nivel, extra = {}) => {
  const v = vista(nivel);
  return reserva({
    estado: 'cancelada', motivo_cancelacion: 'cliente', cuotas: cuotasPagadas({}, { estado: 'anulada', pagado: '0.00' }),
    cancelacion: { nivel, aviso_en: '2026-11-15T14:00:00-05:00', por: 'cliente', pagado: v.pagado, retenido: v.retenido, credito: v.credito, nota: null }, ...extra,
  });
};

// Reserva no_asistio: cancelacion con por 'inasistencia' y lo pagado retenido, sin credito.
export const noAsistio = (extra = {}) => reserva({
  estado: 'no_asistio', cuotas: cuotasPagadas({}, { estado: 'anulada' }),
  cancelacion: { nivel: null, aviso_en: '2026-11-15T09:55:00-05:00', por: 'inasistencia', pagado: '100.00', retenido: '100.00', credito: '0.00', nota: null, registrada_por: { id: 'u1', nombre: 'Ana' } }, ...extra,
});

export const credito = (extra = {}) => ({
  id: CR1, monto: '100.00', saldo: '100.00', vence: '2026-12-17T23:59:59-05:00', estado: 'vigente', tipo: 'nivel_1', origen: { id_reserva: ID, folio: 'R-2026-00001' }, ...extra,
});
export const devolucion = (extra = {}) => ({
  id: DV1, id_credito: CR1, id_reserva: ID, folio: 'R-2026-00001', cliente: { id: 'u3', nombre: 'Eva Soto' }, tipo: 'nivel_1', motivo: 'Prefiero el dinero porque no voy a reservar de nuevo.',
  solicitada_en: '2026-11-14T15:00:00Z', estado: 'pendiente', monto_solicitado: '100.00', ...extra,
});
