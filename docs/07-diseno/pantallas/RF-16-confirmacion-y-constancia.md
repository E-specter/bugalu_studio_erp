---
id: pantalla-rf-16-confirmacion-y-constancia
titulo: Pantalla — Libro de Reclamaciones, confirmación, envío y constancia
estado: borrador
depende_de: [RF-16, pantalla-rf-16-formulario, diseno-brief, patron-formularios, patron-estados-sistema, comp-hoja-reclamacion, comp-barra-acciones, comp-aviso, comp-boton, comp-carga-archivos]
---

# Confirmación, envío y constancia

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-04, CA-05, CA-06 (rechazo de adjuntos), CA-12 (429), CA-13 |
| Actores | Visitante y Artista/Cliente |
| Estructura | Landing, la misma página del [formulario](RF-16-formulario.md) |
| Ruta | `/libro-de-reclamaciones/` (sin cambios de URL: confirmación y constancia son estados de la vista, como la revisión de [textos legales](RF-17-textos-legales.md#administrador-textos)) |
| Isla | `<bugalu-reclamacion>` |

## Recorrido

1. Desde el formulario válido, "Revisar la hoja" oculta el formulario (no lo borra) y muestra la hoja completa en modo lectura.
2. "Corregir datos" vuelve al formulario con todo lo escrito y los adjuntos.
3. "Enviar reclamación" registra la hoja (`POST /reclamaciones`, `multipart/form-data`: `datos` = `NuevaHoja` con `confirmado: true`, y `adjuntos[]`).
4. Con el 201, ve la constancia: número, fecha y hora, la hoja y "Imprimir o guardar en PDF". Recargar vuelve a la hoja vacía: la copia queda en su correo y, con sesión, en [Mis reclamos](RF-16-mis-reclamos.md).

## Composición

| Estado | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Confirmación | Encabezado | Línea técnica + `<h1>` | "PASO 2 DE 2 · CONFIRMA" · LIBRO DE RECLAMACIONES |
| Confirmación | Principal | `<h2>` + párrafo | "REVISA TU HOJA" + texto (Copy) |
| Confirmación | Principal | [hoja](../componentes/hoja-reclamacion.md) Confirmación | Lo escrito, en el orden del Anexo I; adjuntos con nombre y metadato ("PDF · 1,2 MB") |
| Confirmación | Principal | [barra de acciones](../componentes/barra-acciones.md) Formulario, botones **grandes los dos** | "Corregir datos" (Secundario) + "Enviar reclamación" (Primario). Mismo tamaño y alto: corregir es tan fácil como enviar ([formularios](../patrones/formularios.md#prevención-de-errores)). En móvil, Móvil: apilados a ancho completo, el Primario arriba |
| Constancia | Encabezado | Línea técnica + `<h1>` | "HOJA REGISTRADA" · LIBRO DE RECLAMACIONES |
| Constancia | Principal | [aviso](../componentes/aviso.md) Éxito | Copy; `role="status"` |
| Constancia | Principal | Botones en fila (hueco `espacio-3`; apilados en móvil) | Primario "Imprimir o guardar en PDF" (`<button>`, `window.print()`) + Secundario como enlace: "Ver mis reclamos" (`/app/reclamos/`, si la hoja quedó en una cuenta) o "Volver al inicio" (`/`) |
| Constancia | Principal | hoja Constancia | `Hoja` devuelta: número, `creada_en`, proveedor, secciones 1 a 3, adjuntos, definiciones y leyendas |

Los botones van **antes** de la hoja para que no queden al final de una página larga. Todo lo que no es la hoja lleva `data-no-imprimir`.

## Impresión

Se imprime **solo la hoja** con las reglas de la [ficha](../componentes/hoja-reclamacion.md#impresión): encabezado con "HOJA DE RECLAMACIÓN N.º {numero}", fecha y hora, proveedor, secciones 1 a 3, nombres de los adjuntos, definiciones, leyendas y la línea "Copia impresa desde…". Se ocultan cabecera, línea técnica, `<h1>`, aviso, botones y pie. "Guardar en PDF" es el destino del diálogo de impresión del navegador; no se genera PDF en el servidor.

## Envío

| Respuesta | Dónde queda | Forma y texto |
|---|---|---|
| Enviando | Confirmación | Primario en Carga "Enviando…"; "Corregir datos" deshabilitado. A los 10 s, bajo la barra (región `role="status"`): con adjuntos "Subiendo los adjuntos, puede tardar un minuto."; sin ellos "Seguimos registrando tu hoja…" |
| 201 | Constancia | Foco al aviso Éxito |
| 409 `confirmacion_requerida` | Confirmación | Aviso Error "No pudimos registrar la hoja" · "Vuelve a pulsar «Enviar reclamación»." |
| 413 `adjunto_muy_grande` | Formulario | El [archivo](../componentes/archivo.md) señalado en estado Error: "{nombre} pesa más de 5 MB. Quítalo o elige uno más liviano." |
| 422 `adjunto_no_permitido` | Formulario | Ídem: "{nombre} no es un PDF, JPG o PNG válido. Quítalo para enviar la hoja sin él." (CA-06) |
| 422 `demasiados_adjuntos` | Formulario | Error de ADJUNTOS: "Puedes adjuntar hasta 3 archivos. Quita los que sobran." |
| 422 `datos_invalidos` | Formulario | Error bajo el campo de `detalles.campo` (ruta del dato, p. ej. `consumidor.correo`) con el texto del [formulario](RF-16-formulario.md#estados); sin campo, aviso Error con el `mensaje` |
| 429 `demasiadas_solicitudes` | Confirmación | Aviso Error "Demasiados envíos desde tu conexión" · "Recibimos muchas hojas desde tu conexión en la última hora. Tus datos siguen aquí: inténtalo más tarde o preséntala por estos canales:" + canales |
| 503 | Confirmación | Aviso Error "El Libro de Reclamaciones no responde" · "No pudimos registrar tu hoja. Tus datos siguen aquí: inténtalo en unos minutos o preséntala por estos canales:" + canales |
| Red caída | Confirmación | Aviso Error "Sin conexión" · "No sabemos si tu hoja llegó. Si en unos minutos no recibes la constancia en tu correo, vuelve a enviarla: tus datos siguen aquí." |
| No JSON u otro | Confirmación | Aviso Error "Algo salió mal" · "No pudimos registrar tu hoja. Tus datos siguen aquí: inténtalo de nuevo o preséntala por estos canales:" + canales |

- Canales: los de `ContactoEstudio` (correo, WhatsApp y en persona), dentro del aviso.
- Errores que vuelven al formulario: se muestra el formulario con el aviso Error de resumen y el foco va al primer campo con error o, si es un adjunto, a su "Quitar". Si `detalles` no dice qué adjunto, el error va al grupo ADJUNTOS: "Uno de los adjuntos no se aceptó (más de 5 MB o no es PDF, JPG ni PNG). Quítalo o cámbialo."
- Errores que se quedan en la confirmación: foco al aviso; "Enviar reclamación" sigue disponible. Nunca se reintenta solo (evita hojas repetidas).

## Copy

| Elemento | Texto |
|---|---|
| Confirmación | "Así quedará registrada. Si algo no está bien, corrígelo ahora: una vez enviada no se puede cambiar." |
| Aviso de constancia | Título "Registramos tu hoja N.º {numero}" · "Te enviamos una copia a {correo}. Te responderemos por {correo electrónico \| carta a tu domicilio} a más tardar el {vence_respuesta, D MMM AAAA}. Guarda o imprime esta constancia antes de salir." + con cuenta: "También la encuentras en Mis reclamos." |
| `document.title` | "Paso 1 de 2 · Libro de Reclamaciones" · "Paso 2 de 2: confirma · Libro de Reclamaciones" · "Hoja N.º {numero} registrada · Libro de Reclamaciones" |

## Accesibilidad

- Al pasar a la confirmación, foco al `<h2>` REVISA TU HOJA (`tabindex="-1"`) y desplazamiento arriba; al volver con "Corregir datos", foco al `<h1>`.
- En la constancia, foco al aviso Éxito (con anillo, [estados comunes](../componentes/README.md#estados-comunes)); el número se lee completo.
- La región `role="status"` del envío existe desde la carga; los avisos de error reciben el foco, no se anuncian dos veces.
- El orden de la barra en el DOM es Corregir → Enviar en escritorio; en móvil el Primario va arriba solo con `order`, sin cambiar el orden de foco ([barra de acciones](../componentes/barra-acciones.md#accesibilidad)).

## Preguntas para leader

1. **dev-backend:** en 413 y 422 de adjuntos, ¿`detalles` dice cuál (`n`, en el orden de `adjuntos[]`)? Propuesta: `detalles: {adjunto: n}`. Sin él, el error va al grupo.
2. **dev-backend:** el 201 aparente del campo trampa, ¿qué cuerpo trae? La isla pinta la constancia con lo que llegue; si falta `numero`, solo el aviso sin número.
