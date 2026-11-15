---
id: comp-casilla
titulo: Componente — Casilla
estado: borrador
depende_de: [diseno-tokens]
---

# Casilla

Capa "Casilla" del brief de proyecto (`141:28788`, "Necesidades": control 20 × 20 + etiqueta + detalle), "Recordar sesión" del acceso (`112:373`) y "Selector de comparación" del historial de versiones. Elección binaria o múltiple dentro de una lista.

## Anatomía

1. Control cuadrado de `medida-icono-md`: `borde-grosor-base` `color-borde-fuerte`, `borde-radio-ninguno`, fondo `color-fondo-claro`.
2. Marca: icono `check` en `color-texto-principal` sobre `color-fondo-destacado` cuando está marcada.
3. Etiqueta (`fuente-tamano-base`) y detalle opcional (`fuente-tamano-pequeno`, `color-texto-secundario`), separados del control por `espacio-3`.

## Variantes

| Variante | Elemento | Uso |
|---|---|---|
| Casilla | `<input type="checkbox">` | Selección múltiple, aceptación de condiciones |
| Radio | `<input type="radio">` (control circular) | Una opción entre pocas, en lista compacta. Para opciones con descripción: [tarjeta-opcion](tarjeta-opcion.md) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

- Marcada: fondo `color-fondo-destacado` + `check`; radio: punto `medida-senal` en `color-texto-principal`.
- Indeterminada: icono `minus`. La propiedad `indeterminate` solo existe en JS: el componente estático no la ofrece y la usa una isla (p. ej. "seleccionar todo" de una tabla). El nativo se anuncia como "mixto" sin ARIA extra.
- Error de grupo: borde `color-texto-alerta` en cada control (`aria-invalid="true"`) y mensaje al final, **dentro** del `<fieldset>`, unido con `aria-describedby` en el `<fieldset>`.

## Tokens

`medida-icono-md`, `borde-grosor-base`, `borde-radio-ninguno`, `color-borde-fuerte`, `color-fondo-claro`, `color-fondo-destacado`, `color-texto-principal`, `color-texto-secundario`, `espacio-3`, `fuente-tamano-base`, `fuente-tamano-pequeno`.

## Relaciones

En [formularios](../patrones/formularios.md) y en el selector de comparación de [tarjeta-version](tarjeta-version.md).

## Accesibilidad

- Control nativo con `appearance: none` y estilo propio; nunca un `<div>` con rol.
- Toda la fila (control + etiqueta) es el `<label>`: el área de clic supera `medida-control-base` de alto.
- Grupo en `<fieldset>` con `<legend>`.

## Código

`frontend/src/componentes/Casilla.astro`, props `tipo` (`casilla|radio`), `nombre`, `valor`, `etiqueta`, `detalle`, `marcada`; el resto de atributos va al `<input>` (`disabled`, `aria-invalid`, `required`).
