---
id: comp-casilla
titulo: Componente — Casilla
estado: borrador
depende_de: [diseno-tokens]
---

# Casilla

Capa "Casilla" del brief de proyecto (`141:28788`, "Necesidades": control 20 × 20 + etiqueta + detalle), "Recordar sesión" del acceso (`112:373`) y "Selector de comparación" del historial de versiones. Elección binaria o múltiple dentro de una lista.

## Anatomía

1. Control cuadrado de `medida-icono-md`: `borde-grosor-base` `color-borde-fuerte`, `borde-radio-ninguno`, fondo `color-fondo-superficie`.
2. Marca: icono `check` en `color-texto-principal` sobre `color-fondo-destacado` cuando está marcada.
3. Etiqueta (`fuente-tamano-base`) y detalle opcional (`fuente-tamano-pequeno`, `color-texto-secundario`), separados del control por `espacio-3`.

## Variantes

| Variante | Elemento | Uso |
|---|---|---|
| Casilla | `<input type="checkbox">` | Selección múltiple, aceptación de condiciones |
| Radio | `<input type="radio">` (control circular) | Una opción entre pocas, en lista compacta. Para opciones con descripción: [tarjeta-opcion](tarjeta-opcion.md) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios: marcada (fondo `color-fondo-destacado` + marca), indeterminada (raya horizontal), error de grupo (mensaje bajo el `<fieldset>`).

## Tokens

`medida-icono-md`, `borde-grosor-base`, `borde-radio-ninguno`, `color-borde-fuerte`, `color-fondo-superficie`, `color-fondo-destacado`, `color-texto-principal`, `color-texto-secundario`, `espacio-3`, `fuente-tamano-base`, `fuente-tamano-pequeno`.

## Relaciones

En [formularios](../patrones/formularios.md) y en el selector de comparación de [tarjeta-version](tarjeta-version.md).

## Accesibilidad

- Control nativo con `appearance: none` y estilo propio; nunca un `<div>` con rol.
- Toda la fila (control + etiqueta) es el `<label>`: el área de clic supera `medida-control-base` de alto.
- Grupo en `<fieldset>` con `<legend>`.

## Código

`frontend/src/componentes/Casilla.astro`, props `tipo` (`casilla|radio`), `nombre`, `valor`, `etiqueta`, `detalle`, `marcada`.
