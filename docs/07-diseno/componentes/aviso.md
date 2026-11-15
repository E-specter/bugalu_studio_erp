---
id: comp-aviso
titulo: Componente — Aviso
estado: borrador
depende_de: [diseno-tokens, fund-color]
---

# Aviso

Mensaje en línea que informa el resultado de una acción o una condición de la vista. En Figma solo aparece como "Alerta" y "Aviso de fase" (texto en panel, `161:609`); la anatomía y las variantes son **inferidas** para cubrir los estados del sistema.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base` en el color de la variante, `borde-radio-ninguno`, relleno `espacio-4`.
2. Icono `medida-icono-sm` en el color de la variante.
3. Título corto (`fuente-familia-titulo`, `fuente-tamano-base`) y texto (`fuente-tamano-base`).
4. Acción opcional: enlace o [botón](boton.md) contorno ("Reintentar", "Ver pago").

## Variantes

| Variante | Borde e icono | Icono | Uso |
|---|---|---|---|
| Información | `color-borde-fuerte` | `info` | Contexto: "Los cambios se publican en la siguiente ronda" |
| Éxito | `color-texto-exito` | `check-circle` | "Pago registrado. Queda pendiente de validación" |
| Aviso | `color-texto-aviso` | `clock` | Plazo próximo, pre-reserva por vencer |
| Error | `color-texto-alerta` | `alert-triangle` | Fallo de envío, validación del servidor |
| Crítico | fondo `color-fondo-alerta`, texto `color-texto-sobre-alerta` | `alert-triangle` | Bloqueo que impide continuar. Máximo uno por vista |

## Estados

Estático. Si se puede descartar, el botón de cerrar (`x`, solo icono) cumple los [estados comunes](README.md#estados-comunes).

## Tokens

`color-fondo-superficie`, `color-fondo-alerta`, `color-borde-fuerte`, `color-texto-exito`, `color-texto-aviso`, `color-texto-alerta`, `color-texto-sobre-alerta`, `borde-grosor-base`, `borde-radio-ninguno`, `espacio-4`, `medida-icono-sm`, `fuente-*`.

## Relaciones

Base del patrón de [estados del sistema](../patrones/estados-sistema.md). El resumen de errores de un formulario es un aviso Error con enlaces a cada campo ([formularios](../patrones/formularios.md)).

## Accesibilidad

- Resultado de una acción: `role="status"` (éxito, información) o `role="alert"` (error, crítico), presente en el DOM antes de insertar el texto.
- El color nunca es el único indicador: título + icono.
- No desaparece solo: el usuario lo cierra o cambia de vista.

## Código

`frontend/src/componentes/Aviso.astro`, props `variante`, `titulo`, `texto`, `accion`, `descartable`.
