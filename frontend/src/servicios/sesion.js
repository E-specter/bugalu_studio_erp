import { createClient } from '@supabase/supabase-js';

const CLAVE_SESION = 'bugalu-sesion';

// Solo la clave publicable: ninguna clave secreta ni de servicio llega al navegador.
let cliente;
export function obtenerCliente() {
  cliente ??= createClient(import.meta.env.PUBLIC_URL_SUPABASE, import.meta.env.PUBLIC_CLAVE_PUBLICABLE_SUPABASE, {
    auth: { storageKey: CLAVE_SESION },
  });
  return cliente;
}

// Token de acceso de la sesion actual (supabase-js lo renueva si caduco) o null.
export async function obtenerToken() {
  try {
    const { data } = await obtenerCliente().auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    // Sin configuracion o sin almacenamiento: se trata como sin sesion y el backend responde 401.
    return null;
  }
}

// --- Rutas y datos de formulario ---

// `volver` solo acepta rutas propias (RF-01, acceso): empieza por "/", no por "//", sin "\" ni caracteres de control
// (el navegador quita tabuladores y saltos de linea de una URL, y "/\t/x" pasaria a ser "//x").
export function rutaPropia(valor) {
  return typeof valor === 'string' && /^\/(?![/\\])[^\\\u0000-\u001f]*$/.test(valor) ? valor : null;
}

// Telefono: se quitan los espacios; 9 a 15 digitos con "+" inicial opcional. null si no vale (el disparador lo descartaria en silencio).
export function normalizarTelefono(valor) {
  const limpio = String(valor ?? '').replace(/\s+/g, '');
  return /^\+?[0-9]{9,15}$/.test(limpio) ? limpio : null;
}

// --- Errores de Supabase Auth, en español y sin revelar si un correo existe ---

// tipo -> [titulo, texto]; el aviso muestra ambos y un error de campo los une.
const textos = {
  credenciales: ['Correo o contraseña incorrectos', 'Revísalos o recupera tu contraseña.'],
  correo_existente: ['Ya hay una cuenta con este correo', 'Inicia sesión o recupera tu contraseña.'],
  contrasena_debil: ['La contraseña es débil', 'Usa 8 caracteres o más, con minúscula, mayúscula, número y símbolo.'],
  misma_contrasena: ['Elige una contraseña distinta de la anterior', 'No puede repetir la actual.'],
  enlace_caducado: ['El enlace caducó o ya se usó', 'Pide otro enlace para crear una contraseña nueva.'],
  telefono: ['Escribe entre 9 y 15 dígitos', 'Puedes empezar con +.'],
  limite: ['Demasiados intentos', 'Espera unos minutos y vuelve a intentarlo.'],
  servicio: ['El servicio de acceso no responde', 'Inténtalo de nuevo en unos minutos.'],
  red: ['Sin conexión', 'Revisa tu red y vuelve a intentarlo.'],
  desconocido: ['Algo salió mal', 'Inténtalo de nuevo.'],
};

export class ErrorAcceso extends Error {
  constructor(tipo) {
    const [titulo, texto] = textos[tipo];
    super(`${titulo}. ${texto}`);
    this.name = 'ErrorAcceso';
    this.tipo = tipo;
    this.titulo = titulo;
    this.texto = texto;
  }
}

// Traduce un error de supabase-js por su `code` y estado, no por su mensaje en inglés.
function tipoDeError(error) {
  const codigo = error?.code ?? '';
  const estado = error?.status ?? 0;
  if (codigo === 'invalid_credentials') return 'credenciales';
  if (codigo === 'user_already_exists' || codigo === 'email_exists') return 'correo_existente';
  if (codigo === 'weak_password') return 'contrasena_debil';
  if (codigo === 'same_password') return 'misma_contrasena';
  // Sin sesion de recuperacion o con el token caducado al fijar la contraseña.
  if (estado === 401 || error?.name === 'AuthSessionMissingError') return 'enlace_caducado';
  if (estado === 429 || /^over_.*rate_limit$/.test(codigo)) return 'limite';
  if (error?.name === 'AuthRetryableFetchError' && estado === 0) return 'red';
  if (estado >= 500) return 'servicio';
  return 'desconocido';
}

// supabase-js devuelve {data, error}; aquí un fallo siempre es un ErrorAcceso.
async function llamar(promesa) {
  let resultado;
  try {
    resultado = await promesa;
  } catch (error) {
    throw new ErrorAcceso(tipoDeError(error));
  }
  if (resultado.error) throw new ErrorAcceso(tipoDeError(resultado.error));
  return resultado.data;
}

const auth = () => obtenerCliente().auth;

// --- Operaciones ---

