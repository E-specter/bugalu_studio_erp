---
id: comp-tarjeta-opcion
titulo: Componente — Tarjeta de opción
estado: borrador
depende_de: [diseno-tokens, comp-casilla]
---

# Tarjeta de opción

"Opción" de la selección de servicio (`141:28605`, tres columnas) y de la modalidad de asesoría (`141:29060`: "Control de selección" + título + descripción + metadato). Elección única entre alternativas que necesitan explicación.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`, relleno `espacio-5`.
2. Control de selección (radio) arriba a la izquierda, con su texto de estado.
3. Título: `fuente-familia-titulo`, `fuente-tamano-titulo-sm`, mayúsculas.
4. Descripción: `fuente-tamano-base`, `color-texto-cuerpo`.
5. Metadato al pie: `fuente-familia-tecnica`, `fuente-tamano-micro` (precio base, duración, modalidad).

Tarjetas en retícula de 3 columnas con hueco `espacio-3`; en móvil, una columna.

## Variantes

| Variante | Uso |
|---|---|
| Servicio | Selección de servicio en el flujo de contratación |
| Modalidad | Presencial / virtual en la agenda de asesoría ([RF-15](../../03-requerimientos/RF-15.md)) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Hover | Fondo `color-fondo-claro` |
| Seleccionada | Fondo `color-fondo-destacado`, `sombra-plana`; el control marcado y la etiqueta de estado dice "Seleccionado" |
| No disponible | Deshabilitado común + metadato que explica por qué ("Sin horarios esta semana") |

## Tokens

`color-fondo-superficie`, `color-fondo-claro`, `color-fondo-destacado`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-cuerpo`, `borde-grosor-base`, `sombra-plana`, `espacio-3`, `espacio-5`, `fuente-*`.

## Relaciones

Usa el radio de [casilla](casilla.md). Va dentro del [flujo por pasos](../patrones/flujo-por-pasos.md).

## Accesibilidad

- Cada tarjeta es un `<label>` que contiene un `<input type="radio">` real; el grupo es un `<fieldset>` con `<legend>`.
- Las flechas mueven la selección dentro del grupo (comportamiento nativo del radio).
- El estado seleccionado no depende solo del fondo lavanda: hay control marcado y texto.

## Código

`frontend/src/componentes/TarjetaOpcion.astro`, props `nombre`, `valor`, `titulo`, `descripcion`, `metadato`, `seleccionada`, `disponible`.
