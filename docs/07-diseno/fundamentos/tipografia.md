---
id: fund-tipografia
titulo: Fundamento — Tipografía
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Tipografía

Jerarquía de la guía brutalista (`86:100`, "Jerarquía tipográfica y escala"). Valores en [tokens](../tokens.md#tipografía).

## Familias y papel

| Familia | Token | Papel | Cuándo |
|---|---|---|---|
| Unbounded Heavy | `fuente-familia-display` | Display: la voz más fuerte | Titular hero de la landing y título de pantalla. Una vez por vista |
| Mona Sans Bold | `fuente-familia-titulo` | Estructura | Subtítulos de sección, títulos de panel, botones |
| Geist Regular | `fuente-familia-texto` | Lectura y datos | Párrafos, celdas, valores de campo |
| Geist Mono | `fuente-familia-tecnica` | Registro técnico | Códigos (`PRY-014`), nombres de archivo (`V3_MASTER.wav`), tiempos (`02:14`), índices `[01]`, etiquetas técnicas |

## Escala

| Nivel | Token de tamaño | Familia | Interlineado | Transformación |
|---|---|---|---|---|
| Hero | `fuente-tamano-hero` | display | `fuente-interlineado-display` | Mayúsculas |
| Display | `fuente-tamano-display` | display | `fuente-interlineado-display` | Mayúsculas |
| Título de pantalla | `fuente-tamano-titulo-lg` | display | `fuente-interlineado-titulo` | Mayúsculas |
| Subtítulo de sección | `fuente-tamano-titulo-md` | título | `fuente-interlineado-titulo` | Mayúsculas |
| Título de panel / tarjeta | `fuente-tamano-titulo-sm` | título | `fuente-interlineado-titulo` | Mayúsculas |
| Lectura | `fuente-tamano-lectura` | texto | `fuente-interlineado-lectura` | Ninguna |
| Interfaz | `fuente-tamano-base` | texto | `fuente-interlineado-interfaz` | Ninguna |
| Navegación, ayuda, ruta | `fuente-tamano-pequeno` | texto | `fuente-interlineado-interfaz` | Ninguna |
| Etiqueta técnica, columna, metadato | `fuente-tamano-micro` | técnica | `fuente-interlineado-interfaz` | Mayúsculas |

## Reglas

1. **Una sola voz display por vista.** Unbounded no se usa en párrafos, celdas ni botones.
2. **Mayúsculas solo en títulos, botones y etiquetas técnicas.** El contenido del usuario (nombres de proyecto, comentarios) se muestra tal cual se escribió.
3. **Patrones de registro técnico** (de la guía y los accesos): índice `[01]` o `[ 01 ]` antes del título de sección; prefijo `//` en etiquetas de campo en accesos (`// CORREO REGISTRADO`); código + título en identificadores (`PRY-014 · Vórtice sonoro`). Van en `fuente-familia-tecnica`.
4. **Cifras alineables:** importes, duraciones y contadores usan `font-variant-numeric: tabular-nums`; en tablas se alinean a la derecha.
5. **Tamaño mínimo:** `fuente-tamano-micro` (11 px) y solo en mayúsculas técnicas cortas; nunca para frases. Todo texto de lectura ≥ `fuente-tamano-base`.
6. **Escalado:** tamaños en `rem`; la interfaz debe soportar zoom al 200 % sin pérdida de contenido (WCAG 1.4.4) y espaciado de texto aumentado (1.4.12): sin alturas fijas en contenedores de texto.
7. **Longitud de línea:** párrafos de lectura con `max-inline-size: var(--medida-linea-lectura)`.
8. **Carga de fuentes:** autoalojadas en `frontend/public/`, `font-display: swap`, con el respaldo `system-ui` del token para que el cambio no mueva la retícula.

## Por qué

- La guía v1.0 (`86:106`) fija Unbounded / Mona Sans / Geist. La ficha de marca anterior (`35:29`, `12:40`) decía Mona Sans + Google Sans: **manda la guía**, que es la versión compilada.
- La ficha de marca pide una escala basada en φ (1,618). La guía la aproxima con 48 / 24 / 16; la escala de interfaz la completa con pasos compatibles (11–14 px) para la densidad del panel interno.
- **Verificado en Figma (TAREA-201b):** Geist Mono es la familia técnica (`86:154`, `86:164`; confirmada por el usuario); "Heavy" se dibuja con Unbounded Black, 900 (`86:108`); la guía rotula a 11 px en Geist Mono SemiBold (`86:164`) y no usa espaciado de letras.
- **Decisión del brief:** las pantallas `erp` bajan a 8–10 px (`161:702`, `161:690`); no se adopta, el mínimo es 11 px por legibilidad.
