// Datos comunes de las pruebas de RF-17 (textos legales y perfil reforzado).
import { perfil } from './ayudas-acceso.js';

export const t = (tipo, version, resumenes, extra = {}) => ({ tipo, version, tipo_cambio: 'mayor', vigente_desde: '2026-11-01T00:00:00-05:00', resumenes, programada: false, resumen_cambios: null, ...extra });
export const TEXTOS = [
  t('terminos_uso', '1.0.0', { registro: 'Reglas de uso del estudio.' }),
  t('politica_privacidad', '1.2.3', { registro: 'Cómo tratamos tus datos.', pago: 'Revisamos tu pago a mano.', promociones: 'Es opcional.' }),
  t('condiciones_contratacion', '2.0.0', { reserva: 'Pagas el adelanto para confirmar.', usos_promocionales: 'Fragmentos de 30 segundos.' }),
  t('declaracion_agrupacion', '1.0.0', { registro: 'Representas a tu agrupación.' }),
];
export const P = (tipo, version, motivo = 'nuevo') => ({ tipo, version, contexto: 'registro', motivo });
export const PERFIL = {
  modalidad: 'individual', documento: { tipo: 'dni', numero: '12345678' }, domicilio: null, redes: [], integrantes: [], es_menor: false,
  consentimientos: { promociones_correo: false, promociones_whatsapp: false, fotos_videos: false, excluir_material: false }, pendientes: [], datos_para_reservar: true, telefono: '987654321',
};
export const perfilApi = (extra = {}) => perfil({ ...PERFIL, ...extra });

