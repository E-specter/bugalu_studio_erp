---
id: comp-pasos
titulo: Componente — Pasos
estado: borrador
depende_de: [diseno-tokens]
---

# Pasos

"Progreso comercial" del flujo de contratación (`141:28605`, 6 "Paso": número + lectura de estado + nombre) y "Etapa de producción" / "Fase" en proyectos. Muestra en qué punto de una secuencia está el usuario.

## Anatomía

1. Banda de ancho completo bajo la cabecera, fondo `color-fondo-superficie`, regla inferior `borde-grosor-base`.
2. Paso: caja con `borde-grosor-fino`, relleno `espacio-3`:
   - Fila superior: número (`fuente-familia-tecnica`, `01`) y lectura de estado a la derecha ("HECHO", "ACTUAL", "PENDIENTE", `fuente-tamano-micro`).
   - Nombre del paso: `fuente-tamano-base`.
3. Pasos en partes iguales con hueco `espacio-2`.

## Variantes

| Variante | Uso |
|---|---|
| Horizontal | Escritorio: todos los pasos visibles |
| Compacta | Móvil: solo "PASO 3 DE 6 · Agenda de asesoría" + [barra de progreso](barra-progreso.md) |

## Estados

| Estado del paso | Visual |
|---|---|
| Hecho | Lectura "HECHO" con icono `check`; es enlace para volver a ese paso (si el paso no tiene página propia, como la cuenta de la reserva, es texto) |
| Actual | Fondo `color-fondo-destacado`, `borde-grosor-base` `color-borde-fuerte` |
| Pendiente | `color-texto-secundario`; no es enlace |
| Con error | Lectura "REVISAR" en `color-texto-alerta` |

Los pasos "Hecho" cumplen los [estados comunes](README.md#estados-comunes).

## Tokens

`color-fondo-superficie`, `color-fondo-destacado`, `color-borde-fuerte`, `color-texto-secundario`, `color-texto-alerta`, `borde-grosor-base`, `borde-grosor-fino`, `espacio-2`, `espacio-3`, `fuente-familia-tecnica`, `fuente-tamano-micro`, `fuente-tamano-base`.

## Relaciones

Núcleo del [flujo por pasos](../patrones/flujo-por-pasos.md), junto con [barra-acciones](barra-acciones.md) y [resumen-persistente](resumen-persistente.md).

## Accesibilidad

- `<nav aria-label>` con `<ol>` ("Progreso de la solicitud", "Progreso de la reserva"); el paso actual con `aria-current="step"`.
- La lectura de estado es texto, no solo color.

## Código

`frontend/src/componentes/Pasos.astro`, props `pasos` (nombre, href, estado), `actual`, `etiqueta` (`aria-label`). Primer uso: la reserva de sala (TAREA-RF04-6); la isla cambia el `href` de los pasos HECHO (la consulta de la URL lleva la elección) y la lectura a REVISAR.
