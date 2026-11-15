---
id: fund-espaciado-reticula
titulo: Fundamento — Espaciado y retícula
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Espaciado y retícula

Valores en [tokens](../tokens.md#espacio). Medidas tomadas de las pantallas de `landing-page` y `erp` (1440 × 1080 en escritorio, 390 de ancho en móvil).

## Unidades

Las medidas son relativas para que la interfaz crezca con el tamaño de letra del usuario y con el zoom (WCAG 1.4.4 y 1.4.10). Decisión del **usuario**, 2026-11-15.

| Tokens | Unidad | Por qué |
|---|---|---|
| `fuente-tamano-*` | `rem` (y `clamp()` con `rem` + `vw` en el titular) | Respetan el tamaño de letra del usuario |
| `espacio-*`, `medida-*` | `rem` | Crecen con el texto que contienen |
| `punto-quiebre-*` | `em` | Las consultas de medios en `em` reaccionan al tamaño de letra y al zoom |
| `fuente-interlineado-*` | sin unidad | Proporcional al tamaño de la fuente |
| `borde-*`, `sombra-plana`, `efecto-*` | `px` | Líneas técnicas: si crecen pierden su carácter |

Ningún componente escribe px fuera de estas excepciones; el px que acompaña a cada token en [tokens](../tokens.md) es solo referencia.

## Escala

Base de `0.25rem` (4 px con la raíz de 16 px; `espacio-N` = N × `0.25rem`). Las pantallas de Figma usan valores intermedios (14, 18, 22, 30, 34 px); se **normalizan** al paso más cercano de la escala: 14 → `espacio-4`, 18 → `espacio-4`, 22 → `espacio-6`, 30/34 → `espacio-8`. Ningún componente usa un valor fuera de la escala.

| Relación | Token |
|---|---|
| Icono ↔ su texto | `espacio-2` |
| Elementos de un mismo grupo (etiqueta y entrada, título y ayuda) | `espacio-2` |
| Campos en fila, métricas, columnas del tablero | `espacio-3` |
| Relleno de control, celda y métrica | `espacio-4` |
| Relleno de panel | `espacio-5` |
| Entre paneles o columnas del contenido | `espacio-6` |
| Margen del contenido de app; hueco de la retícula de la landing | `espacio-8` |
| Margen lateral de página ≥ 1440 | `espacio-12` |
| Entre secciones de la landing | `espacio-20` |

Regla de proximidad: el espacio **dentro** de un grupo es siempre menor que el espacio **entre** grupos.

## Retícula

| Contexto | Estructura | Origen |
|---|---|---|
| Landing | Contenedor `medida-contenedor-max`, márgenes `espacio-12`, 3 columnas iguales con hueco `espacio-8` | `48:100`, `48:159` |
| App de escritorio | Cabecera `medida-cabecera-escritorio` + navegación lateral `medida-nav-lateral` + contenido con margen `espacio-8` | `161:609`, `145:2885` |
| Contenido de app | 12 columnas fluidas, hueco `espacio-6`; métricas en 4 columnas con hueco `espacio-3` | `161:688` |
| Principal + lateral | Contenido flexible + columna `medida-columna-lateral` (≈ 70/30) | `161:688`, `141:28788` |
| Flujo de contratación | Sin navegación lateral: margen `espacio-12`, formulario + resumen persistente | `141:28605` |
| Móvil | Una columna, margen `espacio-4`; métricas en 2 columnas | `169:4267` |

**Proporción áurea:** la ficha de marca (`35:29`) pide retícula φ (0,618 : 1 : 0,618). Se aplica a composiciones editoriales de la landing (texto 38 % / imagen 62 %, `48:88`); las vistas operativas usan la división 70/30 de las pantallas.

## Adaptabilidad

Puntos de quiebre en [brief](../brief.md#adaptabilidad).

| Rango | Navegación | Retícula |
|---|---|---|
| < `punto-quiebre-tableta` | Cabecera móvil + [navegación táctil](../componentes/navegacion-tactil.md) | 1 columna; lateral pasa debajo |
| Tableta | Igual que móvil | 2 columnas; métricas en 2 |
| ≥ `punto-quiebre-escritorio` | Cabecera + [navegación lateral](../componentes/navegacion-lateral.md) | 12 columnas; principal + lateral |
| ≥ `punto-quiebre-amplio` | Igual | Contenido limitado a `medida-contenedor-max`, centrado |

## Reglas

1. Primero móvil: el CSS base es el de una columna y las consultas `min-width` añaden columnas.
2. Las tablas no se encogen por debajo de su contenido: en móvil pasan a lista de tarjetas ([tabla](../componentes/tabla.md)).
3. Los controles táctiles miden al menos `medida-control-tactil` de alto y área.
4. Retícula con CSS Grid (`grid-template-columns`), sin posiciones absolutas salvo decoración (marcas de registro).
