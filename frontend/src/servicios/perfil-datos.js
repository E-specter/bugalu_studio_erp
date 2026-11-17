// Reglas de los datos del perfil que comparten el perfil y el paso 03 de la reserva (spec RF-17-perfil, Datos).
export const TIPOS_DOCUMENTO = { dni: 'DNI', ce: 'Carné de extranjería', pasaporte: 'Pasaporte' };

// Devuelve {tipo, numero} con el mensaje de error de cada campo, o {valor: {tipo, numero}} normalizado.
export function validarDocumento(tipo, numero) {
  const limpio = String(numero ?? '').replace(/\s+/g, '');
  if (!Object.hasOwn(TIPOS_DOCUMENTO, tipo)) return { tipo: 'Elige el tipo de documento.' };
  if (tipo === 'dni') return /^[0-9]{8}$/.test(limpio) ? { valor: { tipo, numero: limpio } } : { numero: 'Escribe los 8 dígitos de tu DNI.' };
  const mayus = limpio.toUpperCase();
  return /^[A-Z0-9]{6,12}$/.test(mayus) ? { valor: { tipo, numero: mayus } } : { numero: 'Escribe de 6 a 12 letras o cifras, sin espacios ni guiones.' };
}

// Un perfil que aun no permite reservar: datos o textos del registro por aceptar, o menor (etapa A).
export const faltaParaReservar = (perfil) => perfil.es_menor === true || perfil.datos_para_reservar === false || (perfil.pendientes ?? []).some((p) => p.contexto === 'registro');
