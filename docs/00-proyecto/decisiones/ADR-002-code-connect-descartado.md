---
id: ADR-002
titulo: Code Connect de Figma descartado
estado: aprobado
depende_de: [D-14, ADR-001]
---

# ADR-002: Code Connect de Figma descartado

## Contexto

D-14 planteaba vincular los componentes de Figma con el código mediante Code Connect: aporta precisión, pero exige mantenimiento.

## Opciones consideradas

1. Mantener Code Connect sincronizado con cada componente.
2. **Descartarlo.**

## Decisión

Opción 2. Con [ADR-001](ADR-001-figma-fuente-extraccion.md), Figma solo se lee una vez: no habrá componentes de Figma que mantener vinculados.

## Consecuencias

- La correspondencia diseño ↔ código vive en el catálogo `docs/07-diseno/componentes/`: cada ficha enlaza a su componente `.astro`.
- No se instalan ni mantienen archivos `.figma.ts`.
