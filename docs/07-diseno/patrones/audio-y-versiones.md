---
id: patron-audio-y-versiones
titulo: Patrón — Audio, versiones y revisión
estado: borrador
depende_de: [comp-reproductor, comp-comentario, comp-carga-archivos]
---

# Audio, versiones y revisión

Núcleo del producto ("Adiós a los archivos perdidos en WhatsApp", `48:190`). Origen: carga y validación de WAV (`161:1750`), preparar y publicar versión (`161:1986`), centro de revisiones (`161:2241`), detalle de versión (`145:3381`), revisión y comentarios (`145:3617`), historial (`145:3868`) y versión aprobada (`145:4170`). Flujo de dominio: [versionado y feedback](../../02-dominio/flujos/versionado-feedback.md).

## Cadena de señal

Las vistas del personal muestran el proceso como cadena: `ENTRADA WAV → VALIDACIÓN → PUBLICACIÓN`, con [etiquetas](../componentes/etiqueta-tecnica.md) en cada nodo y un conector textual. Sirve de orientación ("dónde está este archivo") y se repite en carga y publicación.

## Carga y publicación (personal)

1. [Carga de archivos](../componentes/carga-archivos.md) Entregable de audio en el área principal.
2. Panel lateral de transformación: formato de salida para el artista, opciones (casillas), destino (proyecto y ruta) y acción "Publicar versión".
3. Publicar es irreversible para el artista (recibe aviso): confirmación según [formularios](formularios.md#prevención-de-errores).

## Revisión (artista y personal)

```
encabezado: índice ── etiqueta de ronda + acción
reproductor (Revisión) con marcadores
┌ hilo de comentarios (≈70) ┐ ┌ panel de comentario ┐
│ comentario …              │ │ vinculación temporal│
│                           │ │ campo + contador    │
│                           │ │ adjunto · enviar    │
│                           │ │ cierre de ronda     │
└───────────────────────────┘ └─────────────────────┘
indicador de estado (Barra): estado de la revisión · fecha límite
```

1. El [reproductor](../componentes/reproductor.md) va arriba y ocupa todo el ancho.
2. Comentar: el formulario toma el tiempo actual del reproductor ("Vincular a 2:14"), que se puede desmarcar para un comentario general.
3. Cada [comentario](../componentes/comentario.md) con marca temporal aparece como marcador en la onda; activar uno lleva al otro.
4. **Cierre de ronda:** acción explícita del artista ("Enviar observaciones" o "Aprobar versión") con texto que explica que los cambios no son diarios y entran en la siguiente versión (`23:2`).

## Historial y comparación

Lista de [tarjetas de versión](../componentes/tarjeta-version.md) Historial, de la más reciente a la más antigua; marcar dos habilita "Comparar" → [reproductor](../componentes/reproductor.md) Comparación.

## Versión aprobada y descarga

[Tarjeta de versión](../componentes/tarjeta-version.md) Aprobada + [archivos](../componentes/archivo.md) Descarga por formato (WAV para archivo, MP3 para referencia) + pasos de cierre ([RF-12](../../03-requerimientos/RF-12.md), [RF-13](../../03-requerimientos/RF-13.md)). Si la descarga depende del pago de posproducción, el motivo se muestra según [estados del sistema](estados-sistema.md#permisos).

## Móvil

Mismo orden en una columna: reproductor Escucha o Revisión, comentarios y formulario debajo; el panel lateral pasa al final.
