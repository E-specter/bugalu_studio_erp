// Llena y gestiona el resumen legal que la isla clona de PlantillasResumenLegal (ficha resumen-legal.md).
let contador = 0;

// `casillas`: [{nombre, etiqueta}]; sin casillas es la variante lectura. `enlaces`: [{etiqueta, href}]. Ninguna casilla nace marcada.
export function resumenLegal(isla, { variante = 'obligatoria', titulo, resumenes, enlaces, casillas = /** @type {any[]} */ ([]) }) {
  const nodo = isla.querySelector(`template[data-plantilla="${casillas.length ? 'resumen-casillas' : 'resumen-lectura'}"]`).content.cloneNode(true);
  const raiz = nodo.firstElementChild;
  const uid = `resumen-legal-${++contador}`;
  raiz.querySelector('.resumen-legal-titulo').textContent = titulo;
  const texto = raiz.querySelector('.resumen-legal-texto');
  texto.id = `${uid}-texto`;
  texto.replaceChildren(...resumenes.map((r) => Object.assign(document.createElement('p'), { textContent: r })));
  const item = raiz.querySelector('.resumen-legal-enlaces li');
  item.replaceWith(...enlaces.map((e) => {
    const li = item.cloneNode(true);
    li.querySelector('a').href = e.href;
    li.querySelector('[data-etiqueta]').textContent = e.etiqueta;
    return li;
  }));
  if (casillas.length) {
    const casilla = raiz.querySelector('.casilla');
    casilla.replaceWith(...casillas.map((c) => {
      const clon = casilla.cloneNode(true);
      const entrada = clon.querySelector('input');
      entrada.name = c.nombre;
      entrada.required = variante === 'obligatoria';
      entrada.setAttribute('aria-describedby', texto.id);
      if (c.deshabilitada) entrada.setAttribute('aria-disabled', 'true');
      clon.querySelector('.casilla-etiqueta').textContent = c.etiqueta;
      if (c.detalle) {
        const detalle = Object.assign(document.createElement('span'), { className: 'casilla-detalle', textContent: c.detalle, id: `${uid}-${c.nombre}-detalle` });
        clon.querySelector('.casilla-texto').append(detalle);
        entrada.setAttribute('aria-describedby', `${texto.id} ${detalle.id}`);
      }
      return clon;
    }));
    raiz.querySelector('[data-error] p').id = `${uid}-error`;
  }
  return raiz;
}

// Error de grupo bajo las casillas (`texto` vacio lo quita); la casilla `nombre` (o la primera) lo referencia.
export function errorResumen(raiz, texto, nombre) {
  const caja = raiz.querySelector('[data-error]');
  const entradas = nombre ? [raiz.querySelector(`input[name="${nombre}"]`)] : [...raiz.querySelectorAll('input')];
  const id = caja.querySelector('p').id;
  caja.hidden = !texto;
  if (texto) caja.querySelector('span').textContent = texto;
  for (const entrada of entradas) {
    entrada.toggleAttribute('aria-invalid', Boolean(texto));
    if (texto) entrada.setAttribute('aria-invalid', 'true');
    const ids = (entrada.getAttribute('aria-describedby') ?? '').split(' ').filter((x) => x && x !== id);
    entrada.setAttribute('aria-describedby', [...ids, ...(texto ? [id] : [])].join(' '));
  }
}

// Aviso de informacion dentro del bloque (p. ej. texto desactualizado).
export function avisoResumen(raiz, texto) {
  const caja = raiz.querySelector('[data-aviso]');
  caja.hidden = !texto;
  caja.querySelector('.aviso-titulo').textContent = texto ?? '';
}
