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
2. Contexto persistente: [etiqueta técnica](etiqueta-tecnica.md) (sala, rol), [indicador de estado](indicador-estado.md) de sincronización y perfil ([avatar](avatar.md) pequeño + nombre).
3. Fondo `color-fondo-superficie` con regla inferior `borde-grosor-base` `color-borde-fuerte`.

Alto `medida-cabecera-escritorio`; márgenes laterales `espacio-8` (app) o `espacio-12` (flujo).

## Variantes

| Variante | Contexto persistente | Uso |
|---|---|---|
| Estudio | Sala + sincronización + perfil | Panel interno |
| Portal | Proyecto seleccionado + sincronización + perfil | Portal del artista |
| Flujo | Estado de guardado + código de solicitud (etiqueta invertida) | Flujo de contratación |
| Móvil | Fila 1: identidad + señal + botón "Menú"; fila 2: proyecto actual + selector | < `punto-quiebre-escritorio` (móvil y tableta, como en el brief); alto `medida-cabecera-movil` + fila de contexto |

## Estados

El perfil y el botón "Menú" son interactivos: [estados comunes](README.md#estados-comunes). El menú de perfil y el menú móvil se abren con `<details>` nativo (sin isla).

## Tokens

`medida-cabecera-escritorio`, `medida-cabecera-movil`, `medida-placa-marca`, `color-fondo-superficie`, `color-borde-fuerte`, `borde-grosor-base`, `espacio-8`, `espacio-12`, `fuente-*`.

## Relaciones

Va sobre [navegacion-lateral](navegacion-lateral.md) (escritorio) o [navegacion-tactil](navegacion-tactil.md) (móvil). Ver [estructura de app](../patrones/estructura-app.md).

## Accesibilidad

- `<header>` con el logo como enlace a inicio.
- Primer elemento enfocable de la página: enlace "Saltar al contenido" (visible al recibir foco).
- El selector de proyecto móvil es un `<select>` nativo o un menú `<details>` con lista de enlaces.

## Código

`frontend/src/componentes/CabeceraApp.astro`, props `variante`, `producto`, `area`, `usuario`; ranura `contexto`.
