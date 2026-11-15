---
id: fund-logotipo
titulo: Fundamento — Logotipo y variantes
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Logotipo y variantes

Logo "icono + texto" de Bugalú Studio (ficha de marca `35:29`, *Taller de marca Bugalú*). Tres símbolos en Figma, página `references`:

| Variante | Símbolo | Proporción | Uso |
|---|---|---|---|
| Icono | `logo icon` (`58:2`, 36 × 36) | 1 : 1 | Favicon, avatar de la app, espacios < `medida-control-grande` de alto |
| Texto | `logo texto` (`40:150`, 93,9 × 30,2) | ≈ 3,1 : 1 | Pies y bandas horizontales donde el icono ya está presente |
| Icono + texto (apilado) | `logo icon+texto` (`58:77`, 93,9 × 86) | ≈ 1,09 : 1 | Logo principal: cabeceras, accesos, guía |

## Placa de marca

En las cabeceras de la app el logo apilado va dentro de una **placa** (`161:611`, `169:5453`): marco cuadrado con `borde-grosor-base`, relleno `espacio-1-5`, seguido del nombre del sistema (producto + ruta) en [cabecera-app](../componentes/cabecera-app.md).

| Contexto | Alto de la placa | Origen |
|---|---|---|
| Escritorio | `medida-placa-marca` | `161:611` |
| Móvil | `medida-control-base` (42 px) | `169:5453` |

## Reglas

1. **Tamaño mínimo:** icono + texto a `medida-logo-min` de alto (el menor observado, placa móvil `169:5454`); por debajo se usa solo el icono, mínimo `medida-icono-md`.
2. **Área de respeto:** como mínimo `espacio-1-5` a cada lado dentro de la placa, y `espacio-4` fuera de ella respecto de cualquier otro elemento.
3. **Color:** navy (`color-texto-principal`) sobre fondos claros; lienzo (`color-texto-invertido`) sobre navy. Nunca naranja, nunca sobre fotografía sin superficie.
4. **No se deforma, rota, recorta ni se le aplican efectos** del catálogo (glitch, RGB): el logo es la única pieza que no se "brutaliza".
5. **Accesibilidad:** el logo que enlaza a inicio lleva `aria-label="Bugalú Studio, inicio"`; dentro de la placa junto al nombre del sistema es decorativo (`alt=""`).
6. **Eslogan:** "Converge y crea." en `fuente-familia-tecnica`, mayúsculas, junto al pie o al panel de acceso (`86:218`, `112:321`), nunca pegado al logo.

## Assets

Exportados de Figma el 2026-11-15 (TAREA-201b, `download_assets`):

| Variante | Archivo | Nodo | Caja |
|---|---|---|---|
| Icono | [logo-icono.svg](assets/logo-icono.svg) | `58:2` | 36 × 36 |
| Texto | [logo-texto.svg](assets/logo-texto.svg) | `40:150` | 94 × 31 |
| Icono + texto (apilado) | [logo-apilado.svg](assets/logo-apilado.svg) | `58:77` | 94 × 86 |

Limpieza aplicada a la exportación: se quitó el fondo `#1E1E1E` del marco y los rellenos navy (`#262757` en el icono, `#23275C` en el texto) pasan a `currentColor`, para que el color lo dé la regla 3. Los trazados no se tocaron.

**Pendiente del taller de marca:** el navy del texto del logo en Figma (`#23275C`) no coincide con el navy de marca (`#262757`). Lo resuelve el taller de marca; no afecta a la interfaz, que pinta el logo con `currentColor` (decisión del usuario, 2026-11-15).
