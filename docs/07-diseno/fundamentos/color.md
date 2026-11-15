---
id: fund-color
titulo: Fundamento — Color
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Color

Paleta de cinco colores de marca (guía brutalista `86:70` y ficha de marca `35:29`). Los valores viven en [tokens](../tokens.md#color--rol); aquí están las reglas.

## Paleta y papel de cada color

| Color de marca | Papel | Token de rol |
|---|---|---|
| Lienzo `#EBEBFF` | Base fría y limpia; deja que los elementos brutales tomen protagonismo | `color-fondo-lienzo`, `color-texto-invertido` |
| Navy `#262757` | Títulos y tipografía pesada, bordes de alto contraste, botones brutalistas | `color-texto-principal`, `color-borde-fuerte`, `color-fondo-invertido` |
| Lavanda `#E1C9E3` | Superficies de alta jerarquía, estado activo, áreas de interacción | `color-fondo-destacado`, `color-borde-tecnico` |
| Naranja reactivo `#FF5A1F` | Máxima atención: hover de acción, alertas críticas, acción urgente | `color-fondo-alerta` |
| Tinta `#231F20` | Texto de párrafos; texto sobre naranja | `color-texto-cuerpo`, `color-texto-sobre-alerta` |

## Reglas

1. **Proporción:** lienzo y superficie dominan (~70 %), navy y tinta estructuran (~20 %: texto, bordes), lavanda marca jerarquía (~8 %), naranja es un acento puntual (≤2 % por pantalla). Si una pantalla tiene más de un foco naranja, sobra uno.
2. **El naranja nunca es texto ni borde informativo sobre fondos claros** (2,65:1). Como relleno lleva texto `color-texto-sobre-alerta`, ni blanco (3,12:1) ni lienzo (2,65:1), aunque Figma lo dibuje así (`86:179`, `161:695`). Para error o alerta en texto se usa `color-texto-alerta`.
3. **Lavanda sobre lienzo no transmite información** (1,31:1): las líneas técnicas y marcas de registro lavanda son decorativas. Un borde que delimita un control usa `color-borde-fuerte`.
4. **El estado nunca se comunica solo con color:** cada etiqueta de estado lleva texto, y la señal de color va junto a una palabra ([indicador-estado](../componentes/indicador-estado.md)).
5. **Superficies invertidas (navy):** texto `color-texto-invertido`, acentos lavanda, foco `color-foco-invertido`. Se usan en paneles de acceso, cabeceras de tabla y la etiqueta invertida.
6. **Éxito y aviso** son los únicos colores fuera de la marca; existen solo como texto o borde, nunca como relleno de superficie, para no romper la paleta.
7. **Texto: prosa en tinta, el resto en navy.** Párrafos, descripciones y texto de avisos y comentarios usan `color-texto-cuerpo`; títulos, etiquetas, botones, celdas, valores y navegación usan `color-texto-principal`. La tinta solo va sobre fondos claros (lienzo, blanco, lavanda): sobre navy la prosa usa `color-texto-invertido`.
8. **Acción principal en lavanda:** el botón primario se rellena con `color-fondo-destacado` y pasa a naranja solo en hover ([botón](../componentes/boton.md)). El relleno naranja con texto lienzo de las pantallas `erp` (`161:695`) no se adopta.
9. Duotono e imagen: solo lavanda + navy ([iconografía e imagen](iconografia-imagen.md)).

## Contraste verificado

WCAG 2.2 AA: 4,5:1 texto normal, 3:1 texto grande (≥24 px o ≥18,66 px en negrita) y componentes no textuales. Calculado con la fórmula de luminancia relativa de WCAG.

| Texto / elemento | Fondo | Razón | Resultado |
|---|---|---|---|
| Navy | Lienzo | 11,83 | AA texto |
| Navy | Fondo claro (blanco) | 13,91 | AA texto |
| Navy | Lavanda | 9,05 | AA texto |
| Lienzo | Navy | 11,83 | AA texto |
| Lavanda | Navy | 9,05 | AA texto |
| Tinta | Naranja | 5,23 | AA texto |
| Tinta | Lienzo | 13,86 | AA texto |
| Tinta | Fondo claro (blanco) | 16,30 | AA texto |
| Tinta | Lavanda | 10,61 | AA texto |
| Tinta | Navy | 1,17 | **No usar** |
| Navy | Naranja | 4,46 | Solo texto grande y no textual |
| Blanco | Naranja | 3,12 | **No usar** para texto normal |
| Naranja | Lienzo | 2,65 | **No usar** (ni texto ni borde informativo) |
| Naranja | Navy | 4,46 | Solo no textual (señal, anillo) |
| Secundario de Figma `#5D5F89` | Lienzo / blanco / lavanda | 5,16 / 6,06 / 3,95 | **No usar**: falla sobre lavanda |
| Secundario `#4A4B7D` | Lienzo / blanco / lavanda | 6,89 / 8,10 / 5,27 | AA texto |
| Alerta `#9A3009` | Lienzo / blanco / lavanda | 6,38 / 7,50 / 4,88 | AA texto |
| Éxito `#14633A` | Lienzo / blanco / lavanda | 6,21 / 7,30 / 4,75 | AA texto |
| Aviso `#6E4700` | Lienzo / blanco / lavanda | 6,96 / 8,19 / 5,33 | AA texto |
| Anillo de foco navy | Lienzo / blanco | 11,83 / 13,91 | AA no textual |
| Anillo de foco lavanda | Navy | 9,05 | AA no textual |
| Borde técnico lavanda | Lienzo | 1,31 | Solo decorativo |

## Por qué

- La guía define el contraste como principio ("Contraste puro", `86:69`): lavanda + navy generan la tensión audiófila; el naranja reactivo es el único color "caliente" y por eso se reserva.
- Figma tiene variables de color (`color/brand/primary`, `color/text/primary` = tinta, `color/text/secondary` = navy, `color/surface/default` = lienzo, `color/border/default` = navy; `86:20`, `161:705`). El brief las renombra por rol: `color/text/primary` (tinta) es `color-texto-cuerpo` y `color/text/secondary` (navy) es `color-texto-principal`.
- **Decisiones del usuario (2026-11-15):** párrafos en tinta y títulos en navy, como en Figma; acción principal en lavanda con naranja solo en hover, porque el naranja con texto lienzo de las pantallas `erp` da 2,65:1 y no pasa AA.
- `#4A4B7D` es el gris azulado de las pantallas (`#5D5F89`, `161:702`) oscurecido hasta pasar AA sobre lavanda.
- `#9A3009`, `#14633A` y `#6E4700` son decisión del brief aprobada por el usuario (2026-11-15): Figma no define estados semánticos y el naranja de marca no pasa AA como texto.
