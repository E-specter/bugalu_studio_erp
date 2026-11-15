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
| Navy `#262757` | Tipografía pesada, bordes de alto contraste, botones brutalistas | `color-texto-principal`, `color-borde-fuerte`, `color-fondo-invertido` |
| Lavanda `#E1C9E3` | Superficies de alta jerarquía, estado activo, áreas de interacción | `color-fondo-destacado`, `color-borde-tecnico` |
| Naranja reactivo `#FF5A1F` | Máxima atención: hover de acción, alertas críticas, acción urgente | `color-fondo-alerta` |
| Tinta `#231F20` | Texto sobre naranja | `color-texto-sobre-alerta` |

## Reglas

1. **Proporción:** lienzo y superficie dominan (~70 %), navy estructura (~20 %: texto, bordes), lavanda marca jerarquía (~8 %), naranja es un acento puntual (≤2 % por pantalla). Si una pantalla tiene más de un foco naranja, sobra uno.
2. **El naranja nunca es texto ni borde informativo sobre fondos claros** (2,65:1). Como relleno lleva texto `color-texto-sobre-alerta`, no blanco (3,12:1). Para error o alerta en texto se usa `color-texto-alerta`.
3. **Lavanda sobre lienzo no transmite información** (1,31:1): las líneas técnicas y marcas de registro lavanda son decorativas. Un borde que delimita un control usa `color-borde-fuerte`.
4. **El estado nunca se comunica solo con color:** cada etiqueta de estado lleva texto, y la señal de color va junto a una palabra ([indicador-estado](../componentes/indicador-estado.md)).
5. **Superficies invertidas (navy):** texto `color-texto-invertido`, acentos lavanda, foco `color-foco-invertido`. Se usan en paneles de acceso, botón secundario y cabeceras de tabla.
6. **Éxito y aviso** son los únicos colores fuera de la marca; existen solo como texto o borde, nunca como relleno de superficie, para no romper la paleta.
7. Duotono e imagen: solo lavanda + navy ([iconografía e imagen](iconografia-imagen.md)).

## Contraste verificado

WCAG 2.2 AA: 4,5:1 texto normal, 3:1 texto grande (≥24 px o ≥18,66 px en negrita) y componentes no textuales. Calculado con la fórmula de luminancia relativa de WCAG.

| Texto / elemento | Fondo | Razón | Resultado |
|---|---|---|---|
| Navy | Lienzo | 11,83 | AA texto |
| Navy | Superficie blanca | 13,91 | AA texto |
| Navy | Lavanda | 9,05 | AA texto |
| Lienzo | Navy | 11,83 | AA texto |
| Lavanda | Navy | 9,05 | AA texto |
| Tinta | Naranja | 5,23 | AA texto |
| Navy | Naranja | 4,46 | Solo texto grande y no textual |
| Blanco | Naranja | 3,12 | **No usar** para texto normal |
| Naranja | Lienzo | 2,65 | **No usar** (ni texto ni borde informativo) |
| Naranja | Navy | 4,46 | Solo no textual (señal, anillo) |
| Secundario `#4A4B7D` | Lienzo / blanco / lavanda | 6,89 / 8,10 / 5,27 | AA texto |
| Alerta `#9A3009` | Lienzo / blanco / lavanda | 6,38 / 7,50 / 4,88 | AA texto |
| Éxito `#14633A` | Lienzo / blanco / lavanda | 6,21 / 7,30 / 4,75 | AA texto |
| Aviso `#6E4700` | Lienzo / blanco / lavanda | 6,96 / 8,19 / 5,33 | AA texto |
| Anillo de foco navy | Lienzo / blanco | 11,83 / 13,91 | AA no textual |
| Anillo de foco lavanda | Navy | 9,05 | AA no textual |
| Borde técnico lavanda | Lienzo | 1,31 | Solo decorativo |

## Por qué

- La guía define el contraste como principio ("Contraste puro", `86:69`): lavanda + navy generan la tensión audiófila; el naranja reactivo es el único color "caliente" y por eso se reserva.
- `#4A4B7D`, `#9A3009`, `#14633A` y `#6E4700` son **inferidos**: la guía no define texto secundario ni estados semánticos, y el naranja de marca no pasa AA como texto. Se eligieron dentro de la familia navy/naranja y validados sobre las tres superficies claras.
