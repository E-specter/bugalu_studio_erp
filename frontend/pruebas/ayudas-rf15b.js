// Datos comunes de las pruebas de RF-15 etapa B (agendar, mis asesorias, pagar y reprogramar). La API se simula con page.route.
import { API, json, perfil, conSesion, silenciarApi } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { AHORA, POLITICA } from './ayudas-rf18.js';

export const PID = 'p1';
export const AID = '22222222-2222-4222-8222-222222222222';
export const CUOTA = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
export const CUOTA2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
export const IGV = { porcentaje: '18.00', incluido: true, base: '67.80', monto: '12.20' };
export const IGV_MAS = { porcentaje: '18.00', incluido: false, base: '80.00', monto: '14.40' };
export const PROF = {
  id: PID, nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat', foto_url: null, presentacion: null, redes: [],
  especialidades: [{ id: 'e1', nombre: 'Producción' }, { id: 'e2', nombre: 'Coros' }],
  duraciones: [{ minutos: 30, precio: '80.00', igv: IGV }, { minutos: 60, precio: '140.00', igv: { ...IGV, monto: '21.36' } }],
  activo: true, publicado: true,
};
export const TEXTOS = [{ tipo: 'condiciones_contratacion', version: '0.4.0', tipo_cambio: 'mayor', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes: { reserva: 'Resumen de la reserva.', asesoria: 'La asesoría dura 30 o 60 minutos y se paga por adelantado.' }, programada: false }];
const t = (dia, hora) => `2026-11-${dia}T${hora}:00-05:00`;
// Martes 17 nov: bloque 10:00-13:00 con una asesoria ajena de 11:00 a 12:00. Una asesoria de 60 min solo empieza a las 10:00 y a las 12:00.
export const DISP = (extra = {}) => ({
  limites: { desde: t('15', '17:00'), hasta: '2027-01-10T00:00:00-05:00' },
  horarios: [{ id: 'h1', inicio: t('17', '10:00'), fin: t('17', '13:00') }],
  ocupados: [{ inicio: t('17', '11:00'), fin: t('17', '12:00'), propia: false }],
  dias: [{ fecha: '2026-11-17', minutos_libres: 120 }], duraciones: PROF.duraciones, ...extra,
});
export const INICIO = t('17', '10:00');
export const dentroDe = (min) => new Date(AHORA.getTime() + min * 60e3).toISOString();

export const cuotaUnica = (extra = {}) => ({ id: CUOTA, hito: 'al_reservar', monto: '140.00', estado: 'pendiente', pagable: true, pagado: '0.00', pagos: [], ...extra });
export const pagoOk = (extra = {}) => ({ id: 'pg1', estado: 'aprobado', metodo: 'yape', monto: '140.00', numero_operacion: 'OP1234', motivo_rechazo: null, registrado_en: '2026-11-10T12:00:00Z', ...extra });
// Asesoria virtual de 1 h el vie 18 dic, pendiente de pago.
export const asesoria = (extra = {}) => ({
  id: AID, tipo: 'asesoria', folio: 'A-2026-00001', estado: 'pre_reservada', motivo_cancelacion: null, nota_cancelacion: null,
  inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T16:00:00-05:00', duracion: 60, modalidad: 'virtual', lugar: null, enlace: null,
  profesional: { id: PID, nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat' },
  precio: { total: '140.00', impuesto: { ...IGV, base: '118.64', monto: '21.36' } }, total: '140.00', vence_pago: dentroDe(26 * 60), cuotas: [cuotaUnica()], pagado: '0.00',
  politica: POLITICA, version_condiciones: '0.4.0', realizada_en: null, constancia_disponible: false, ...extra,
});
export const confirmada = (extra = {}) => asesoria({ estado: 'confirmada', vence_pago: null, cuotas: [cuotaUnica({ estado: 'pagada', pagable: false, pagado: '140.00', pagos: [pagoOk()] })], pagado: '140.00', ...extra });
export const resumen = (extra = {}) => ({
  id: AID, folio: 'A-2026-00001', estado: 'pre_reservada', inicio: '2026-12-18T15:00:00-05:00', fin: '2026-12-18T16:00:00-05:00', modalidad: 'virtual',
  profesional: { id: PID, nombre: 'Ana Pérez', nombre_artistico: 'Ana Beat' }, por_cerrar: false, vence_pago: dentroDe(26 * 60), encuentro_pendiente: true, ...extra,
});

export async function comoCliente(page, rol = 'cliente', extra = {}) {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol, telefono: '999111222', documento: { tipo: 'dni', numero: '12345678' }, datos_para_reservar: true, pendientes: [], ...extra })));
}
// Lo comun del flujo de agendar: profesional, disponibilidad y textos. `crear`: funcion (ruta) -> respuesta.
export async function montarAgendar(page, { prof = PROF, crear, sesion = true, perfilExtra } = {}) {
  if (sesion) await comoCliente(page, 'cliente', perfilExtra);
  else {
    await page.clock.setFixedTime(AHORA);
    await silenciarApi(page);
  }
  await simular(page, 'GET', `/profesionales/${PID}`, typeof prof === 'function' ? prof : json(200, prof));
  await simular(page, 'GET', `/profesionales/${PID}/disponibilidad`, json(200, DISP()));
  await simular(page, 'GET', '/textos-legales', json(200, TEXTOS));
  return crear ? simular(page, 'POST', '/asesorias', crear) : [];
}
