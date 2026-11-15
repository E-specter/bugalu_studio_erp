---
id: comp-encabezado-pantalla
titulo: Componente — Encabezado de pantalla
estado: borrador
depende_de: [diseno-tokens, fund-tipografia]
---

# Encabezado de pantalla

Capa "Encabezado de pantalla" (24 apariciones; `161:609`, `145:2885`, `141:28605`): contexto (ruta + fecha), índice y acción, título, descripción y regla. Abre toda vista de app.

## Anatomía

1. Contexto: ruta a la izquierda (`fuente-tamano-pequeno`, `color-texto-secundario`) y fecha o sesión a la derecha (`fuente-familia-tecnica`).
2. Índice y acción: índice técnico (`fuente-familia-tecnica`, `fuente-tamano-micro`: `[03] TABLERO / PRODUCCIÓN`) y, a la derecha, la acción principal de la vista o un grupo de etiqueta + acción.
3. Título: `fuente-familia-display`, `fuente-tamano-titulo-lg`, mayúsculas.
4. Descripción: `fuente-tamano-lectura`, `color-texto-cuerpo`, `medida-linea-lectura`.
5. Regla: `borde-grosor-base` `color-borde-fuerte` a todo el ancho.

Separaciones: `espacio-2` entre contexto e índice, `espacio-3` hasta el título y la descripción; `espacio-6` desde la regla hasta el siguiente bloque.

## Variantes

| Variante | Diferencia | Uso |
|---|---|---|
| App | Con contexto y acción | Panel interno y portal |
| Flujo | Sin contexto (ni ruta ni fecha: la ubicación la dan los [pasos](pasos.md)); el índice indica paso ("PASO 02 / 06") y el metadato va a la derecha por la ranura `acciones` | Flujo de contratación |
| Móvil | Acción debajo de la descripción, ancho del contenido. No es prop: lo aplica el punto de quiebre | < `punto-quiebre-tableta` |

## Estados

Estático. La acción sigue a [botón](boton.md).

## Tokens

`fuente-familia-display`, `fuente-familia-tecnica`, `fuente-tamano-titulo-lg`, `fuente-tamano-lectura`, `fuente-tamano-pequeno`, `fuente-tamano-micro`, `medida-linea-lectura`, `color-texto-principal`, `color-texto-cuerpo`, `color-texto-secundario`, `color-borde-fuerte`, `borde-grosor-base`, `espacio-2`, `espacio-3`, `espacio-6`.

## Relaciones

Siempre el primer bloque de `<main>` en [estructura de app](../patrones/estructura-app.md). Debajo suelen ir [métricas](metrica.md).

## Accesibilidad

- El título es el único `<h1>` de la vista y coincide con el `<title>` del documento. Única excepción: el catálogo de desarrollo, que muestra varias variantes en una página y no es una vista.
- La ruta es un `<nav aria-label="Ruta">` con `<ol>` y `aria-current="page"` en el último elemento.

## Código

`frontend/src/componentes/EncabezadoPantalla.astro`, props `ruta` (`{ etiqueta, href }[]`, el último es la página actual), `fecha`, `indice`, `titulo`, `descripcion`, `variante` (`app|flujo`); ranura `acciones`.
