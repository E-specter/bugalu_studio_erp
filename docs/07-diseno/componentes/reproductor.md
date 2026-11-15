---
id: comp-reproductor
titulo: Componente — Reproductor (isla)
estado: borrador
depende_de: [diseno-tokens, comp-comentario, arq-frontend-islas]
---

# Reproductor

"Monitor de revisión" (`145:3617`): cabecera del audio (versión, metadato, lectura de tiempo actual / duración) + audio (botón reproducir de 52 px, forma de onda, fila de marcadores). Aplica "Rigor sonoro" (`86:66`): medición precisa, sin ornamento. [RF-10](../../03-requerimientos/RF-10.md).

## Anatomía

1. [Panel](panel.md) Técnico o Base.
2. Cabecera: archivo de la versión (`fuente-familia-tecnica`) + metadato; a la derecha, tiempo actual en `fuente-tamano-titulo-md` y duración en `fuente-tamano-micro`, `tabular-nums`.
3. Botón reproducir/pausar: cuadrado de `medida-reproducir`, [botón](boton.md) secundario de solo icono.
4. Forma de onda: barras verticales en `color-fondo-invertido` (parte reproducida) y `color-borde-tecnico` (pendiente) con cabezal de `borde-grosor-base` en `color-borde-fuerte`. En el panel Técnico (navy): reproducida `color-texto-invertido`, pendiente `color-borde-tecnico`, cabezal `color-foco-invertido`. La posición la dan el cabezal y la lectura de tiempo; el color de las barras solo refuerza (lavanda sobre lienzo es decorativo). Los picos los calcula el backend al cargar el archivo.
5. Marcadores: fila bajo la onda con una marca por comentario en su tiempo; la marca es un botón con contorno `borde-grosor-base` `color-borde-fuerte`.

## Variantes

| Variante | Uso |
|---|---|
| Revisión | Con marcadores y vinculación temporal al formulario de comentario |
| Escucha | Sin marcadores: detalle de versión, versión aprobada, móvil |
| Comparación | Dos ondas apiladas (versión A / B) con un único control de reproducción y conmutador A/B |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Cargando audio | Onda en `color-borde-tecnico` con `aria-busy="true"`; botón deshabilitado |
| Reproduciendo | Icono `pause`; cabezal avanza (lineal) |
| Marcador activo | Marca rellena `color-fondo-invertido` (en reposo solo contorno), `aria-current="true"`, y [comentario](comentario.md) activo resaltado. Sin naranja: hay un marcador por comentario |
| Error de audio | [Aviso](aviso.md) Error: "No se pudo cargar la versión. Reintentar" |

## Tokens

`medida-reproducir`, `color-fondo-invertido`, `color-borde-tecnico`, `color-borde-fuerte`, `color-texto-invertido`, `color-foco-invertido`, `borde-grosor-base`, `fuente-familia-tecnica`, `fuente-tamano-titulo-md`, `fuente-tamano-micro`.

## Relaciones

Con [comentario](comentario.md) y [tarjeta-version](tarjeta-version.md) en [audio y versiones](../patrones/audio-y-versiones.md).

## Accesibilidad

- **Sin JS:** `<audio controls preload="metadata">` nativo; los comentarios enlazan a `#t=` del archivo.
- Con JS: la onda es un control deslizante (`role="slider"`, `aria-valuetext="1 minuto 30 de 3 minutos 45"`); flechas ±5 s, Inicio/Fin.
- Espacio reproduce/pausa solo cuando el foco está en el reproductor (no atajo global).
- Marcadores en orden temporal, cada uno con `aria-label` "Comentario de Ana en 2:14".
- No hay reproducción automática.

## Código

Isla `frontend/src/islas/Reproductor.astro` que registra `<bugalu-reproductor>`; atributos `src`, `picos` (URL JSON), `variante`; emite `bugalu-tiempo` para que el formulario de comentario tome la marca temporal.
