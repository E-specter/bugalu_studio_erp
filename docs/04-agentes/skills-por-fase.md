---
id: agentes-skills-por-fase
titulo: Skills por fase y rol
estado: aprobado
depende_de: [agentes-equipo]
---

# Skills por fase y rol

Lo **precargado** es fijo y está en [equipo](equipo.md). Esta tabla lista lo que se carga **bajo demanda** en cada fase. Una celda vacía (—) significa que el rol no participa en esa fase. `documentador` no usa skills: su celda indica la tarea.

| Fase | leader | disenador-ui | dev-backend | dev-frontend | dev-audit | documentador |
|---|---|---|---|---|---|---|
| 1 · Decisiones (D-01..D-04) | `superpowers:brainstorming`, `claude-mem:mem-search` | — | — | — | — | índice y estado de los ADR |
| 2 · Extracción del diseño | `find-skills`, `superpowers:writing-plans` | `figma:figma-design-to-code`, `impeccable` (extract), `design:accessibility-review` | — | — | Opus: revisión del brief | índice de `07-diseno` |
| 3 · Esqueleto backend | `find-skills`, `superpowers:writing-plans` | — | skills externas de FastAPI/Supabase si se aprueban; `superpowers:systematic-debugging` ante fallos | — | — | `montaje-local` |
| 4 · Esqueleto frontend | `find-skills`, `superpowers:writing-plans` | `design:design-critique` (revisión visual) | — | `frontend-design`, skill externa de Astro si se aprueba (`aplicar-brief` ya va precargada desde la fase 2) | `design:accessibility-review` | índice |
| 5 · Skills propias | `superpowers:writing-skills` | `aplicar-brief`, `disenar-pantalla` (las mantiene) | — | — | — | registro en `herramientas-mcp` |
| 6 · Auditoría del esqueleto | — | — | — | — | Opus: `security-review`, `design:accessibility-review` | changelog |
| 7 · Implementación por RF | `superpowers:brainstorming` (solo si hay preguntas abiertas), `superpowers:writing-plans` | `disenar-pantalla` | `crear-slice-backend`, `crear-migracion` | `crear-componente`, `crear-isla` | `auditar-entrega`; Opus en las compuertas | estado de los RF, changelog |

## find-skills

- `leader` lo ejecuta **una vez al inicio de cada fase**, solo para los huecos que esta tabla no cubre.
- Una candidata se aprueba si tiene más de 1.000 instalaciones y su fuente es oficial o conocida.
- Se registra en [herramientas-mcp](../06-operacion/herramientas-mcp.md#skills-externas) y se instala solo con aprobación del usuario.
- Al instalarla, se agrega a esta tabla. Si pasa a precargarse, también a [equipo](equipo.md).

## Skills que no se usan

`superpowers:subagent-driven-development` y `superpowers:executing-plans` no se cargan: el ciclo de ejecución está en [implementacion](../05-protocolos/implementacion.md#ciclo-de-bajo-consumo).
