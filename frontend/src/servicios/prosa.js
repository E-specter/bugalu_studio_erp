// Prosa de un texto legal (RF-17): la usan la pagina publica y el panel del Administrador (ver, vista previa y revision).
const PERMITIDOS = ['href', 'src', 'alt', 'title', 'colspan', 'rowspan', 'scope'];

// El backend ya sanea el HTML; esto es una segunda barrera en el navegador: DOMParser no ejecuta nada y se quita lo activo.
// `titulo`: nivel del encabezado que contiene la prosa; los del texto bajan hasta quedar por debajo (hasta <h6>).
// `nuevaPestana`: los enlaces abren aparte para no perder lo escrito (editor del Administrador).
export function limpiar(html, { titulo = 1, nuevaPestana = false } = {}) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script, style, iframe, object, embed, form, link, meta, base, svg, math').forEach((n) => n.remove());
  doc.body.querySelectorAll('*').forEach((n) => {
    for (const a of [...n.attributes]) {
      // Solo atributos permitidos; los enlaces, a https, correo, ancla o ruta propia (no `//x` ni `/\x`).
      const url = ['href', 'src'].includes(a.name) && !/^(https?:|mailto:|#|\/(?![/\\]))/i.test(a.value.replace(/[\t\n\r ]/g, ''));
      if (!PERMITIDOS.includes(a.name) || url) n.removeAttribute(a.name);
    }
  });
  const encabezados = [...doc.body.querySelectorAll('h1, h2, h3, h4, h5, h6')];
  const menor = Math.min(...encabezados.map((h) => Number(h.tagName[1])));
  if (encabezados.length && menor <= titulo) {
    encabezados.reverse().forEach((h) => {
      const nuevo = doc.createElement(`h${Math.min(6, Number(h.tagName[1]) + titulo + 1 - menor)}`);
      nuevo.append(...h.childNodes);
      h.replaceWith(nuevo);
    });
  }
  if (nuevaPestana) {
    doc.body.querySelectorAll('a[href]:not([href^="#"])').forEach((a) => {
      a.target = '_blank';
      a.rel = 'noopener';
      const aviso = doc.createElement('span');
      aviso.className = 'visualmente-oculto';
      aviso.textContent = ' (se abre en otra pestaña)';
      a.append(aviso);
    });
  }
  return [...doc.body.childNodes];
}
