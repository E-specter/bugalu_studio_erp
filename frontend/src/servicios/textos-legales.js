import { pedir } from './api.js';

// Textos de la etapa A (RF-17); `autorizacion_menor` entra con la etapa B. `contextos`: pasos donde se muestra el resumen de cada texto (resumenes-para-pantallas).
export const tipos = {
  terminos_uso: { slug: 'terminos-de-uso', nombre: 'Términos de uso', contextos: ['registro'] },
  politica_privacidad: { slug: 'privacidad', nombre: 'Política de privacidad', contextos: ['pago', 'promociones'] },
  condiciones_contratacion: { slug: 'condiciones-de-contratacion', nombre: 'Condiciones de contratación', contextos: ['reserva', 'asesoria', 'usos_promocionales'] },
  declaracion_agrupacion: { slug: 'declaracion-de-agrupacion', nombre: 'Declaración de agrupación', contextos: ['registro'] },
};
export const contextos = { registro: 'Registro', reserva: 'Reserva de sala', asesoria: 'Asesoría', pago: 'Registro de un pago', promociones: 'Promociones', usos_promocionales: 'Usos promocionales' };

// Contrato de RF-17: los GET son publicos (`sinToken`: un token caducado no los rompe); POST y DELETE son del Administrador.
export const listarTextosLegales = () => pedir('/api/v1/textos-legales', { sinToken: true });
export const obtenerVersionTexto = (tipo, version) => pedir(`/api/v1/textos-legales/${encodeURIComponent(tipo)}/versiones/${encodeURIComponent(version)}`, { sinToken: true });
export const publicarTexto = (cuerpo) => pedir('/api/v1/textos-legales', { method: 'POST', cuerpo });
export const retirarVersion = (tipo, version) => pedir(`/api/v1/textos-legales/${encodeURIComponent(tipo)}/versiones/${encodeURIComponent(version)}`, { method: 'DELETE' });

export const esVersion = (v) => /^\d+\.\d+\.\d+$/.test(v ?? '');

// La vigente es la del tipo que no esta `programada`; a lo mas hay una programada (CA-02).
export const delTipo = (lista, tipo) => ({
  vigente: lista.find((t) => t.tipo === tipo && !t.programada),
  programada: lista.find((t) => t.tipo === tipo && t.programada),
});

// Sin version previa, cualquier tipo de cambio arranca en 1.0.0.
export function siguienteVersion(ultima, cambio) {
  if (!ultima) return '1.0.0';
  const [a, b, c] = ultima.split('.').map(Number);
  return cambio === 'mayor' ? `${a + 1}.0.0` : cambio === 'menor' ? `${a}.${b + 1}.0` : `${a}.${b}.${c + 1}`;
}
