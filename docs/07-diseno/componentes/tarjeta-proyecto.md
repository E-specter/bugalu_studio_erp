---
id: comp-tarjeta-proyecto
titulo: Componente — Tarjeta de proyecto
estado: borrador
depende_de: [diseno-tokens, comp-etiqueta-tecnica]
---

# Tarjeta de proyecto

"Tarjeta de proyecto" del tablero (`161:1083`, 257 × 159) y "Proyecto" de los listados de proyectos activos (`161:609`, `145:2885`, `169:4267`): resumen (código, título, estado) + datos (responsable, siguiente hito, avance).

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base`, `sombra-plana-sm`, relleno `espacio-4`.
2. Resumen: código y prioridad (`fuente-familia-tecnica`, `fuente-tamano-micro`) + [etiqueta](etiqueta-tecnica.md) de estado; título del proyecto (`fuente-familia-titulo`, `fuente-tamano-base`); artista.
3. Datos: responsable ([avatar](avatar.md) pequeño + nombre), siguiente hito con fecha, [barra de progreso](barra-progreso.md).

## Variantes

| Variante | Diseño | Uso |
|---|---|---|
| Fila | Ancho completo; resumen arriba, datos en 3 columnas | Dashboard (proyectos activos) |
| Columna | Compacta, datos apilados | Columna del tablero de producción |

## Estados

Toda la tarjeta enlaza a la ficha del proyecto: [estados comunes](README.md#estados-comunes). Hover: fondo `color-fondo-lienzo`. Prioridad alta: código en [etiqueta](etiqueta-tecnica.md) Alerta. Atrasado: fecha del hito en `color-texto-alerta` con texto "Atrasado".

## Tokens

`color-fondo-superficie`, `color-fondo-lienzo`, `color-texto-alerta`, `borde-grosor-base`, `sombra-plana-sm`, `espacio-4`, `fuente-familia-tecnica`, `fuente-familia-titulo`, `fuente-tamano-micro`, `fuente-tamano-base`.

## Relaciones

En el tablero de [tablas y tableros](../patrones/tablas-y-tableros.md). Mover de etapa no es arrastre: es una acción en la ficha del proyecto ([RF-08](../../03-requerimientos/RF-08.md)).

## Accesibilidad

- `<article>` con el título como enlace (`<a>` que se extiende a toda la tarjeta con un pseudoelemento), no la tarjeta entera envuelta en `<a>`, para que el lector no lea todo como un enlace.
- La prioridad y el atraso se dicen en texto.

## Código

`frontend/src/componentes/TarjetaProyecto.astro`, props `codigo`, `titulo`, `artista`, `estado`, `responsable`, `hito`, `avance`, `href`, `variante`.
