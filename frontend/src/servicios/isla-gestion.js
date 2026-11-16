// Base de las islas de gestion del Administrador (<bugalu-franjas>, <bugalu-tarifas>): carga por vista, estados del sistema
// (carga, 401, 403, error con Reintentar), envios con carga y bloqueo, validacion con resumen y avisos por URL.
// La subclase define un metodo por vista (this[vista]() devuelve el texto del anuncio o null), `alEnviar(formulario)` y,
// opcionalmente, `iniciar()`, `errorEnvio(error)` (true = ya lo trato) y `noEncontrada` ([titulo, texto]).
import { ponerError, mostrarAviso, enfocarAviso, limpiarAvisos, llenarAviso } from './formulario.js';

const textos = {
  'no-autenticado': ['Tu sesión no es válida', 'Inicia sesión para continuar.'],
  'sin-permiso': ['No tienes permiso', 'Esta sección es solo para el Administrador.'],
};

export const mensajeError = (e) =>
  e.estado === 0 ? ['Sin conexión', 'Revisa tu red y vuelve a intentarlo.']
  : e.estado === 503 ? ['El servicio no responde', 'Inténtalo de nuevo en unos minutos.']
  : ['Algo salió mal', 'Inténtalo de nuevo.'];

const limpio = (texto) => texto.replace(/\s+/g, ' ').trim();

// Un clon de plantilla repite ids de campo: los vuelve unicos con un sufijo y reapunta label, ayudas y errores.
export function hacerUnico(nodo, sufijo) {
  const nuevos = new Map();
  nodo.querySelectorAll('[id]').forEach((e) => {
    nuevos.set(e.id, `${e.id}-${sufijo}`);
    e.id = nuevos.get(e.id);
  });
  nodo.querySelectorAll('label[for]').forEach((l) => nuevos.has(l.htmlFor) && (l.htmlFor = nuevos.get(l.htmlFor)));
  nodo.querySelectorAll('[aria-describedby]').forEach((e) => e.setAttribute('aria-describedby', e.getAttribute('aria-describedby').split(' ').map((i) => nuevos.get(i) ?? i).join(' ')));
}

export class IslaGestion extends HTMLElement {
  vista = '';
  avisosUrl = {}; // lista cerrada de claves ?aviso= -> [titulo, texto?]
  noEncontrada = ['No encontramos esto', 'Puede que el enlace esté mal escrito.'];

  connectedCallback() {
    this.vista = this.getAttribute('vista');
    this.avisoDeUrl();
    this.addEventListener('click', (e) => e.target.closest('[data-reintentar]') && this.cargar(true));
    this.addEventListener('submit', (e) => {
      e.preventDefault();
      this.alEnviar(e.target);
    });
    // Volver con "Atrás" restaura la página desde la caché con los botones en "…ando": se recarga la vista.
    addEventListener('pageshow', (e) => e.persisted && this.ocupado && this.cargar());
    this.iniciar?.();
    this.cargar();
  }

  // Muestra el aviso de ?aviso= si es de la lista cerrada y quita el parametro para que recargar no lo repita.
  avisoDeUrl() {
    const url = new URL(location.href);
    const clave = url.searchParams.get('aviso');
    if (clave === null) return;
    url.searchParams.delete('aviso');
    history.replaceState(null, '', url);
    if (Object.hasOwn(this.avisosUrl, clave)) enfocarAviso(mostrarAviso(this, 'exito', ...this.avisosUrl[clave]));
  }

  mostrar(estado) {
    const plantilla = this.querySelector(`template[data-estado="${estado}"]`);
    this.querySelector('[data-salida]').replaceChildren(plantilla.content.cloneNode(true));
    const [titulo, texto] = (estado === 'no-encontrada' ? this.noEncontrada : textos[estado]) ?? [];
    const aviso = this.querySelector('[data-salida] .aviso');
    if (aviso && titulo) llenarAviso(aviso, titulo, texto);
    if (estado === 'no-autenticado') this.querySelector('.aviso-accion').href = `/acceso/interno?${new URLSearchParams({ volver: location.pathname + location.search })}`;
  }

  // Foco al titulo del panel (tabindex -1) para no caer en <body> al sustituirse el contenido.
  enfocar() {
    const titulo = this.querySelector('[data-salida] .panel-titulo');
    titulo.tabIndex = -1;
    titulo.focus();
  }

