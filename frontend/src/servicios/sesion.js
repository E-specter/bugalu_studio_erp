import { createClient } from '@supabase/supabase-js';

// Solo la clave publicable: ninguna clave secreta ni de servicio llega al navegador.
let cliente;
function obtenerCliente() {
  cliente ??= createClient(import.meta.env.PUBLIC_URL_SUPABASE, import.meta.env.PUBLIC_CLAVE_PUBLICABLE_SUPABASE, {
    auth: { storageKey: 'bugalu-sesion' },
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
