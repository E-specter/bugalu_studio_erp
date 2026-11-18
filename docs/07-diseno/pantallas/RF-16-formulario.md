---
id: pantalla-rf-16-formulario
titulo: Pantalla — Libro de Reclamaciones, enlace y formulario público
estado: aprobado
depende_de: [RF-16, RF-17, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-pie-publico, comp-hoja-reclamacion, comp-panel, comp-campo, comp-casilla, comp-carga-archivos, comp-aviso, comp-boton]
---

# Libro de Reclamaciones: enlace y formulario

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-01, CA-02, CA-03, CA-06 (lado del consumidor), CA-10 (prellenado), CA-12 |
| Actores | Visitante y Artista/Cliente (con o sin sesión) |
| Estructura | Landing (`LayoutPublico`, [estructura de app](../patrones/estructura-app.md#landing)), con [pie público](../componentes/pie-publico.md) Completa |
| Ruta | `/libro-de-reclamaciones/`. Nada en la URL: los datos personales no viajan en ella y no hay borrador en el servidor |
| Isla | `<bugalu-reclamacion>` (nueva): formulario, [confirmación y constancia](RF-16-confirmacion-y-constancia.md) son estados de la misma vista |

## Enlace "Libro de Reclamaciones" (CA-01)

| Dónde | Cómo |
|---|---|
| Portada, textos legales, flujo de reserva y toda página con `LayoutPublico` | [Pie público](../componentes/pie-publico.md) Completa, último enlace de la fila |
| Accesos (`layouts/Acceso.astro`) | Pie público Acceso |
| App (portal y panel interno) | Pie público Acceso al final de la columna de contenido, siempre a la vista al bajar; sale del menú de la [cabecera](../componentes/cabecera-app.md) |

Texto exacto "Libro de Reclamaciones", subrayado, sin icono (el texto manda; un libro dibujado no añade nada al lector). Un clic: `href="/libro-de-reclamaciones/"`. Correos: ya en el pie de la [plantilla](../correos/plantilla.md#pie-copy-fijo).

## Recorrido

1. El consumidor llega desde el pie (o el aviso del local). Ve la hoja vacía con los datos del proveedor ya puestos.
2. Si tiene sesión de cliente, los datos de su perfil vienen escritos y puede cambiarlos.
3. Completa 1, 2 y 3, elige cómo quiere la respuesta y, si quiere, adjunta hasta 3 archivos.
4. "Revisar la hoja": si falta algo, se le dice qué y el foco va al primer campo; si no, pasa a la [confirmación](RF-16-confirmacion-y-constancia.md).

## Datos

Cuerpo: `NuevaHoja` de `POST /reclamaciones` ([contrato](../../03-requerimientos/RF-16.md#contrato-api)). Todos obligatorios salvo los marcados "(opcional)".

| Campo (etiqueta) | Dato | Control y reglas |
|---|---|---|
| NOMBRE COMPLETO | `consumidor.nombre` | Texto, `maxlength="200"`, `autocomplete="name"` |
| TIPO DE DOCUMENTO · NÚMERO DE DOCUMENTO | `consumidor.tipo_documento`, `documento` | Selector DNI · CE · Pasaporte (sin valor inicial) + Texto; formato como en [perfil](RF-17-perfil.md) (ver Preguntas) |
| DOMICILIO | `consumidor.domicilio` | Texto, `maxlength="200"`, `autocomplete="street-address"` |
| TELÉFONO (opcional) · CORREO | `consumidor.telefono`, `correo` | `tel` (`autocomplete="tel"`) + `email` (`autocomplete="email"`) |
| Soy menor de edad | `es_menor` | [Casilla](../componentes/casilla.md), sin marcar; al marcarla aparece el grupo siguiente justo debajo |
| Grupo DATOS DE TU MADRE, PADRE O TUTOR | `representante.nombre`, `domicilio`, `telefono` (opcional), `correo` | Mismos controles, `autocomplete="off"` (no es la persona que llena); solo se envía si `es_menor` |
| PRODUCTO O SERVICIO | `bien.tipo` | Casilla Radio: Servicio (marcada por defecto: el estudio vende servicios) · Producto |
| MONTO RECLAMADO EN S/ (opcional) | `bien.monto` | Importe ([campo](../componentes/campo.md) Texto, `inputmode="decimal"`), 0,01 a 999 999,99; se envía como texto decimal con punto |
| DESCRIPCIÓN (opcional) | `bien.descripcion` | Área, `maxlength="1000"` |
| TIPO | `tipo` | Casilla Radio con detalle: Reclamo · Queja (definiciones literales abajo), ninguna marcada |
| DETALLE · PEDIDO | `detalle`, `pedido` | Área, `minlength="10"`, `maxlength="3000"` |
| ADJUNTOS (opcional) | `adjuntos[]` | [Carga de archivos](../componentes/carga-archivos.md#adjuntos-de-reclamo) Adjuntos de reclamo |
| MEDIO PARA LA RESPUESTA | `medio_respuesta` | Casilla Radio con detalle: Correo electrónico (marcada) · Carta a mi domicilio |
| (trampa) | `sitio_web` | Ver Composición |

**Prellenado (CA-10):** con sesión de **cliente**, `GET /perfil` llena nombre, documento, domicilio, teléfono, correo, `es_menor` y, si hay `menor.tutor`, su nombre, teléfono y correo. La isla envía el token con el `POST` y la hoja queda en la cuenta. Sin sesión, con otro rol o si `/perfil` falla: hoja vacía, sin error.

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | Línea técnica + `<h1>` (`fuente-familia-display`, `fuente-tamano-titulo-lg`) + descripción (`fuente-tamano-lectura`) | "PASO 1 DE 2 · COMPLETA LA HOJA" · LIBRO DE RECLAMACIONES · descripción (Copy) |
| Principal | [aviso](../componentes/aviso.md) Información (solo prellenado) | Copy |
| Principal | Encabezado y proveedor de la [hoja](../componentes/hoja-reclamacion.md) Confirmación (anatomía 2 y 3) | "HOJA DE RECLAMACIÓN" · "N.º Se asigna al enviar" · FECHA de hoy · proveedor fijo como texto (no son campos) |
| Principal | `<form novalidate>` con tres [paneles](../componentes/panel.md) Base: `1` IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE · `2` IDENTIFICACIÓN DEL BIEN CONTRATADO · `3` DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR | Campos de Datos en ese orden ([formularios](../patrones/formularios.md#composición)); en 3: TIPO, DETALLE, PEDIDO, ADJUNTOS y MEDIO PARA LA RESPUESTA |
| Principal | Párrafos (`fuente-tamano-pequeno`, `color-texto-cuerpo`) | Las dos leyendas del Anexo I y la línea de privacidad |
| Principal | [Botón](../componentes/boton.md) Primario grande `arrow-right` | "Revisar la hoja": una acción, sin barra |
| Pie | [Pie público](../componentes/pie-publico.md) Completa | — |

**Campo trampa (CA-12):** `<div aria-hidden="true" class="visualmente-oculto">` con `<label>` "No completes este campo" e `<input name="sitio_web" tabindex="-1" autocomplete="off">`. Fuera de la vista y del árbol de accesibilidad, fuera del orden de teclado, pero no `display: none` (los robots lo saltarían). Su valor va en `datos.sitio_web`; la isla no lo valida.

Adaptabilidad: una columna en móvil; desde `punto-quiebre-tableta`, pares hermanos en fila (documento, teléfono + correo). Contenido a `medida-contenedor-max`, campos a `medida-linea-lectura`.

## Estados

| Situación | Forma y texto |
|---|---|
| Sin JS | `<noscript>`: aviso Información "Para llenar la hoja aquí necesitas JavaScript. También puedes presentar tu reclamo o queja por estos canales:" + canales (`ContactoEstudio`) + "Danos tu nombre, documento, domicilio, el detalle y tu pedido. Te respondemos en un máximo de 15 días hábiles." y las dos leyendas. El formulario nace `hidden` y la isla lo muestra |
| Cargando perfil | El formulario ya se ve y es usable; los campos se llenan al llegar (sin "Cargando…": no bloquea) |
| Validación local | Ver tabla siguiente; al pulsar "Revisar la hoja" con errores: aviso Error arriba del formulario, título "Revisa {n} datos antes de seguir" (1: "Revisa 1 dato…") con un enlace por error al campo, y **foco al primer campo con error** (CA-03) |
| Errores del servidor | Vuelven a este estado desde la confirmación: [envío](RF-16-confirmacion-y-constancia.md#envío) |

| Campo | Mensaje |
|---|---|
| Nombre (de consumidor o tutor) | "Escribe el nombre completo." · "El nombre admite hasta 200 caracteres." |
| Documento | "Elige el tipo de documento." · "Escribe el número de documento." · "Escribe los 8 dígitos de tu DNI." · "Escribe de 6 a 12 letras o cifras, sin espacios ni guiones." |
| Domicilio | "Escribe el domicilio." · "El domicilio admite hasta 200 caracteres." |
| Correo | "Escribe el correo." · "Escribe un correo válido, como nombre@correo.com." |
| Monto | "Escribe un monto entre S/ 0,01 y S/ 999 999,99, o déjalo vacío." |
| Descripción | "La descripción admite hasta 1000 caracteres." |
| Tipo | "Elige si es un reclamo o una queja." |
| Detalle · Pedido | "Cuenta qué pasó con al menos 10 caracteres." · "Escribe qué pides con al menos 10 caracteres." · "Admite hasta 3000 caracteres." |
| Adjuntos | "{nombre} no es PDF, JPG ni PNG. Elige otro archivo." · "{nombre} pesa más de 5 MB. Elige uno más liviano." |

## Copy

| Elemento | Texto |
|---|---|
| Descripción | "Presenta un reclamo o una queja sobre nuestros servicios. No necesitas cuenta. Te respondemos en un máximo de 15 días hábiles." |
| Línea sobre el formulario | "Todos los datos son obligatorios salvo los marcados como opcionales." |
| Aviso de prellenado | Título "Usamos los datos de tu cuenta" · "Puedes cambiarlos: valen solo para esta hoja y no tocan tu perfil. La hoja quedará en Mis reclamos." |
| Ayuda de menor | "Si tienes menos de 18 años, añade los datos de tu madre, padre o tutor." |
| Ayudas de 2 | Producto o servicio: "Lo que contrataste o quisiste contratar: una sesión, una mezcla, una asesoría." · Descripción: "Qué contrataste y cuándo. Si tienes una reserva, escribe su folio, por ejemplo R-2026-00014." · Monto: "Por ejemplo, 150,00." |
| Ayudas de 3 | Detalle: "Qué pasó, cuándo y con quién. De 10 a 3000 caracteres." · Pedido: "Qué solución esperas. De 10 a 3000 caracteres." · Adjuntos: "Comprobantes, capturas o fotos. Hasta 3 archivos PDF, JPG o PNG de 5 MB cada uno." |
| Medio (detalle) | Correo: "Te escribimos al correo de la sección 1." · Carta: "Te la llevamos al domicilio de la sección 1. Tarda más en llegar." |
| Privacidad | "Usamos estos datos solo para atender tu hoja y responderte. Más en la [Política de privacidad]." (enlace a `/legal/privacidad/`) |

### Textos del Anexo I

Transcritos del Anexo I (D.S. 011-2011-PCM, modificado por el D.S. 101-2022-PCM); son fijos y no se redactan (ver Preguntas):

- Definiciones (detalle de cada opción de TIPO y pie de la hoja): "RECLAMO: Disconformidad relacionada a los productos o servicios." · "QUEJA: Disconformidad no relacionada a los productos o servicios; o, malestar o descontento respecto a la atención al público."
- Leyendas: "La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es requisito previo para interponer una denuncia ante el INDECOPI." · "El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días hábiles improrrogables."

## Accesibilidad

- Un `<h1>`; la hoja `<h2>`; cada panel `<section>` con `<h2>`; cada grupo de radios y el del tutor en `<fieldset>` + `<legend>`. La casilla de menor lleva `aria-controls` al grupo; el grupo entra en el DOM tras ella y el foco no se mueve.
- El aviso de errores no es región viva: el foco va al primer campo, cuyo `aria-describedby` lee el error. Cada campo con `aria-invalid` mientras falle.
- Etiquetas siempre visibles; ayudas por `aria-describedby`; objetivos ≥ `medida-control-tactil` en móvil.

## Preguntas para leader

1. **Textos del Anexo I:** el RF los exige literales pero no los trae; aquí van transcritos. Pasarlos al RF (o a `docs/08-legal/`) para que el abogado los confirme junto con la vigencia del proyecto de 2026.
2. **Formato del documento y del teléfono:** CA-03 no lo fija. Propuesta: el de RF-17 (DNI 8 cifras; CE y pasaporte 6 a 12 letras o cifras) y teléfono libre hasta 20 caracteres.
3. **Sesión vencida al enviar:** el contrato no lista 401. Propuesta: la isla renueva la sesión antes del `POST`; si no puede, envía sin token y la hoja no queda en la cuenta (se dice en la constancia).
