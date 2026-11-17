import { pedir } from './api.js';
import { tipos } from './textos-legales.js';

// Contrato de RF-17: POST /aceptaciones {contexto, textos: [{tipo, version}]}, historial propio, consentimientos y las aceptaciones de una persona (Administrador).
export const aceptar = (contexto, textos) => pedir('/api/v1/aceptaciones', { method: 'POST', cuerpo: { contexto, textos } });
export const misAceptaciones = () => pedir('/api/v1/aceptaciones/mias');
export const aceptacionesDe = (id) => pedir(`/api/v1/usuarios/${encodeURIComponent(id)}/aceptaciones`);
export const guardarConsentimientos = (cuerpo) => pedir('/api/v1/perfil/consentimientos', { method: 'PUT', cuerpo });

// Textos vigentes (no programados) que traen resumen para ese paso.
export const vigentesDe = (lista, contexto) => lista.filter((t) => !t.programada && t.resumenes?.[contexto]);
export const vigenteDe = (lista, tipo) => lista.find((t) => t.tipo === tipo && !t.programada);
export const enlaceTexto = (tipo, version) => `/legal/${tipos[tipo].slug}/?version=${encodeURIComponent(version)}`;

// Los textos de la lista pendientes del paso, con la version vigente (la que se acepta), no la que el perfil vio.
export const pendientesDe = (perfil, contexto) => (perfil.pendientes ?? []).filter((p) => p.contexto === contexto);

const LEER = { terminos_uso: 'los Términos de uso', politica_privacidad: 'la Política de privacidad', condiciones_contratacion: 'las Condiciones de contratación', declaracion_agrupacion: 'la Declaración de agrupación' };
// Con varios textos en un bloque, cada enlace dice cual es; con uno, "Leer el texto completo (versión 1.0.0)".
export const enlacesDe = (textos) =>
  textos.map((t) => ({
    etiqueta: textos.length > 1 ? `Leer ${LEER[t.tipo]} (versión ${t.version})` : `Leer el texto completo (versión ${t.version})`,
    href: enlaceTexto(t.tipo, t.version),
  }));

export const dondeAcepto = { registro: 'Registro', reserva: 'Reserva', asesoria: 'Asesoría', pago: 'Pago', promociones: 'Promociones', usos_promocionales: 'Usos promocionales' };

// Bloques de aceptacion del registro: terminos y politica comparten casilla; la declaracion de agrupacion lleva la suya.
// `pendientes`: los tipos de texto por aceptar. Devuelve [{clave, titulo, resumenes, enlaces, casilla: {nombre, etiqueta}, textos: [{tipo, version}]}].
export function bloquesRegistro(lista, pendientes) {
  const falta = (tipo) => (pendientes.includes(tipo) ? vigenteDe(lista, tipo) : undefined);
  const grupo = ['terminos_uso', 'politica_privacidad'].map(falta).filter((t) => t?.resumenes?.registro);
  const bloques = [];
  if (grupo.length) {
    const [terminos, politica] = [grupo.find((t) => t.tipo === 'terminos_uso'), grupo.find((t) => t.tipo === 'politica_privacidad')];
    const etiqueta = terminos && politica
      ? `Acepto los Términos de uso (versión ${terminos.version}) y he leído la Política de privacidad (versión ${politica.version}).`
      : terminos ? `Acepto los Términos de uso (versión ${terminos.version}).` : `He leído la Política de privacidad (versión ${politica.version}).`;
    bloques.push({
      clave: 'terminos',
      titulo: terminos && politica ? 'Términos de uso y política de privacidad' : terminos ? 'Términos de uso' : 'Política de privacidad',
      resumenes: grupo.map((t) => t.resumenes.registro),
      enlaces: enlacesDe(grupo),
      casilla: { nombre: 'terminos', etiqueta },
      textos: grupo.map(({ tipo, version }) => ({ tipo, version })),
    });
  }
  const declaracion = falta('declaracion_agrupacion');
  if (declaracion?.resumenes?.registro) {
    bloques.push({
      clave: 'declaracion',
      titulo: 'Declaración de agrupación',
      resumenes: [declaracion.resumenes.registro],
      enlaces: enlacesDe([declaracion]),
      casilla: { nombre: 'declaracion', etiqueta: 'Declaro que represento a la agrupación, que sus integrantes me autorizaron a contratar por ella y a dar sus datos, y que conocen estos textos.' },
      textos: [{ tipo: declaracion.tipo, version: declaracion.version }],
    });
  }
  return bloques;
}

// Bloque de las condiciones de contratacion de la reserva; null si no hay texto vigente con resumen para `reserva`.
export function bloqueReserva(lista) {
  const t = vigenteDe(lista, 'condiciones_contratacion');
  if (!t?.resumenes?.reserva) return null;
  return {
    titulo: 'Condiciones de contratación',
    resumenes: [t.resumenes.reserva],
    enlaces: enlacesDe([t]),
    casilla: { nombre: 'condiciones', etiqueta: `Acepto las Condiciones de contratación (versión ${t.version}), incluida la propiedad intelectual de las grabaciones.` },
    version: t.version,
  };
}
