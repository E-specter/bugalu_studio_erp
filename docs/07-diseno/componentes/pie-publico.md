---
id: comp-pie-publico
titulo: Componente — Pie público
estado: borrador
depende_de: [diseno-tokens, patron-estructura-app, RF-16, RF-17]
---

# Pie público

Pie de las páginas que ve cualquiera: identifica al proveedor y enlaza siempre los textos legales y el Libro de Reclamaciones. La landing de Figma termina con un pie (`44:4`), sin contenido legal; este contenido es **decisión del brief** (TAREA-RF20-1) a partir de [ADR-012](../../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md) y [RF-16](../../03-requerimientos/RF-16.md).

## Anatomía

1. `<footer>` a ancho completo, fondo `color-fondo-lienzo`, regla superior `borde-grosor-base` `color-borde-fuerte`, relleno `espacio-6` / `espacio-4`, contenido limitado a `medida-contenedor-max`.
2. Fila de enlaces (`fuente-tamano-pequeno`, `color-texto-principal`, subrayados): Términos de uso · Política de privacidad · Condiciones de contratación · Textos legales · **Libro de Reclamaciones**. Separación `espacio-4`; en móvil se apilan.
3. Línea técnica (`fuente-familia-tecnica`, `fuente-tamano-micro`, `color-texto-secundario`): "AURAL PERÚ E.I.R.L. · RUC 20615656128 · AV. JAVIER PRADO ESTE 5920, LA MOLINA, LIMA" y "BUGALÚ STUDIO © 2026".

## Variantes

| Variante | Dónde | Diferencia |
|---|---|---|
| Completa | Landing (`layouts/LayoutPublico.astro`), [textos legales](../pantallas/RF-17-textos-legales.md#páginas-públicas) y estructura Flujo | Las dos filas |
| Acceso | Pie de la estructura Acceso ([acceso](../pantallas/RF-01-acceso.md#composición)) y de la estructura App | Solo la fila de enlaces, con `fuente-tamano-micro`. En Acceso va sobre el pie técnico existente; en App, al final de la columna de contenido (bajo `<main>`, fuera de él), con la regla superior y relleno `espacio-4` |

En App el pie sustituye a los enlaces legales que antes iban en el menú de la [cabecera](cabecera-app.md) (TAREA-RF16-1): la ley pide el enlace al Libro de Reclamaciones a la vista, no detrás de un menú ([RF-16](../../03-requerimientos/RF-16.md) CA-01).

## Estados

Estático. El enlace del Libro de Reclamaciones lleva al [formulario de RF-16](../pantallas/RF-16-formulario.md) con un clic, con el texto exacto "Libro de Reclamaciones" y sin icono (el texto manda).

## Tokens

`color-fondo-lienzo`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-secundario`, `borde-grosor-base`, `espacio-4`, `espacio-6`, `medida-contenedor-max`, `fuente-familia-tecnica`, `fuente-tamano-pequeno`, `fuente-tamano-micro`.

## Relaciones

Cierra las estructuras Landing, Flujo, Acceso y App ([estructura de app](../patrones/estructura-app.md)). Los enlaces a cada texto llevan a su versión vigente.

## Accesibilidad

- `<footer>` (punto de referencia `contentinfo`) con `<nav aria-label="Legal">` y `<ul>` de enlaces.
- Los enlaces superan `medida-control-tactil` de alto en móvil (relleno vertical), WCAG 2.5.8.
- La línea técnica es texto, no imagen.

## Código

`frontend/src/componentes/PiePublico.astro`, prop `variante` (`completa|acceso`). Rutas fijas: `/legal/terminos-de-uso/`, `/legal/privacidad/`, `/legal/condiciones-de-contratacion/`, `/legal/`, `/libro-de-reclamaciones/`.
