---
id: comp-barra-progreso
titulo: Componente — Barra de progreso
estado: borrador
depende_de: [diseno-tokens]
---

# Barra de progreso

Capas "Progreso" / "Avance" (control de sala y de proyecto, `161:651`), "Límite de trabajo" del tablero (`161:1083`) y "Progreso de carga" (`161:1750`). Muestra cuánto falta como medidor, en la línea del principio "Rigor sonoro" (indicadores de nivel, `86:66`).

## Anatomía

1. Lectura superior opcional: canal a la izquierda y nivel a la derecha (`fuente-familia-tecnica`, `fuente-tamano-micro`), como un vúmetro.
2. Pista: alto `medida-progreso`, `borde-grosor-fino` `color-borde-fuerte`, fondo `color-fondo-superficie`.
3. Nivel: relleno `color-fondo-invertido`.
4. Texto de avance debajo ("3 de 5 etapas", "64 % · 42 MB de 66 MB").

## Variantes

| Variante | Nivel | Uso |
|---|---|---|
| Avance | `color-fondo-invertido` | Fase del proyecto, etapas |
| Carga | `color-fondo-invertido`; al terminar, texto en `color-texto-exito` | Subida de archivos |
| Límite | `color-fondo-destacado`; al superar el límite, `color-fondo-alerta` | Límite de trabajo por etapa del tablero |
| Indeterminada | Segmento que recorre la pista | Procesos sin porcentaje conocido (validación técnica) |

## Estados

Estático (no interactivo). Error de carga: el nivel se detiene, el texto pasa a `color-texto-alerta` con la causa.

## Tokens

`medida-progreso`, `borde-grosor-fino`, `color-borde-fuerte`, `color-fondo-superficie`, `color-fondo-invertido`, `color-fondo-destacado`, `color-fondo-alerta`, `color-texto-exito`, `color-texto-alerta`, `fuente-familia-tecnica`, `fuente-tamano-micro`.

## Relaciones

En [navegacion-lateral](navegacion-lateral.md) (control de sala), [carga-archivos](carga-archivos.md), [tarjeta-proyecto](tarjeta-proyecto.md), [pasos](pasos.md).

## Accesibilidad

- `<progress value max>` nativo con estilo propio, o `<meter>` para niveles con límite (variante Límite).
- Texto de avance visible: el lector de pantalla no depende de la barra.
- Indeterminada: `<progress>` sin `value`; movimiento anulado con `prefers-reduced-motion`.

## Código

`frontend/src/componentes/BarraProgreso.astro`, props `variante`, `valor`, `maximo`, `canal`, `texto`.
