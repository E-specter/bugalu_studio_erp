import { pedir } from './api.js';
import { hoyLima, diaMesAnio } from './formatos.js';

// RF-03 (CA-10 a CA-13): aforo por sala. `datos` = {aforo, itse_certificado, itse_vence}; responde la Sala actualizada.
export const guardarSala = (id, datos) => pedir(`/api/v1/salas/${encodeURIComponent(id)}`, { method: 'PATCH', cuerpo: datos });

export const personas = (n) => `${n} ${n === 1 ? 'persona' : 'personas'}`;

const ITSE = 'Inspección Técnica de Seguridad en Edificaciones';

// <abbr> de ITSE: lo comparten el calendario y Reservar.
const abbr = () => Object.assign(document.createElement('abbr'), { textContent: 'ITSE', title: ITSE });

export const certificado = (itse) => ['Certificado ', abbr(), ` ${itse.certificado}`];

// Nodos de "Aforo máximo: 6 personas · Certificado ITSE 0123-2026"; null sin aforo. El público nunca ve el vencimiento (decisión del brief).
export function lineaAforo(sala) {
  if (sala?.aforo == null) return null;
  const nodos = [`Aforo máximo: ${personas(sala.aforo)}`];
  if (sala.itse?.certificado) nodos.push(' · ', ...certificado(sala.itse));
  return nodos;
}

// Estado del certificado para el Administrador: días que quedan (vence - hoy en Lima) y su clase.
export function estadoItse(sala) {
  if (sala?.aforo == null || !sala.itse) return { clase: 'sin-registrar' };
  const dias = Math.round((Date.parse(`${sala.itse.vence}T00:00:00Z`) - Date.parse(`${hoyLima()}T00:00:00Z`)) / 864e5);
  const vence = diaMesAnio(sala.itse.vence);
  if (dias < 0) return { clase: 'vencido', dias, vence };
  return { clase: dias <= 30 ? 'por-vencer' : 'vigente', dias, vence };
}

export const cuando = (dias) => (dias === 0 ? 'vence hoy' : dias === 1 ? 'vence mañana' : `vence en ${dias} días`);
