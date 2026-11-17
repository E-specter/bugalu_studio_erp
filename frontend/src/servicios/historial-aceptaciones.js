import { tipos } from './textos-legales.js';
import { enlaceTexto, dondeAcepto } from './aceptaciones.js';
import { fechaDe, horaDe, diaMesAnio } from './formatos.js';

// Pinta en `caja` la tabla de textos aceptados (la propia o la de una persona) con las plantillas de PlantillasHistorial.
// `cargar` devuelve [Aceptacion]; `textos`: {tabla, vacio, error} con el copy de cada vista. Lo mas reciente primero.
export async function pintarHistorial(isla, caja, cargar, textos) {
  const clonar = (nombre) => isla.querySelector(`template[data-historial="${nombre}"]`).content.cloneNode(true);
  caja.setAttribute('aria-busy', 'true');
  let lista;
  try {
    lista = await cargar();
    if (!Array.isArray(lista)) throw new Error('lista');
  } catch {
    const aviso = clonar('error');
    aviso.querySelector('.aviso-titulo').textContent = textos.error;
    caja.replaceChildren(aviso);
    caja.querySelector('[role]')?.removeAttribute('role'); // el bloque se anuncia solo al cargar
    return caja.setAttribute('aria-busy', 'false');
  }
  caja.setAttribute('aria-busy', 'false');
  if (!lista.length) {
    const vacio = clonar('vacio');
    vacio.querySelector('p').textContent = textos.vacio;
    return caja.replaceChildren(vacio);
  }
  const tabla = clonar('tabla');
  tabla.querySelector('caption').textContent = textos.tabla;
  tabla.querySelector('tbody').append(
    ...[...lista].sort((a, b) => Date.parse(b.aceptada_en) - Date.parse(a.aceptada_en)).map((a) => {
      const fila = clonar('fila');
      fila.querySelector('[data-nombre]').textContent = tipos[a.tipo]?.nombre ?? a.tipo;
      const enlace = fila.querySelector('[data-version]');
      if (tipos[a.tipo]) Object.assign(enlace, { href: enlaceTexto(a.tipo, a.version), textContent: `versión ${a.version}` });
      else enlace.replaceWith(`versión ${a.version}`);
      const donde = fila.querySelector('[data-donde]');
      const nombreDonde = dondeAcepto[a.contexto] ?? a.contexto;
      if (a.contexto === 'reserva' && a.id_operacion) donde.append(Object.assign(document.createElement('a'), { href: `/app/reservas/detalle?id=${encodeURIComponent(a.id_operacion)}`, textContent: nombreDonde }));
      else donde.textContent = nombreDonde;
      fila.querySelector('[data-fecha]').textContent = `${diaMesAnio(fechaDe(a.aceptada_en))}, ${horaDe(a.aceptada_en)}`;
      fila.querySelector('[data-retirada]').textContent = a.retirada_en ? `Retirado el ${diaMesAnio(fechaDe(a.retirada_en))}` : '—';
      return fila;
    }),
  );
  caja.replaceChildren(tabla);
}
