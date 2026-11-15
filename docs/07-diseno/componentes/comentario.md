---
id: comp-comentario
titulo: Componente — Comentario
estado: borrador
depende_de: [diseno-tokens, comp-avatar]
---

# Comentario

"Comentario" del hilo de revisión (`145:3617`, 788 × 105–122: avatar + contenido con autor y estado, marca temporal y mensaje). Observación de un artista o del personal sobre una versión ([RF-10](../../03-requerimientos/RF-10.md)).

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base`, relleno `espacio-4`; [avatar](avatar.md) medio a la izquierda, contenido con sangría `espacio-3`.
2. Autor y estado: nombre (`fuente-peso-titulo`), rol, [etiqueta](etiqueta-tecnica.md) de estado ("ABIERTO", "RESUELTO").
3. Marca temporal del audio: botón `fuente-familia-tecnica` (`02:14`) que lleva el reproductor a ese punto.
4. Mensaje: `fuente-tamano-lectura`, `color-texto-cuerpo`, `medida-linea-lectura`.
5. Fecha de publicación: `fuente-tamano-micro`, `color-texto-secundario`.

## Variantes

| Variante | Diferencia |
|---|---|
| Artista | Avatar con fondo `color-fondo-destacado` |
| Personal | Avatar invertido; puede marcar "Resuelto" |
| Resuelto | Mensaje en `color-texto-secundario` y etiqueta Éxito |

## Estados

La marca temporal y "Marcar resuelto" cumplen los [estados comunes](README.md#estados-comunes). Comentario activo (el reproductor está en su marca): borde izquierdo `borde-grosor-grueso` `color-borde-fuerte`.

## Tokens

`color-fondo-superficie`, `color-texto-principal`, `color-texto-cuerpo`, `color-texto-secundario`, `borde-grosor-base`, `borde-grosor-grueso`, `color-borde-fuerte`, `espacio-3`, `espacio-4`, `medida-linea-lectura`, `fuente-*`.

## Relaciones

Hilo + formulario de comentario junto al [reproductor](reproductor.md) en [audio y versiones](../patrones/audio-y-versiones.md).

## Accesibilidad

- `<article>` por comentario; el hilo es una `<ol>`.
- La marca temporal es `<button>` con `aria-label="Ir a 2 minutos 14 segundos"` (o enlace `#t=134` sin JS).

## Código

`frontend/src/componentes/Comentario.astro`, props `autor`, `rol`, `marca`, `mensaje`, `fecha`, `estado`.
