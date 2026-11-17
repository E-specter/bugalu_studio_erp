---
id: pantalla-rf-16-transcribir
titulo: Pantalla — Transcribir hoja del libro físico (Administrador)
estado: borrador
depende_de: [RF-16, pantalla-rf-16-formulario, pantalla-rf-16-confirmacion-y-constancia, pantalla-rf-16-bandeja, diseno-brief, patron-formularios, patron-estados-sistema, comp-hoja-reclamacion, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-aviso, comp-boton, comp-encabezado-pantalla]
---

# Transcribir hoja del libro físico

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-09 |
| Actores | Administrador |
| Estructura | App, panel interno |
| Ruta | `/app/reclamos/transcribir` (nada en la URL) |
| Isla | `<bugalu-reclamacion transcripcion>`: el mismo formulario del [público](RF-16-formulario.md), con los cambios de abajo |

## Recorrido

1. Cuando la plataforma no funcionó, el consumidor llenó el Libro de Reclamaciones de Respaldo. Dentro de 1 día calendario, el Administrador abre la [bandeja](RF-16-bandeja.md) → "Transcribir hoja del libro físico".
2. Copia la hoja tal cual: número de la hoja física, fecha y hora originales y los datos del Anexo I.
3. La revisa y la registra; llega al detalle de la hoja nueva con `?aviso=hoja-transcrita`, desde donde la responde como cualquier otra.

## Datos

`POST /reclamaciones/transcripcion` con `NuevaHoja` (`confirmado: true`, sin `sitio_web`) + `{fecha_original, numero_hoja_fisica}` → 201 `Hoja`. JSON, sin adjuntos.

| Campo | Dato | Control y reglas |
|---|---|---|
| NÚMERO DE LA HOJA FÍSICA | `numero_hoja_fisica` | Texto, obligatorio, tal como está impreso en la hoja |
| FECHA ORIGINAL · HORA ORIGINAL | `fecha_original` | `date` (`max` = hoy) + `time` (`step="60"`), obligatorias; se envían como ISO con la zona de Lima |
| Secciones 1, 2 y 3 | `NuevaHoja` | Los campos y reglas del [formulario](RF-16-formulario.md#datos), sin prellenado ni campo trampa |
| TIPO | `tipo` | Radio con una tercera opción "Sin marcar en la hoja física" (`null`): la hoja se tramita según su contenido (CA-03) |
| ADJUNTOS | — | No se ofrecen: el contrato no los recibe (ver Preguntas) |
| MEDIO PARA LA RESPUESTA | `medio_respuesta` | Sin valor por defecto: se copia el que marcó el consumidor |

## Composición

| Estado | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Formulario | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; acción Secundario como enlace "Volver a reclamos" |
| Formulario | Principal | [panel](../componentes/panel.md) `T0 HOJA FÍSICA` | NÚMERO DE LA HOJA FÍSICA + FECHA y HORA ORIGINALES en una fila; [aviso](../componentes/aviso.md) Aviso si la fecha original tiene más de 1 día (Copy) |
| Formulario | Principal | Paneles `1`, `2`, `3` del [formulario](RF-16-formulario.md#composición) | Mismo orden y textos; las leyendas no se repiten (las imprimió la hoja física) |
| Formulario | Principal | [Botón](../componentes/boton.md) Primario | "Revisar la hoja" |
| Revisión | Principal | [hoja](../componentes/hoja-reclamacion.md) Confirmación con la etiqueta TRANSCRITA y la fecha original | Lo escrito, en lectura |
| Revisión | Principal | [barra](../componentes/barra-acciones.md) Formulario | "Corregir datos" (Secundario) + Primario "Registrar hoja" |

Irreversible como la del consumidor (las hojas no se editan), así que la revisión es la misma que la [confirmación pública](RF-16-confirmacion-y-constancia.md#composición), con otro botón.

## Estados

| Situación | Forma y texto |
|---|---|
| Validación local | La del [formulario](RF-16-formulario.md#estados) + "Escribe el número de la hoja física." · "Elige la fecha original." · "Elige la hora original." · "La fecha original no puede ser futura." · "Elige qué marcó el consumidor como medio de respuesta." Aviso de resumen y foco al primer campo con error |
| Enviando | Primario en Carga "Registrando…"; "Corregir datos" deshabilitado |
| 422 | Bajo el campo de `detalles.campo`; si no, aviso Error con el `mensaje`. Vuelve al formulario con lo escrito |
| 401 · 403 · 503 · red · no JSON · sin JS | Como en la [bandeja](RF-16-bandeja.md#estados); al enviar, sin "Reintentar" y con lo escrito conservado |
| Éxito | `/app/reclamos/detalle?id={id}&aviso=hoja-transcrita` "Hoja transcrita con el N.º {numero}. El plazo de respuesta cuenta desde la fecha original: vence el {D MMM AAAA}." |

## Copy

| Elemento | Texto |
|---|---|
| Ruta e índice | Inicio / Reclamos / Transcribir · `[A12] CONTROL / RECLAMOS` |
| Título y descripción | TRANSCRIBIR HOJA · "Copia aquí, tal cual, una hoja del libro de respaldo. Recibe un número de la app y su plazo cuenta desde la fecha original." |
| Aviso de más de 1 día | Título "Esta hoja tiene más de 1 día" · "El reglamento pide transcribirla dentro de 1 día calendario. Regístrala igual: el plazo de respuesta ya corre desde el {D MMM AAAA}." |
| Ayuda de T0 | "La fecha y la hora en que el consumidor llenó la hoja, no las de hoy." |

## Accesibilidad

- Igual que el [formulario](RF-16-formulario.md#accesibilidad) y la [confirmación](RF-16-confirmacion-y-constancia.md#accesibilidad); el aviso de más de 1 día es estático (aparece al salir de la fecha, sin región viva) y no bloquea.

## Preguntas para leader

1. **Adjuntos de la hoja física:** ¿se suben fotos de la hoja manuscrita? Sería la prueba de que la transcripción es fiel. El contrato no recibe adjuntos en `/transcripcion`; propuesta: aceptar `multipart` como el público, con la foto de la hoja.
