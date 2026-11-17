// Llena la hoja del Libro de Reclamaciones (ficha hoja-reclamacion.md) que la isla clona del <template> de HojaReclamacion.astro.
// Una funcion, cuatro vistas: confirmacion, constancia y consulta (cliente o Administrador).
import { soles, fechaDe, horaDe, diaMesAnio } from './formatos.js';

// Textos fijos del Anexo I (D.S. 011-2011-PCM, mod. D.S. 101-2022-PCM): los confirma el abogado antes de produccion.
export const PROVEEDOR = { razon_social: 'Aural Perú E.I.R.L.', ruc: '20615656128', domicilio: 'Av. Javier Prado Este 5920, La Molina, Lima' };
export const DEFINICIONES = {
  reclamo: 'RECLAMO: Disconformidad relacionada a los productos o servicios.',
  queja: 'QUEJA: Disconformidad no relacionada a los productos o servicios; o, malestar o descontento respecto a la atención al público.',
};
export const LEYENDAS = [
  'La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es requisito previo para interponer una denuncia ante el INDECOPI.',
  'El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días hábiles improrrogables.',
];

const MB = 1048576;
export const tamanoArchivo = (bytes) => (bytes < MB ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${String(Number((bytes / MB).toFixed(1))).replace('.', ',')} MB`);
// `tipo` de la API (MIME o corto) o del File -> [rotulo, tipo del componente Archivo].
export const tipoArchivo = (tipo = '') => (/pdf/i.test(tipo) ? ['PDF', 'pdf'] : /png/i.test(tipo) ? ['PNG', 'imagen'] : ['JPG', 'imagen']);

const DOCUMENTOS = { dni: 'DNI', ce: 'CE', pasaporte: 'Pasaporte' };
const MEDIOS = { correo: 'Correo electrónico', carta: 'Carta al domicilio' };
export const TIPOS = { reclamo: 'Reclamo', queja: 'Queja' };
const SIN = '—';
export const fechaHora = (iso) => `${diaMesAnio(fechaDe(iso))}, ${horaDe(iso)}`;

let contador = 0;

function fila(lista, rotulo, valor, ancho = false) {
  const div = document.createElement('div');
  if (ancho) div.className = 'hoja-ancho';
  const dt = Object.assign(document.createElement('dt'), { textContent: rotulo });
  const dd = Object.assign(document.createElement('dd'), { textContent: valor || SIN });
  div.append(dt, dd);
  lista.append(div);
  return dd;
}

function pintarCopia(nodo) {
  nodo.textContent = `Copia impresa desde ${location.host} el ${fechaHora(new Date().toISOString())}`;
}
// La fecha de la copia es la de imprimir, no la de pintar.
if (typeof addEventListener === 'function') addEventListener('beforeprint', () => document.querySelectorAll('[data-copia]').forEach(pintarCopia));

// `hoja`: Hoja de la API o, en la confirmacion, lo escrito con la forma de NuevaHoja (sin numero). `variante`: confirmacion | constancia | consulta.
// Los adjuntos se abren (enlaces con `data-adjunto`) solo para el Administrador en la consulta; la isla atiende el clic.
export function pintarHoja(isla, hoja, { variante = 'consulta', administrador = false, hoy = new Date().toISOString() } = {}) {
  const raiz = isla.querySelector('template[data-plantilla-hoja]').content.firstElementChild.cloneNode(true);
  const uid = `hoja-${++contador}`;
  const q = (s) => raiz.querySelector(s);
  const titulo = q('.hoja-titulo');
  titulo.id = `${uid}-titulo`;
  raiz.setAttribute('aria-labelledby', titulo.id);
  raiz.querySelectorAll('section[aria-labelledby]').forEach((s) => {
    const h = s.querySelector('h3');
    h.id = `${uid}-${h.id}`;
    s.setAttribute('aria-labelledby', h.id);
  });
  raiz.dataset.variante = variante;
  const proveedor = hoja.proveedor ?? PROVEEDOR;
  const registrada = Boolean(hoja.numero);

  // Encabezado
  if (registrada) q('[data-numero]').textContent = hoja.numero;
  else q('[data-numero-rotulo]').remove();
  q('[data-sin-numero]').hidden = registrada;
  const fisica = hoja.origen === 'libro_fisico';
  const etiqueta = q('[data-transcrita]');
  if (fisica) etiqueta.querySelector('.etiqueta > span:last-child').textContent = `TRANSCRITA DEL LIBRO FÍSICO · HOJA ${hoja.numero_hoja_fisica ?? ''}`.trim().toUpperCase();
  else etiqueta.remove();
  const tiempo = q('[data-fecha]');
  const original = fisica && hoja.fecha_original;
  if (registrada || original) {
    const iso = original || hoja.creada_en;
    tiempo.textContent = fechaHora(iso);
    tiempo.dateTime = iso;
  } else {
    tiempo.textContent = `${diaMesAnio(fechaDe(hoy))} · la hora se fija al enviar`;
    tiempo.dateTime = fechaDe(hoy);
  }

  // Proveedor
  q('[data-proveedor="razon"]').textContent = proveedor.razon_social;
  q('[data-proveedor="ruc"]').textContent = proveedor.ruc;
  q('[data-proveedor="domicilio"]').textContent = proveedor.domicilio;

  // 1. Consumidor
  const c = hoja.consumidor;
  const s1 = q('[data-seccion="1"]');
  fila(s1, 'Nombre completo', c.nombre);
  fila(s1, 'Documento', `${DOCUMENTOS[c.tipo_documento] ?? c.tipo_documento} ${c.documento}`);
  fila(s1, 'Domicilio', c.domicilio);
  fila(s1, 'Teléfono', c.telefono);
  fila(s1, 'Correo', c.correo);
  if (hoja.es_menor) {
    fila(s1, 'Menor de edad', 'Sí');
    const r = hoja.representante ?? {};
    fila(s1, 'Madre, padre o tutor', r.nombre);
    fila(s1, 'Domicilio del tutor', r.domicilio);
    fila(s1, 'Teléfono del tutor', r.telefono);
    fila(s1, 'Correo del tutor', r.correo);
  }

  // 2. Bien contratado
  const s2 = q('[data-seccion="2"]');
  fila(s2, 'Producto o servicio', hoja.bien.tipo === 'producto' ? 'Producto' : 'Servicio');
  fila(s2, 'Monto reclamado', hoja.bien.monto ? soles(hoja.bien.monto) : SIN);
  fila(s2, 'Descripción', hoja.bien.descripcion, true).classList.add('hoja-texto');

  // 3. Detalle y pedido
  const s3 = q('[data-seccion="3"]');
  fila(s3, 'Tipo', TIPOS[hoja.tipo] ?? 'Sin marcar');
  fila(s3, 'Medio para la respuesta', MEDIOS[hoja.medio_respuesta]);
  fila(s3, 'Detalle', hoja.detalle, true).classList.add('hoja-texto');
  fila(s3, 'Pedido', hoja.pedido, true).classList.add('hoja-texto');
  const adjuntos = hoja.adjuntos ?? [];
  const lista = q('[data-adjuntos]');
  q('[data-adjuntos-caja]').hidden = !adjuntos.length;
  const abre = administrador && variante === 'consulta';
  for (const a of adjuntos) {
    const [rotulo] = tipoArchivo(a.tipo);
    const nodo = q(`template[data-archivo="${abre ? 'abrir' : 'sin'}"]`).content.firstElementChild.cloneNode(true);
    const li = document.createElement('li');
    nodo.querySelector('.archivo-nombre').textContent = a.nombre;
    nodo.querySelector('.archivo-nombre').title = a.nombre;
    nodo.querySelector('.archivo-metadato').textContent = `${rotulo} · ${tamanoArchivo(a.tamano)}`;
    if (abre) {
      const enlace = nodo.querySelector('.archivo-enlace');
      enlace.firstChild.textContent = `Abrir ${a.nombre}`;
      enlace.dataset.adjunto = a.n;
    }
    li.append(nodo);
    lista.append(li);
  }

  // 4. Respuesta (solo hojas registradas, en consulta)
  if (variante !== 'consulta') q('[data-seccion-4]').remove();
  else if (hoja.respuesta) {
    const r = hoja.respuesta;
    const dl = q('[data-seccion="4"]');
    q('[data-sin-respuesta]').remove();
    fila(dl, 'Fecha de comunicación de la respuesta', fechaHora(r.enviada_en));
    fila(dl, 'Medio', MEDIOS[r.medio]);
    if (r.referencia_carta) fila(dl, 'Referencia de la carta', r.referencia_carta);
    if (administrador && r.respondida_por) fila(dl, 'Respondió', r.respondida_por.nombre);
    fila(dl, 'Respuesta', r.texto, true).classList.add('hoja-texto');
  } else {
    q('[data-seccion="4"]').remove();
    q('[data-plazo]').textContent = `Plazo de respuesta: hasta el ${diaMesAnio(fechaDe(hoja.vence_respuesta))}`;
  }

  // Pie
  pintarCopia(q('[data-copia]'));
  return raiz;
}
