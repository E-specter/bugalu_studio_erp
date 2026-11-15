---
id: comp-tabla
titulo: Componente — Tabla
estado: borrador
depende_de: [diseno-tokens, comp-panel]
---

# Tabla

"Tabla de clientes" (`161:842`: cabecera de 32 px + filas con identidad, datos, estado y acción), "Tabla de entregables" y partidas de la cotización (`141:29356`: descripción, cantidad, precio unitario, importe). Datos tabulares del panel interno.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`.
2. Cabecera: fondo `color-fondo-invertido`, texto `color-texto-invertido`, `fuente-familia-tecnica` `fuente-tamano-micro` mayúsculas, relleno `espacio-3` / `espacio-4`.
3. Fila: relleno `espacio-4`, divisor inferior `borde-grosor-fino`. Celda principal con [avatar](avatar.md) o código + nombre y dato secundario debajo (`color-texto-secundario`).
4. Celdas de estado con [etiqueta técnica](etiqueta-tecnica.md); celda de acción con [botón](boton.md) secundario o enlace.
5. Pie opcional: totales (cotización) o paginación.

Cifras alineadas a la derecha con `tabular-nums`; texto a la izquierda.

## Variantes

| Variante | Uso |
|---|---|
| Directorio | Clientes, personal, pagos por validar |
| Partidas | Cotización y cobro: columnas numéricas + fila de total en `fuente-peso-titulo` |
| Compacta | Relleno `espacio-3`; listados largos (historial, reportes) |

## Estados

| Estado | Visual |
|---|---|
| Fila hover (si toda la fila enlaza) | Fondo `color-fondo-claro` |
| Fila seleccionada | Fondo `color-fondo-destacado` + borde izquierdo `borde-grosor-grueso` `color-borde-fuerte` en la primera celda + [casilla](casilla.md) marcada si la selección es múltiple. El fondo lavanda solo no basta (1,31:1) |
| Cabecera ordenable | Botón en la celda con icono `arrow-up-down`; la columna ordenada muestra `arrow-up` o `arrow-down` |
| Vacía, carga, error | [Estados del sistema](../patrones/estados-sistema.md): una fila con el mensaje a todo el ancho |

## Adaptabilidad

< `punto-quiebre-escritorio`: cada fila pasa a tarjeta con pares etiqueta/valor (`<dl>`) en una columna. Si se necesita la tabla completa, contenedor con `overflow-x: auto` y `tabindex="0"` + `aria-label`.

## Tokens

`color-fondo-superficie`, `color-fondo-invertido`, `color-fondo-claro`, `color-fondo-destacado`, `color-texto-invertido`, `color-texto-secundario`, `color-borde-fuerte`, `borde-grosor-base`, `borde-grosor-fino`, `borde-grosor-grueso`, `espacio-3`, `espacio-4`, `fuente-*`, `punto-quiebre-escritorio`.

## Relaciones

Dentro de un [panel](panel.md); controles encima según [tablas y tableros](../patrones/tablas-y-tableros.md).

## Accesibilidad

- `<table>` real con `<caption>` (puede ser visualmente oculto), `<th scope="col">` y, en la celda principal, `<th scope="row">`.
- Ordenación: `aria-sort` en el `<th>` ordenado.
- Fila seleccionada: la selección se hace con la casilla nativa de la primera celda, que da el estado; `role="grid"` solo si una isla aporta la navegación con flechas. La fila del registro abierto en el lateral usa `aria-current="true"` en su enlace.
- Acciones por fila con texto que incluye el objeto ("Validar pago PAG-031").

## Código

`frontend/src/componentes/Tabla.astro`, props `titulo` (`<caption>` oculto), `columnas` (`string[]`; `""` es la columna de acciones, con nombre oculto "Acciones") y `variante` (`directorio|compacta`). Las filas entran por la **ranura por defecto** como `<tr>` completos: la celda principal es `<th scope="row">` y cada `<td>` lleva `data-etiqueta` con el rótulo de su columna, que la tarjeta móvil muestra delante del valor (`data-etiqueta=""` en la de acciones). Cada `<td>` ya es la "ranura por celda": dentro va cualquier componente ([etiqueta](etiqueta-tecnica.md), [botón](boton.md)).

Sin prop `filas`: las tablas de datos del servidor las pinta una isla clonando un `<template>` de fila en el navegador, así que una prop que solo sirve al pintar en el servidor no la usaría nadie. Decisión de la revisión visual de RF-01.

Se implementan con la primera pantalla que los pida (antes, sin código): variante Partidas (cifras a la derecha con `tabular-nums` y fila de total), cabecera ordenable, fila seleccionada y pie.
