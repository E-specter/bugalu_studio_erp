import { ErrorAcceso, obtenerCliente } from './sesion.js';

// CA-06: pide el enlace de un solo uso; al abrirlo, la sesion vuelve a /app/perfil?verificar=1.
// Solo para quien ya tiene cuenta: shouldCreateUser false evita crear una cuenta con un correo ajeno.
export async function pedirEnlaceVerificacion(correo) {
  let error;
  try {
    ({ error } = await obtenerCliente().auth.signInWithOtp({ email: correo, options: { shouldCreateUser: false, emailRedirectTo: `${location.origin}/app/perfil?verificar=1` } }));
  } catch (e) {
    error = e;
  }
  if (!error) return;
  throw new ErrorAcceso(error.status === 429 || /^over_.*rate_limit$/.test(error.code ?? '') ? 'limite' : error.status === 0 || error.name === 'AuthRetryableFetchError' ? 'red' : 'servicio');
}
