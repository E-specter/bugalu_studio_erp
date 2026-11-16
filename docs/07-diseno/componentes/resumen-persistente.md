---
id: comp-resumen-persistente
titulo: Componente — Resumen persistente
estado: borrador
depende_de: [diseno-tokens, comp-panel]
---

# Resumen persistente

"Resumen persistente" del flujo de contratación (`141:28788`: cabecera con título y estado + "Datos del resumen" con pares etiqueta/valor). Columna fija que acumula lo elegido: servicio, fecha, modalidad, importe.

## Anatomía

1. Contenedor de `medida-columna-lateral`, `color-fondo-superficie`, `borde-grosor-base`, `sombra-plana`, relleno `espacio-5`.
2. Cabecera: título (`fuente-familia-titulo`) + [etiqueta](etiqueta-tecnica.md) de estado ("BORRADOR"), regla `borde-grosor-fino`.
3. Datos: lista de pares — etiqueta (`fuente-tamano-pequeno`, `color-texto-secundario`) / valor (`fuente-tamano-base`, alineado a la derecha si es cifra), filas separadas por `borde-grosor-fino`.
4. Total opcional al pie: `fuente-tamano-titulo-sm`, `tabular-nums`.

## Variantes

| Variante | Uso |
|---|---|
| Solicitud | Flujo de contratación y reserva |
| Ficha | Lateral de detalle de proyecto o pago (datos clave del objeto) |

En móvil (< `punto-quiebre-escritorio`) deja de ser lateral: va como bloque `<aside>` normal tras el cierre del paso, sin plegar (decisión TAREA-RF04-6: el `<details>` "Ver resumen" sobre la barra escondía lo elegido y no aportaba, porque el principal de cada paso ya muestra el precio cuando importa).

## Estados

Estático; se actualiza al cambiar de paso (recarga del servidor). Dato aún no elegido: "—" en `color-texto-secundario`.

## Tokens

`medida-columna-lateral`, `color-fondo-superficie`, `color-borde-fuerte`, `color-texto-secundario`, `borde-grosor-base`, `borde-grosor-fino`, `sombra-plana`, `espacio-5`, `fuente-*`.

## Relaciones

En el [flujo por pasos](../patrones/flujo-por-pasos.md). Los datos usan la misma estructura que la [métrica](metrica.md) (`<dl>`).

## Accesibilidad

- `<aside aria-labelledby>` con `<dl>` para los pares.
- `position: sticky` solo en escritorio y sin tapar contenido con zoom al 200 %.

## Código

`frontend/src/componentes/ResumenPersistente.astro`, props `titulo`, `estado`, `datos`, `total`, `variante`. Mientras solo lo use la reserva (cuyos datos pinta la isla), vale componerlo con [panel](panel.md) Lateral + [etiqueta](etiqueta-tecnica.md) + `<dl>` siguiendo esta anatomía; el componente se extrae con el segundo flujo (contratación, [RF-15](../../03-requerimientos/RF-15.md)). Lo que no se negocia: hueco `espacio-3` entre la etiqueta y los datos, "—" en `color-texto-secundario` y el total al pie en `fuente-tamano-titulo-sm` con `tabular-nums`, separado por `borde-grosor-fino`.
