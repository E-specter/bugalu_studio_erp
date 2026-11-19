---
id: pantalla-rf-17-textos-editor
titulo: Pantalla — Editor de textos legales (ver, prellenar, cargar Markdown y vista previa)
estado: borrador
depende_de: [RF-17, pantalla-rf-17-textos-legales, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-encabezado-pantalla, comp-panel, comp-campo, comp-boton, comp-aviso, comp-barra-acciones, comp-etiqueta-tecnica, comp-carga-archivos]
---

# Editor de textos legales

Amplía la vista del Administrador de [textos legales](RF-17-textos-legales.md#administrador-textos): lo que no se nombra aquí sigue como allí.

| Campo | Valor |
|---|---|
| Requerimiento | [RF-17](../../03-requerimientos/RF-17.md), ampliación del 2026-11-19: ver (CA-14), prellenar (CA-15), cargar archivo (CA-16) y vista previa (CA-17) |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/textos/ver?tipo=&version=` (nueva) · `/app/textos/publicar?tipo=`. La vista previa y la confirmación de carga no tienen URL |
| Isla | `<bugalu-textos-legales>`: vista nueva `ver`; `publicar` suma carga y vista previa. Sin isla nueva |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

**Decisión del brief: vista previa junto al editor, sin pestañas.** La [navegación](../patrones/estructura-app.md#navegación) no admite pestañas que oculten contenido principal, y con Escribir / Vista previa no se ve a la vez lo escrito y su resultado. Desde `punto-quiebre-escritorio`, CONTENIDO y VISTA PREVIA van en dos columnas iguales y del mismo alto; por debajo (390 incluido), VISTA PREVIA va justo bajo CONTENIDO y antes de los resúmenes, a ancho completo. Se actualiza a petición, no a cada tecla: ni una llamada por pausa ni un anuncio por cambio.

## Recorrido

1. En la lista, "Ver" en la versión vigente o programada → `/app/textos/ver`: datos y texto con su formato final. Sale por "Volver a textos" o la ruta.
2. "Publicar versión de {texto}" abre el formulario con CONTENIDO y los resúmenes de la última versión (la programada si hay; si no, la vigente). RESUMEN DE CAMBIOS llega vacío: describe el cambio nuevo.
3. Edita o pulsa "Cargar archivo .md": elige el archivo y, si CONTENIDO tenía texto, confirma el reemplazo.
4. Pulsa "Actualizar vista previa" cuando quiere ver el resultado.
5. "Revisar y publicar" abre R1 con el texto con formato final; "Publicar versión", como hoy.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Versión | `GET /textos-legales/{tipo}/versiones/{version}` → `TextoLegal` | `tipo_cambio` Mayor · Menor · Parche; `vigente_desde` y `publicado_en` `D MMM AAAA`; `resumenes` y `resumen_cambios` tal cual; `contenido_html` |
| Prellenado | `GET /textos-legales` (ya cargado por la vista) → versión de partida → su `TextoLegal` | `contenido` en CONTENIDO; `resumenes[contexto]` en su RESUMEN POR PASO. Texto sin versiones: campos vacíos |
| Archivo | `File` del input, leído en el navegador con `TextDecoder("utf-8", {fatal: true})`; nunca se envía | Sin el BOM inicial; reemplaza CONTENIDO |
| Vista previa | `POST /textos-legales/previsualizar {contenido}` → `{contenido_html}` | Pasa por el mismo saneado del navegador que la página pública |

`contenido_html` se pinta con la prosa de la [página pública](RF-17-textos-legales.md#páginas-públicas) (`fuente-tamano-lectura`, `fuente-interlineado-lectura`, `medida-linea-lectura`) y sus encabezados bajan un nivel por debajo del título que los contiene (hasta `<h6>`). En Ver, VISTA PREVIA y R1, sus enlaces abren otra pestaña (`target="_blank"`, `rel="noopener"`, "(se abre en otra pestaña)" oculto): un clic no hace perder lo escrito.

## Ver

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Inicio / Textos / {Texto} · `[A10] CONTROL / TEXTOS` · {TEXTO} · VERSIÓN 1.0.0 · "Así la leen los clientes en la página pública."; ranura `acciones`: "Volver a textos" ([botón](../componentes/boton.md) Secundario como enlace) |
| Principal | [panel](../componentes/panel.md) Base `V1 VERSIÓN` | `<dl>`: TIPO DE CAMBIO · VIGENTE DESDE (programada: [etiqueta](../componentes/etiqueta-tecnica.md) Aviso PROGRAMADA junto a la fecha) · PUBLICADA EL · RESUMEN DE CAMBIOS ("—" si no hay) |
| Principal | panel Base `V2 RESÚMENES` | Por contexto, su etiqueta de RESUMEN POR PASO y el texto |
| Principal | panel Base `V3 TEXTO` | `contenido_html` |

Sin acción principal: es lectura. Estados: carga "Cargando…" con `aria-busy` · 404 o `tipo`/`version` inválidos: [aviso](../componentes/aviso.md) Información "Esa versión ya no existe: se retiró o el enlace está mal." + "Volver a textos" · 401, 403, 503, red, no JSON: como [tarifas](RF-02-tarifas.md#estados), con "Reintentar".

## Publicar: contenido y vista previa

| Elemento (dentro de P2) | Componente (variante) | Contenido |
|---|---|---|
| Ayuda de P2 | Texto de ayuda | "Parte de la versión {1.0.0}. Cambia solo lo necesario." (sin versión previa, no se muestra) |
| Barra de CONTENIDO | Entre la ayuda y el área, en fila que se ajusta | "Cargar archivo .md": el control de [captura de pago](../componentes/carga-archivos.md#captura-de-pago) (`<label for>` con aspecto de Secundario e icono `upload`; `<input type="file" accept=".md,text/markdown">` visualmente oculto y **sin `name`**, para que no viaje con el formulario), sin Adjunto · "Actualizar vista previa" (Secundario) |
| CONTENIDO | [campo](../componentes/campo.md) Área | Prellenado. Ayuda de siempre + "Puedes cargar un archivo .md en UTF-8 de hasta 200 KB; reemplaza el contenido." |
| Confirmar reemplazo | aviso Aviso + [barra](../componentes/barra-acciones.md) Decisión, entre la barra y el área | "¿Reemplazar el contenido por {nombre.md}?" · "Se pierde lo que hay escrito en CONTENIDO." · "Mantener lo escrito" (Secundario) + "Reemplazar contenido" (Peligro) |
| VISTA PREVIA | Bloque con título técnico `<h3>` VISTA PREVIA, borde `borde-grosor-base`, desplazamiento propio | `contenido_html`; etiqueta Aviso DESACTUALIZADA junto al título si CONTENIDO cambió desde la última |

**Cargar archivo.** Al elegir, en este orden; la primera regla que falla da su error y CONTENIDO no cambia:

1. Nombre terminado en `.md` (sin distinguir mayúsculas; el tipo MIME de `.md` no es fiable): "{nombre} no es un archivo .md. Elige un archivo Markdown."
2. Hasta 200 000 bytes: "{nombre} pesa {350 KB}; el máximo es 200 KB." Así ningún archivo admitido supera los 200 000 caracteres del 422.
3. No vacío: "{nombre} está vacío."
4. UTF-8 válido: "{nombre} no está en UTF-8. Guárdalo con codificación UTF-8 y vuelve a cargarlo."
5. CONTENIDO con texto (sin contar espacios) → confirmar reemplazo; vacío → reemplaza sin preguntar.

Tras reemplazar: foco en CONTENIDO, la vista previa se actualiza sola y el input se vacía (se puede volver a elegir el mismo archivo). Los resúmenes no cambian.

| Vista previa | Forma y texto |
|---|---|
| Cuándo se genera | Al cargar el prellenado, al cargar un archivo y con "Actualizar vista previa" |
| Sin generar | "Pulsa «Actualizar vista previa» para ver el texto con su formato final." |
| CONTENIDO vacío o de más de 200 000 caracteres | Sin llamada: "Escribe el contenido para ver la vista previa." · "El contenido supera los 200 000 caracteres. Acórtalo para verlo y publicarlo." (también 422 `datos_invalidos`) |
| Actualizando | Botón en Carga "Actualizando…"; la vista anterior sigue, con `aria-busy="true"` |
| Éxito | Se pinta y se quita DESACTUALIZADA |
| 401 | Aviso Error en el bloque "Tu sesión no es válida. Inicia sesión y vuelve a intentarlo." + "Ir al acceso interno" (en otra pestaña, para no perder lo escrito) + "Reintentar" |
| 403 | Aviso Error "Tu cuenta ya no puede publicar textos." Sin reintentar |
| 503 · red · no JSON | Textos de [tarifas](RF-02-tarifas.md#estados) + "Reintentar"; la última vista previa se conserva con DESACTUALIZADA |
| Prellenado | Cargando: campos de P2 deshabilitados y "Cargando la versión {1.0.0}…" con `aria-busy`. Error: aviso Error "No pudimos cargar la versión {1.0.0} para partir de ella." + "Reintentar" |

## Revisión (R1)

"Revisar y publicar" valida como hoy (más "El contenido supera los 200 000 caracteres. Acórtalo para publicarlo.") y, si la vista previa no corresponde al CONTENIDO actual, la pide (Primario en Carga "Preparando revisión…"). R1 muestra `contenido_html` en el contenedor con desplazamiento de siempre. Si la vista previa falla, R1 no se abre: se publica solo lo que se ha visto. Aviso Error sobre el formulario con el texto de la tabla de arriba y foco en él; lo escrito se conserva.

## Accesibilidad

- Ver: `<h1>` del encabezado, V1 a V3 `<section>` con `<h2>`; el `<h2>` del texto pasa a `<h3>`. En P2, VISTA PREVIA es `<h3>` y el texto empieza en `<h4>`.
- VISTA PREVIA y el contenedor de R1: `role="region"` con `aria-labelledby` de su título y `tabindex="0"` para desplazarse con teclado; `aria-busy` mientras se actualiza. DESACTUALIZADA es texto, sin `aria-live`.
- "Cargar archivo .md": `<label for>` visible; ayuda de CONTENIDO y error en `aria-describedby` del input; el anillo de foco del label sale de `:focus-visible` del input. El error va en `role="alert"`, bajo la barra.
- Confirmar reemplazo: al aparecer, foco al título del aviso (`tabindex="-1"`); "Mantener lo escrito" devuelve el foco a "Cargar archivo .md"; "Reemplazar contenido", a CONTENIDO.
- La región `role="status"` de la isla anuncia solo "Vista previa actualizada." al terminar cada actualización, "Contenido reemplazado por {nombre}." y los errores de la vista previa; nada mientras se escribe.
- "Ver" con objeto en el nombre accesible: "Ver versión 1.0.0 de Términos de uso". Controles de al menos `medida-control-tactil` de alto.

## Pendientes

- **leader:** RF-17 tenía ya un CA-14 (casos de rotura) y la ampliación numera CA-14 a CA-17: hay dos CA-14. Proponemos renumerar la ampliación como CA-15 a CA-18.
- **leader:** con una versión programada, publicar da siempre 409 `version_programada`, así que prellenar desde ella no sirve hoy. Proponemos "Publicar versión de {texto}" deshabilitado con el motivo "Retira la versión programada para publicar otra."
- **leader:** 200 KB se toma como 200 000 bytes (encaja con el límite de 200 000 caracteres). Confirmar.
- Informativo: `GET /textos-legales` solo trae la vigente y la programada, así que "Ver" no llega a versiones anteriores; harían falta `GET /textos-legales/{tipo}/versiones` y otra columna.
- **disenador-ui:** si el control de carga sin adjunto se repite, pasarlo a una variante de [carga de archivos](../componentes/carga-archivos.md).
