---
id: comp-boton
titulo: Componente — Botón
estado: borrador
depende_de: [diseno-tokens, fund-forma-elevacion]
---

# Botón

"Botón brutalista" de la guía (`86:158`: `ButtonPrimary` `86:161`, `ButtonSecondary` `86:168`), `BrutalistButton` de la landing (`48:122`) y las capas "Acción" de las pantallas del `erp`. Ejecuta una acción o envía un formulario.

## Anatomía

1. Contenedor rectangular: `borde-grosor-base` en `color-borde-fuerte`, `borde-radio-ninguno`, **sin sombra** (`86:161`, `86:168`, `161:695`).
2. Etiqueta: `fuente-familia-titulo`, `fuente-peso-titulo`, `fuente-tamano-base`, mayúsculas.
3. Icono opcional al final (`arrow-right` si avanza), `medida-icono-sm`, separado `espacio-2`.

Relleno horizontal `espacio-5`; alto `medida-control-base`.

## Variantes

| Variante | Fondo | Texto | Uso |
|---|---|---|---|
| Primario | `color-fondo-destacado` | `color-texto-principal` | La acción principal de la vista. **Una por vista**; en un listado vacío manda la del vacío ([estados del sistema](../patrones/estados-sistema.md#vacío)) |
| Secundario | `color-fondo-superficie` | `color-texto-principal` | Acciones de apoyo: escuchar máster, "anterior", "ver todos" (`86:168`) |
| Peligro | `color-fondo-superficie`, borde `color-texto-alerta` | `color-texto-alerta` | Cancelar reserva, rechazar pago (brief: Figma no dibuja acciones destructivas) |

| Tamaño | Alto | Uso |
|---|---|---|
| Base | `medida-control-base` | Panel interno y portal |
| Grande | `medida-control-grande` | Acción principal de un flujo por pasos y CTA de la landing |

En móvil todo botón mide al menos `medida-control-tactil`.

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Hover (primario, secundario) | Fondo `color-fondo-alerta`, texto `color-texto-sobre-alerta` (la guía reserva el naranja para el hover interactivo, `86:99`) |
| Hover (peligro) | Fondo `color-fondo-peligro`, texto `color-texto-invertido` (6,38:1) |
| Activo | Sin desplazamiento ni cambio propio: el botón no lleva sombra ([forma](../fundamentos/forma-elevacion.md#interacción-física)) |
| Carga | Etiqueta en gerundio ("Publicando…"), `aria-busy="true"`, `disabled` para evitar doble envío. El ancho puede variar con el texto: no se fija a mano. En un grupo, el botón que entra en carga va al final para que el cambio no desplace a los demás |

Las pantallas `erp` rellenan la acción de naranja con texto lienzo (`161:695`, 2,65:1): no se adopta; el naranja queda para el hover, como en la guía (decisión del usuario, 2026-11-15).

## Tokens

`color-fondo-destacado`, `color-fondo-superficie`, `color-fondo-alerta`, `color-fondo-peligro`, `color-texto-*`, `color-borde-fuerte`, `borde-grosor-base`, `borde-radio-ninguno`, `fuente-*`, `espacio-2`, `espacio-5`, `medida-control-*`, `movimiento-duracion-rapida`.

## Relaciones

Usado por [barra-acciones](barra-acciones.md), [encabezado-pantalla](encabezado-pantalla.md), [panel](panel.md). No confundir con [etiqueta-tecnica](etiqueta-tecnica.md) (radio 4 px, sin sombra, no es acción).

## Accesibilidad

- `<button type="button|submit">` para acciones; `<a href>` con el mismo aspecto si navega.
- Etiqueta que dice qué pasa ("Publicar versión", no "Aceptar").
- Botón de solo icono: `aria-label` obligatorio.
- Área mínima 24 × 24 px (WCAG 2.5.8); en la práctica, el alto del tamaño.

## Código

`frontend/src/componentes/Boton.astro`, props `variante`, `tamano`, `tipo`, `href`, `icono` (`arrow-right`, `x`, `eye`, `search`, `menu`), `cargando`; el resto de atributos va al `<button>` o `<a>` ([reglas de las fichas](README.md#reglas-de-las-fichas)). La etiqueta es la ranura por defecto; en carga, quien usa el botón pasa el gerundio.
