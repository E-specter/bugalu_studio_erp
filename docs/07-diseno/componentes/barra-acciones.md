---
id: comp-barra-acciones
titulo: Componente — Barra de acciones
estado: borrador
depende_de: [diseno-tokens, comp-boton]
---

# Barra de acciones

"Barra de acciones" del flujo de contratación (`141:28788`, `141:29060`): acción anterior + nota a la izquierda, acción principal a la derecha. Cierra un formulario o paso.

## Cuándo se usa

Solo cuando el formulario o el paso cierra con **dos o más** acciones (anterior + continuar, cancelar + guardar, rechazar + aprobar). Con una sola acción no hay barra: el [botón](boton.md) Primario va al final del formulario, a su ancho natural y alineado al inicio (perfil, cambiar rol). Decisión de la revisión visual de RF-01: una regla y un contenedor para un solo botón no ordenan nada.

## Anatomía

1. Regla superior `borde-grosor-base` `color-borde-fuerte`, separación `espacio-4`.
2. Izquierda: [botón](boton.md) secundario grande ("Anterior") y nota (`fuente-tamano-pequeno`, `color-texto-secundario`: "Tu avance se guarda automáticamente").
3. Derecha: botón primario grande ("Continuar" + `arrow-right`).

## Variantes

| Variante | Uso |
|---|---|
| Flujo | Anterior + nota + continuar |
| Formulario | Cancelar (secundario) + guardar (primario) |
| Decisión | Rechazar (peligro) + aprobar (primario): validación de pagos, aprobación de versión |
| Móvil | Botones a ancho completo, apilados; el principal arriba. También a cualquier ancho dentro de un [panel](panel.md) Lateral (decisión de la revisión visual de pagos: dos botones grandes no caben en fila y su texto se partía) |

## Estados

Los de [botón](boton.md). Mientras se envía, el principal en estado Carga y el resto deshabilitado.

## Tokens

`borde-grosor-base`, `color-borde-fuerte`, `color-texto-secundario`, `espacio-4`, `fuente-tamano-pequeno`.

## Relaciones

Al final de [formularios](../patrones/formularios.md) y de cada paso del [flujo por pasos](../patrones/flujo-por-pasos.md).

## Accesibilidad

- El orden del DOM sigue el visual de lectura (anterior → continuar); en móvil el reordenamiento es solo visual si mantiene el orden lógico de foco.
- El principal es `type="submit"`; "Anterior" es un enlace o `type="submit"` con `formnovalidate` para no bloquear por validación.

## Código

`frontend/src/componentes/BarraAcciones.astro`, props `variante` (`flujo|formulario|decision`), `nota`; ranuras `secundaria` y `principal`. Móvil no es prop: la da el punto de quiebre (`punto-quiebre-tableta`) o el panel Lateral.
