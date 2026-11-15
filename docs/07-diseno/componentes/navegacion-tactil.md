---
id: comp-navegacion-tactil
titulo: Componente — Navegación táctil
estado: borrador
depende_de: [diseno-tokens, comp-navegacion-lateral]
---

# Navegación táctil

"Navegación táctil" de las pantallas móviles del portal (`169:5490`): cinco destinos de 78 × 56 (icono + etiqueta) en una barra fija **bajo la cabecera** (decisión del usuario, 2026-11-15: arriba, como en Figma).

## Anatomía

1. Barra de ancho completo, alto `medida-nav-tactil`, fondo `color-fondo-superficie`, regla inferior `borde-grosor-base` `color-borde-fuerte`.
2. Destinos en partes iguales: icono `medida-icono-md` sobre etiqueta (`fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas).

Máximo cinco destinos; el resto va al menú de la [cabecera](cabecera-app.md).

**Foco no tapado (WCAG 2.4.11):** la fila 1 de la cabecera móvil y esta barra quedan fijas (`position: sticky`) y la fila de contexto se desplaza. El documento lleva `scroll-padding-top: var(--medida-zona-fija-movil)` para que el elemento enfocado o el ancla nunca quede debajo; ≥ `punto-quiebre-escritorio` no hay barra y vuelve a `0`. Decisión del brief (TAREA-203).

## Variantes

Una. Los destinos son los mismos que en la [navegación lateral](navegacion-lateral.md) del perfil, en el mismo orden.

## Estados

Comunes: [catálogo](README.md#estados-comunes). Actual: fondo `color-fondo-destacado` y regla inferior `borde-grosor-grueso` `color-borde-fuerte`.

## Tokens

`medida-nav-tactil`, `medida-zona-fija-movil`, `medida-icono-md`, `color-fondo-superficie`, `color-fondo-destacado`, `color-borde-fuerte`, `borde-grosor-base`, `borde-grosor-grueso`, `fuente-familia-tecnica`, `fuente-tamano-micro`.

## Relaciones

Solo < `punto-quiebre-escritorio`. Parte de [estructura de app](../patrones/estructura-app.md).

## Accesibilidad

- `<nav aria-label="Principal">` con enlaces y `aria-current="page"`.
- Cada destino mide al menos `medida-control-tactil` de alto (la barra mide `medida-nav-tactil`).
- Etiqueta siempre visible: no hay destinos de solo icono.

## Código

`frontend/src/componentes/NavegacionTactil.astro`, props `destinos`, `actual`.
