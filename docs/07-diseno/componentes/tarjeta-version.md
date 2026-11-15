---
id: comp-tarjeta-version
titulo: Componente — Tarjeta de versión
estado: borrador
depende_de: [diseno-tokens, comp-indicador-estado]
---

# Tarjeta de versión

"Version Control Widget" de la guía (`86:185`, *used for feedback validation*: archivo + señal + "Modulado hace 2h por Ing. Ramírez"), `VersionControlSimulator` de la landing (`48:205`) y "Versión" del historial (`145:3868`: identificador + autor y fecha + etiqueta + selector de comparación).

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base`, relleno `espacio-4`.
2. Identificador: caja cuadrada con el número de versión (`V3`) en `fuente-familia-tecnica` `fuente-tamano-titulo-sm`.
3. Archivo (`fuente-familia-tecnica`) + [señal](indicador-estado.md) + autor y fecha relativa ("Publicado hace 2 h por Ing. Ramírez").
4. [Etiqueta](etiqueta-tecnica.md) de estado de la versión.
5. Opcional: [casilla](casilla.md) "Comparar" y acciones (escuchar, ver comentarios).

## Variantes

| Variante | Uso |
|---|---|
| Actual | Versión vigente: etiqueta Activa ("V3 · EN REVISIÓN"), fondo `color-fondo-destacado` en el identificador |
| Historial | Fila de la lista de versiones, con casilla de comparación |
| Aprobada | Etiqueta Éxito "APROBADA"; enlaza a la descarga |

Estados de versión del dominio: [versionado y feedback](../../02-dominio/flujos/versionado-feedback.md).

## Estados

La tarjeta enlaza al detalle de la versión: [estados comunes](README.md#estados-comunes). Al marcar dos versiones, se habilita "Comparar".

## Tokens

`color-fondo-superficie`, `color-fondo-destacado`, `borde-grosor-base`, `espacio-4`, `fuente-familia-tecnica`, `fuente-tamano-titulo-sm`.

## Relaciones

Junto al [reproductor](reproductor.md) en [audio y versiones](../patrones/audio-y-versiones.md).

## Accesibilidad

- La fecha relativa va en `<time datetime>` con la fecha absoluta en `title`.
- El selector de comparación es un formulario `GET` con casillas: funciona sin JS.

## Código

`frontend/src/componentes/TarjetaVersion.astro`, props `numero`, `archivo`, `autor`, `fecha`, `estado`, `variante`, `comparable`, `href`.
