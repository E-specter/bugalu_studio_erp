---
id: diseno-componentes
titulo: Catálogo de componentes (Figma ↔ código)
estado: borrador
depende_de: [diseno-figma, arq-frontend-islas]
---

# Catálogo de componentes

| Figma | Código |
|---|---|
| Componente `bugalu-calendario` | Isla `<bugalu-calendario>` en `islas/` |
| Componente `boton/primario` | `componentes/Boton.astro` con variante `primario` |

Reglas:
- Componente sin interactividad → `componentes/<Nombre>.astro`, sin JS.
- Componente interactivo → isla en `islas/` que registra `<bugalu-<nombre>>` ([frontend-islas](../01-arquitectura/frontend-islas.md)).

Catálogo completo: pendiente (fase 2).
