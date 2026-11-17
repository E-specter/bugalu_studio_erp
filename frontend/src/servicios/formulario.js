// Piezas compartidas por las islas de acceso (<bugalu-acceso>, <bugalu-solicitud>): errores de campo, avisos y avisos por URL.
// Las islas llevan <template data-plantilla="..."> con los componentes del catalogo (PlantillasFormulario.astro); aqui solo se clonan.

const plantilla = (isla, nombre) => isla.querySelector(`template[data-plantilla="${nombre}"]`).content.cloneNode(true);

const ids = (entrada) => (entrada.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);

// Quita el error de un campo y su aria-invalid.
export function quitarError(entrada) {
  const id = `${entrada.id}-error`;
  document.getElementById(id)?.remove();
  entrada.removeAttribute('aria-invalid');
  const resto = ids(entrada).filter((i) => i !== id);
  if (resto.length) entrada.setAttribute('aria-describedby', resto.join(' '));
  else entrada.removeAttribute('aria-describedby');
}

// Pone el error bajo el campo y lo une con aria-describedby. `contenido`: texto o nodos (p. ej. un enlace).
export function ponerError(isla, entrada, contenido) {
  quitarError(entrada);
  const fragmento = plantilla(isla, 'error');
  const mensaje = fragmento.querySelector('p');
  mensaje.id = `${entrada.id}-error`;
  mensaje.querySelector('span').replaceChildren(...[].concat(contenido));
  entrada.closest('.campo').append(fragmento);
  entrada.setAttribute('aria-invalid', 'true');
  entrada.setAttribute('aria-describedby', [...ids(entrada), mensaje.id].join(' '));
}

export const limpiarAvisos = (isla) => isla.querySelector('[data-avisos]').replaceChildren();

// Titulo y texto se leen como una frase: punto tras el titulo y un espacio entre ambos (invisible en la columna flex).
export function llenarAviso(aviso, titulo, texto) {
  aviso.querySelector('.aviso-titulo').textContent = texto ? `${titulo}.` : titulo;
  const parrafo = aviso.querySelector('.aviso-texto');
  if (texto) {
    parrafo.textContent = texto;
    parrafo.before(' ');
  } else parrafo.remove();
}

// Aviso de resultado arriba del formulario. `enlaces`: [{texto, href}] (resumen de errores); `boton`: {texto, atributo} (Reintentar);
// `enlace`: {texto, href} (accion principal que navega).
export function mostrarAviso(isla, variante, titulo, texto, { enlaces, boton, enlace } = {}) {
  const fragmento = plantilla(isla, `aviso-${variante}`);
  const aviso = fragmento.querySelector('.aviso');
  llenarAviso(aviso, titulo, texto);
  const cuerpo = aviso.querySelector('.aviso-cuerpo');
  if (enlaces) {
    const lista = document.createElement('ul');
    for (const { texto: t, href } of enlaces) {
      const item = document.createElement('li');
      const enlace = document.createElement('a');
      enlace.href = href;
      enlace.textContent = t;
      item.append(enlace);
      lista.append(item);
    }
    cuerpo.append(lista);
  }
  if (boton) {
    const bloque = plantilla(isla, 'boton');
    const control = bloque.querySelector('button');
    control.textContent = boton.texto;
    control.setAttribute(boton.atributo, '');
    cuerpo.append(bloque);
  }
  if (enlace) {
    const bloque = plantilla(isla, 'enlace');
    const control = bloque.querySelector('a');
    control.textContent = enlace.texto;
    control.href = enlace.href;
    cuerpo.append(bloque);
  }
  isla.querySelector('[data-avisos]').replaceChildren(fragmento);
  return aviso;
}

// El foco ya lo lee el lector: sin rol vivo para no anunciarlo dos veces (formularios.md).
export function enfocarAviso(aviso) {
  aviso.removeAttribute('role');
  aviso.tabIndex = -1;
  aviso.focus();
}

// Lista cerrada de claves ?aviso= (estados-sistema): el texto sale de aqui, nunca de la URL.
const avisosUrl = {
  'sesion-cerrada': ['informacion', 'Cerraste sesión.'],
  'cuenta-creada': ['exito', 'Cuenta creada. Ya puedes reservar.'],
  'contrasena-cambiada': ['exito', 'Contraseña actualizada. Usa la nueva la próxima vez que inicies sesión.'],
  'textos-aceptados': ['exito', 'Listo. Ya puedes reservar.'],
  'solicitud-enviada': ['exito', 'Solicitud enviada. El Administrador la revisará; vuelve aquí para ver su estado.'],
};

// Muestra el aviso de ?aviso= si es de los `permitidos` y quita el parametro para que recargar no lo repita.
export function mostrarAvisoDeUrl(isla, permitidos) {
  const url = new URL(location.href);
  const clave = url.searchParams.get('aviso');
  if (clave === null) return;
  url.searchParams.delete('aviso');
  history.replaceState(null, '', url);
  if (!permitidos.includes(clave) || !Object.hasOwn(avisosUrl, clave)) return;
  const [variante, texto] = avisosUrl[clave];
  mostrarAviso(isla, variante, texto);
}

// Fecha del estudio: D MMM AAAA en la zona de Lima (estructura-app, formato de datos).
const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
export function formatearFecha(iso) {
  const [anio, mes, dia] = new Date(iso).toLocaleDateString('en-CA', { timeZone: 'America/Lima' }).split('-').map(Number);
  return `${dia} ${meses[mes - 1]} ${anio}`;
}