// Devuelve { conSesion }: false si el servicio exige confirmar el correo antes de entrar.
export async function registrar({ correo, contrasena, nombre, telefono, nombreArtistico = "" }) {
  const numero = normalizarTelefono(telefono);
  if (!numero) throw new ErrorAcceso('telefono');
  const data = await llamar(
    auth().signUp({
      email: correo,
      password: contrasena,
      // Metadatos que lee el disparador de perfil (RF-01).
      options: { data: { nombre, telefono: numero, ...(nombreArtistico && { nombre_artistico: nombreArtistico }) } },
    }),
  );
  // Con "proteger enumeracion" el servicio no da error por un correo existente: devuelve un usuario sin identidades.
  if (data.user?.identities?.length === 0) throw new ErrorAcceso('correo_existente');
  return { conSesion: Boolean(data.session) };
}

export const iniciarSesion = ({ correo, contrasena }) => llamar(auth().signInWithPassword({ email: correo, password: contrasena }));

// Proveedores sociales (CA-04, ADR-009): lista de PUBLIC_ACCESO_PROVEEDORES al construir, filtrada por la lista cerrada; lo desconocido se ignora.
// Para sumar uno: agregarlo aqui y su texto de boton en Acceso.astro. El acceso interno nunca los usa.
/** @type {Record<string, string>} */
export const PROVEEDORES = { google: 'Google', facebook: 'Facebook' };
export const proveedoresDisponibles = [
  ...new Set(String(import.meta.env.PUBLIC_ACCESO_PROVEEDORES ?? '').split(',').map((p) => p.trim().toLowerCase())),
].filter((p) => Object.hasOwn(PROVEEDORES, p));
export async function iniciarConProveedor(proveedor, destino = '/app/') {
  if (!proveedoresDisponibles.includes(proveedor)) throw new ErrorAcceso('desconocido');
  await llamar(auth().signInWithOAuth({ provider: proveedor, options: { redirectTo: location.origin + (rutaPropia(destino) ?? '/app/') } }));
}

// CA-05: la misma respuesta exista o no el correo. Solo fallan 429, 5xx, red y respuestas ajenas a la API (no dependen del correo).
export async function recuperarContrasena(correo, origen) {
  const redirectTo = `${location.origin}/acceso/nueva-contrasena${origen === 'interno' ? '?origen=interno' : ''}`;
  let error;
  try {
    ({ error } = await auth().resetPasswordForEmail(correo, { redirectTo }));
  } catch (e) {
    error = e;
  }
  if (!error) return;
  // 4xx de la API distintos de 429 (user_not_found, email_address_invalid...): se responde igual que si existiera.
  if (error.name === 'AuthApiError' && error.status < 500 && error.status !== 429) return;
  throw new ErrorAcceso(tipoDeError(error));
}

// Espera la sesion de recuperacion que abre el enlace del correo: true si el enlace trae type=recovery y abre sesion.
// Debe llamarse antes que cualquier otro uso del cliente: el fragmento de la URL se procesa al inicializarlo.
// supabase-js emite INITIAL_SESSION antes que PASSWORD_RECOVERY, por eso se decide con el fragmento y la sesion.
export function esperarRecuperacion() {
  if (/error_code=|error=/.test(location.hash)) return Promise.resolve(false);
  const esRecuperacion = /type=recovery/.test(location.hash);
  return new Promise((resolver) => {
    const { data } = auth().onAuthStateChange((evento, sesion) => {
      if (evento !== 'PASSWORD_RECOVERY' && evento !== 'INITIAL_SESSION') return;
      resolver(evento === 'PASSWORD_RECOVERY' || (esRecuperacion && Boolean(sesion)));
      // La suscripcion aun no existe dentro de su primer callback: se cancela en el ciclo siguiente.
      setTimeout(() => data.subscription.unsubscribe());
    });
  });
}

export const fijarContrasena = (nueva) => llamar(auth().updateUser({ password: nueva }));

// Area desde la que se entro ('estudio' o 'portal'): decide el destino de cerrar sesion si el perfil aun no dio el rol.
const CLAVE_AREA = 'bugalu-area';
export function recordarArea(area) {
  try {
    localStorage.setItem(CLAVE_AREA, area);
  } catch {
    // Sin almacenamiento: cerrar sesion cae al acceso de artistas.
  }
}
export function areaRecordada() {
  try {
    return localStorage.getItem(CLAVE_AREA);
  } catch {
    return null;
  }
}

// CA-12: borra la sesion del navegador aunque falle la red.
export async function cerrarSesion() {
  try {
    await auth().signOut({ scope: 'local' });
  } catch {
    // Se ignora: la sesion local se borra abajo igualmente.
  }
  try {
    localStorage.removeItem(CLAVE_SESION);
    localStorage.removeItem(CLAVE_AREA);
  } catch {
    // Sin almacenamiento no hay sesion que borrar.
  }
}
