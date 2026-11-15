---
id: comp-indicador-estado
titulo: Componente — Indicador de estado
estado: borrador
depende_de: [diseno-tokens, fund-color]
---

# Indicador de estado

Señal + texto. Capas "Sincronización" (`161:640`), "Estado de guardado" (`141:28605`), "Estado técnico" (`169:4267`), "Estado de revisión" (`145:3617`) y el punto del widget de versión (`86:191`). Comunica el estado del sistema o del objeto en una línea.

## Anatomía

1. Señal: círculo de `medida-senal` en el color de la variante.
2. Texto de estado: `fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas ("SINCRONIZADO", "GUARDADO HACE 1 MIN").
3. Dato opcional a la derecha (fecha límite, hora).

## Variantes

| Variante | Forma | Uso |
|---|---|---|
| En línea | Señal + texto, sin caja | Cabecera (sincronización, guardado) |
| Barra | Caja de ancho completo: `borde-grosor-fino`, relleno `espacio-3`, mensaje + dato a la derecha | Pie de vista: estado de la revisión, estado técnico del proyecto |

| Tono | Señal | Ejemplos |
|---|---|---|
| Correcto | `color-texto-exito` | Sincronizado, guardado, validado |
| Pendiente | `color-texto-aviso` | Guardando, en revisión |
| Problema | `color-fondo-alerta` sobre fondo claro con texto `color-texto-alerta` | Sin conexión, error al guardar |
| Neutro | `color-texto-secundario` | Borrador, sin cambios |

## Estados

Estático. La señal "activa" (sincronizando) parpadea con `movimiento-duracion-bucle` ([movimiento](../fundamentos/movimiento.md)); con movimiento reducido queda fija.

## Tokens

`medida-senal`, `color-texto-exito`, `color-texto-aviso`, `color-texto-alerta`, `color-fondo-alerta`, `color-texto-secundario`, `borde-grosor-fino`, `espacio-3`, `fuente-familia-tecnica`, `fuente-tamano-micro`, `movimiento-duracion-bucle`.

## Relaciones

En [cabecera-app](cabecera-app.md), [tarjeta-version](tarjeta-version.md), [pasos](pasos.md). Para estados de objeto en tablas, usar [etiqueta-tecnica](etiqueta-tecnica.md).

## Accesibilidad

- El texto es obligatorio; la señal es `aria-hidden="true"`.
- Si cambia sin acción del usuario (guardado automático, sincronización), el contenedor lleva `role="status"`.

## Código

`frontend/src/componentes/IndicadorEstado.astro`, props `variante` (`linea|barra`), `tono`, `texto`, `dato`.
