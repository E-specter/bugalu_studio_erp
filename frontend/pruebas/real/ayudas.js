// Ayudas compartidas por los recorridos reales. Desde RF-17 reservar exige textos de registro aceptados, perfil con documento y la version de las condiciones.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const API = 'http://127.0.0.1:8010/api/v1';
export const BACKEND = resolve(import.meta.dirname, '../../../backend');

// Idempotente: publica los textos que aun no tienen version (tras `db reset`). Se llama en el beforeAll de cada recorrido.
export const cargarTextos = () => execFileSync('uv', ['run', 'python', '-m', 'bugalu.herramientas.cargar_textos_legales'], { cwd: BACKEND, encoding: 'utf8' });

// Llamada a la API desde la pagina con el token de esa sesion (el de supabase-js en localStorage).
export const llamar = (page, metodo, ruta, cuerpo) =>
  page.evaluate(async ({ url, metodo, cuerpo }) => {
    const token = JSON.parse(localStorage.getItem('bugalu-sesion')).access_token;
    const r = await fetch(url, { method: metodo, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    return { estado: r.status, cuerpo: await r.json().catch(() => null) };
  }, { url: API + ruta, metodo, cuerpo });

// DNI de 8 cifras distinto en cada llamada (un repetido no bloquea, pero marca la cuenta).
let serie = Date.now() % 1e7;
export const dniNuevo = () => String(10_000_000 + ((serie += 7919) % 80_000_000));

// Por la API, con la sesion de la pagina: documento en el perfil y aceptacion `registro` de lo que el perfil pide.
export async function prepararCliente(page, documento = dniNuevo()) {
  const parche = await llamar(page, 'PATCH', '/perfil', { documento: { tipo: 'dni', numero: documento } });
  if (parche.estado !== 200) throw new Error(`PATCH /perfil ${parche.estado}: ${JSON.stringify(parche.cuerpo)}`);
  const { cuerpo: perfil } = await llamar(page, 'GET', '/perfil');
  const vigentes = await (await fetch(`${API}/textos-legales`)).json();
  const textos = perfil.pendientes.filter((p) => p.contexto === 'registro').map((p) => ({ tipo: p.tipo, version: vigentes.find((t) => t.tipo === p.tipo && !t.programada).version }));
  if (textos.length) {
    const r = await llamar(page, 'POST', '/aceptaciones', { contexto: 'registro', textos });
    if (r.estado !== 201) throw new Error(`POST /aceptaciones ${r.estado}: ${JSON.stringify(r.cuerpo)}`);
  }
  return documento;
}

// Marca la casilla de condiciones del paso de confirmacion y reserva.
export async function confirmarReserva(page) {
  await page.getByRole('checkbox', { name: /Acepto las Condiciones de contratación/ }).check();
  await page.getByRole('button', { name: 'Confirmar reserva' }).click();
}

// Fechas desde ahora en Lima (UTC-5, sin horario de verano): el lunes de la semana siguiente y sus dias.
const lima = new Date(Date.now() - 5 * 3600_000);
const lunesSiguiente = new Date(Date.UTC(lima.getUTCFullYear(), lima.getUTCMonth(), lima.getUTCDate() + (8 - (lima.getUTCDay() || 7))));
export const dia = (n) => new Date(lunesSiguiente.getTime() + n * 86400_000);
export const ymd = (d) => d.toISOString().slice(0, 10);
export const inicio = (d, hora) => `${ymd(d)}T${hora}:00-05:00`;
export const hoyMasDias = (n) => ymd(new Date(lima.getTime() + n * 86400_000));

// Solo pruebas: la clave de servicio borra los objetos de Storage que crea el recorrido (Configuracion y src/ no la conocen).
export const claveServicio = () => process.env.CLAVE_SERVICIO_SUPABASE_PRUEBAS ?? readFileSync(resolve(BACKEND, '.env'), 'utf8').match(/^CLAVE_SERVICIO_SUPABASE_PRUEBAS=(.+)$/m)?.[1].trim();

// Vacia `comprobantes/<id>/` de cada usuario y devuelve cuantos objetos borro; falla si quedan huerfanos.
export async function vaciarComprobantes(ids, supabase = 'http://127.0.0.1:45621') {
  const clave = claveServicio();
  const cabeceras = { apikey: clave, authorization: `Bearer ${clave}`, 'content-type': 'application/json' };
  const listar = async (id) => (await (await fetch(`${supabase}/storage/v1/object/list/comprobantes`, { method: 'POST', headers: cabeceras, body: JSON.stringify({ prefix: id, limit: 100 }) })).json()).map((o) => `${id}/${o.name}`);
  let borrados = 0;
  let restos = 0;
  for (const id of ids) {
    const objetos = await listar(id);
    borrados += objetos.length;
    if (objetos.length) await fetch(`${supabase}/storage/v1/object/comprobantes`, { method: 'DELETE', headers: cabeceras, body: JSON.stringify({ prefixes: objetos }) });
    restos += (await listar(id)).length;
  }
  if (restos) throw new Error(`${restos} huérfanos en comprobantes`);
  return borrados;
}