  anunciar(texto) {
    this.querySelectorAll('[data-salida] .aviso[role]').forEach((e) => e.removeAttribute('role'));
    this.querySelector('[data-anuncio]').textContent = texto ?? limpio(this.querySelector('[data-salida] .aviso')?.textContent ?? '');
  }

  // La region viva estable anuncia el estado una sola vez: el aviso clonado pierde su rol vivo.
  async cargar(reintento = false) {
    this.querySelector('[data-anuncio]').textContent = '';
    this.querySelectorAll('[data-avisos] .aviso-error').forEach((a) => a.remove());
    this.mostrar('cargando');
    let texto = null;
    try {
      texto = await this[this.vista]();
    } catch (error) {
      this.fallo(error);
    }
    this.anunciar(texto);
    if (reintento) this.enfocar();
  }

  // 401 y 403 sustituyen el bloque; el resto es un error con Reintentar.
  fallo(error) {
    if (error.estado === 401) this.mostrar('no-autenticado');
    else if (error.estado === 403) this.mostrar('sin-permiso');
    else {
      this.mostrar('error');
      llenarAviso(this.querySelector('[data-salida] .aviso'), ...mensajeError(error));
    }
  }

  sustituir(estado) {
    this.mostrar(estado);
    this.anunciar();
    this.enfocar();
  }

  encabezado(descripcion, ruta) {
    const texto = document.querySelector('.encabezado-descripcion');
    if (texto && descripcion) texto.textContent = descripcion;
    const actual = document.querySelector('.encabezado-ruta [aria-current="page"]');
    if (actual && ruta) actual.textContent = ruta;
  }

  // --- Validacion: errores bajo cada campo y resumen con enlaces (formularios.md); foco al aviso ---

  // errores: [{entrada, mensaje, texto}] (texto = nombre del campo en el resumen). Devuelve true si no hay errores.
  validar(errores, unidad = ['campo', 'campos']) {
    limpiarAvisos(this);
    if (!errores.length) return true;
    errores.forEach(({ entrada, mensaje }) => ponerError(this, entrada, mensaje));
    const n = errores.length;
    enfocarAviso(mostrarAviso(this, 'error', `Revisa ${n} ${unidad[n === 1 ? 0 : 1]}`, '', { enlaces: errores.map((e) => ({ texto: e.texto, href: `#${e.entrada.id}` })) }));
    return false;
  }

  // Texto de la etiqueta de un campo, sin el " (obligatorio)".
  etiqueta(entrada) {
    return this.querySelector(`label[for="${entrada.id}"]`).childNodes[0].textContent.trim();
  }

  // --- Envio: carga en el boton, el resto de envios bloqueados, y respuestas ---

  get ocupado() {
    return this.querySelector('[data-envio][aria-busy]') !== null;
  }

  bloquear(si) {
    this.querySelectorAll('[data-envio]:not([aria-disabled="true"])').forEach((b) => (b.disabled = si));
  }

  // `accion` llama a la API; `alExito(resultado)` recarga o navega (`navega`: true si siempre navega). Los errores 401/403 sustituyen la vista; los demas, `errorEnvio` o aviso.
  async enviar(boton, carga, accion, alExito, navega = false) {
    if (this.ocupado) return;
    const original = boton.innerHTML;
    this.bloquear(true);
    boton.setAttribute('aria-busy', 'true');
    boton.textContent = carga;
    const soltar = () => {
      this.bloquear(false);
      boton.removeAttribute('aria-busy');
      boton.innerHTML = original;
    };
    let resultado;
    try {
      resultado = await accion();
    } catch (error) {
      soltar();
      if (error.estado === 401 || error.estado === 403) return this.sustituir(error.estado === 401 ? 'no-autenticado' : 'sin-permiso');
      if (this.errorEnvio?.(error)) return;
      enfocarAviso(mostrarAviso(this, 'error', ...(error.estado === 422 && error.mensaje ? [error.mensaje] : mensajeError(error))));
      return;
    }
    // Con `navega`, el boton sigue bloqueado hasta salir de la pantalla (evita un segundo envio); solo se suelta si falla.
    if (!navega) soltar();
    try {
      await alExito(resultado);
    } catch (error) {
      if (navega) soltar();
      this.fallo(error);
      this.anunciar();
    }
  }
}
