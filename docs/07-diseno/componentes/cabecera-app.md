---
id: comp-cabecera-app
titulo: Componente — Cabecera de app
estado: borrador
depende_de: [diseno-tokens, fund-logotipo]
---

# Cabecera de app

"Cabecera del estudio" (`161:610`), "Cabecera del portal" (`145:2886`, móvil `169:5450`) y "Cabecera del flujo" (`141:28605`). Barra superior persistente: identidad a la izquierda, contexto persistente a la derecha.

## Anatomía

1. Identidad: placa de marca ([logotipo](../fundamentos/logotipo.md#placa-de-marca)) + nombre del sistema: producto (`fuente-familia-titulo`, `fuente-tamano-base`) y ruta o área (`fuente-familia-tecnica`, `fuente-tamano-micro`).
2. Contexto persistente: [etiqueta técnica](etiqueta-tecnica.md) (sala, rol), [indicador de estado](indicador-estado.md) de sincronización y perfil (nombre; el [avatar](avatar.md) pequeño se suma cuando se implemente).
3. Fondo `color-fondo-superficie` con regla inferior `borde-grosor-base` `color-borde-fuerte`.

Alto `medida-cabecera-escritorio`; márgenes laterales `espacio-8` (app) o `espacio-12` (flujo).

## Variantes

| Variante | Contexto persistente | Uso |
|---|---|---|
| Estudio | Sala + sincronización + perfil | Panel interno |
| Portal | Proyecto seleccionado + sincronización + perfil | Portal del artista |
| Flujo | Estado de guardado + código de solicitud (etiqueta invertida) | Flujo de contratación |
| Móvil | Fila 1 (fija): identidad + botón "Menú"; fila 2 (se desplaza): el contexto persistente, incluida la señal de sincronización con su texto (en la fila 1 no cabe el texto y una señal sola sería solo color, [color](../fundamentos/color.md#reglas) regla 4). La placa lleva el logo **icono** ([logotipo](../fundamentos/logotipo.md#placa-de-marca)) | < `punto-quiebre-escritorio` (móvil y tableta, como en el brief); alto `medida-cabecera-movil` + fila de contexto. No es prop |

## Estados

El menú es **un solo** `<details>` nativo (sin isla) con el contenido de la ranura `menu` (perfil, cerrar sesión, destinos que no caben en la [navegación táctil](navegacion-tactil.md)): < `punto-quiebre-escritorio` su `<summary>` es el botón "Menú" (icono `menu`); ≥ `punto-quiebre-escritorio` es el perfil (avatar + nombre) y el panel se abre alineado a la derecha con `sombra-plana` (nivel 2, menú abierto). Nunca se oculta en escritorio si la ranura tiene contenido. Cumple los [estados comunes](README.md#estados-comunes).

## Tokens

`medida-cabecera-escritorio`, `medida-cabecera-movil`, `medida-placa-marca`, `color-fondo-superficie`, `color-borde-fuerte`, `borde-grosor-base`, `espacio-8`, `espacio-12`, `fuente-*`.

## Relaciones

Va sobre [navegacion-lateral](navegacion-lateral.md) (escritorio) o [navegacion-tactil](navegacion-tactil.md) (móvil). Ver [estructura de app](../patrones/estructura-app.md).

## Accesibilidad

- `<header>` (punto de referencia `banner`) con el logo como enlace a inicio: `/app/` en Estudio y Portal, `/` en Flujo. < `punto-quiebre-escritorio` el `<header>` usa `display: contents` para que solo la fila 1 sea fija; una prueba de Playwright a 390 px comprueba que el `banner` sigue en el árbol de accesibilidad.
- Primer elemento enfocable de la página: enlace "Saltar al contenido" (visible al recibir foco).
- El selector de proyecto móvil es un `<select>` nativo o un menú `<details>` con lista de enlaces.

## Código

`frontend/src/componentes/CabeceraApp.astro`, props `variante` (`estudio|portal|flujo`), `producto`, `area`, `usuario`; ranuras `contexto` (fila 2 / derecha) y `menu` (contenido del `<details>`).
