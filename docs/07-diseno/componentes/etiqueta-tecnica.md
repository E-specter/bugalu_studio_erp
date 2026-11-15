---
id: comp-etiqueta-tecnica
titulo: Componente — Etiqueta técnica
estado: borrador
depende_de: [diseno-tokens, fund-forma-elevacion]
---

# Etiqueta técnica

`BrutalistTag` de la guía (`86:170`: "SALA ÚNICA", "LA MOLINA", "LIVE"; *Padding 6px/12px, Corner 4px*, `86:184`) y la capa "Etiqueta técnica" de las pantallas (190 apariciones). Marca estado, categoría o filtro con un texto corto.

## Anatomía

1. Contenedor: `borde-grosor-fino` en `color-borde-fuerte`, `borde-radio-etiqueta`, relleno `espacio-1-5` / `espacio-3`. Sin sombra.
2. Texto: `fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas.
3. Señal opcional a la izquierda (`medida-senal`) cuando es un estado en vivo ("LIVE", sincronizado).

## Variantes

| Variante | Fondo | Texto / borde | Uso |
|---|---|---|---|
| Neutra | transparente | `color-texto-principal` | Categoría, metadato (sala, género, formato) |
| Activa | `color-fondo-destacado`, borde `borde-grosor-base` | `color-texto-principal` | Estado vigente ("V3 MASTER ACTIVO"), filtro seleccionado |
| Invertida | `color-fondo-invertido` | `color-texto-invertido` | Sobre superficies claras muy cargadas; código de solicitud |
| Éxito | transparente | `color-texto-exito` | Validado, aprobado, confirmada |
| Aviso | transparente | `color-texto-aviso` | Pendiente, pre-reservada, en revisión |
| Alerta | transparente, borde `borde-grosor-base` | `color-texto-alerta` | Rechazado, vencido, cancelada, prioridad alta. Naranja oscuro y no de marca: puede repetirse en una tabla ([color](../fundamentos/color.md#reglas), regla 1) |
| Filtro | Neutra (sin aplicar) / Activa + icono `check` (aplicado) | — | Enlace de filtro en tableros y tablas |

Correspondencia de estados del dominio: [estados de reserva](../../02-dominio/estados-reserva.md) → Aviso (Pre-reservada), Éxito (Confirmada, Finalizada), Activa (En curso), Alerta (Cancelada).

## Estados

Estática: no tiene estados interactivos. La variante **Filtro** es un enlace y cumple los [estados comunes](README.md#estados-comunes); el filtro aplicado lleva la variante Activa, el icono `check` (`medida-icono-sm`) antes del texto y `aria-current="true"` (es un enlace: `aria-pressed` es solo para botones). Así se distingue del inactivo por borde, icono y atributo, no solo por el relleno lavanda (1,31:1). En un formulario (etiquetado rápido de [formularios](../patrones/formularios.md)) el Filtro es una casilla nativa con este aspecto: marcada = Activa + `check`, sin ARIA extra.

## Tokens

`borde-grosor-fino`, `borde-grosor-base`, `borde-radio-etiqueta`, `color-borde-fuerte`, `color-fondo-destacado`, `color-fondo-invertido`, `color-texto-*`, `medida-icono-sm`, `espacio-1-5`, `espacio-3`, `fuente-familia-tecnica`, `fuente-tamano-micro`, `medida-senal`.

## Relaciones

Dentro de [tabla](tabla.md), [tarjeta-proyecto](tarjeta-proyecto.md), [tarjeta-version](tarjeta-version.md), [cabecera-app](cabecera-app.md), [archivo](archivo.md). La señal es la de [indicador-estado](indicador-estado.md).

## Accesibilidad

- El texto de la etiqueta es el estado: nunca una etiqueta vacía con solo color.
- Etiqueta de estado: `<span>`; filtro: `<a href="?estado=...">`.
- Si el estado cambia en vivo, el contenedor padre anuncia el cambio (`aria-live="polite"`).

## Código

`frontend/src/componentes/EtiquetaTecnica.astro`, props `variante`, `texto`, `href`, `senal`.
