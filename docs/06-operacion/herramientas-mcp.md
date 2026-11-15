---
id: operacion-herramientas-mcp
titulo: Herramientas del agente — MCP y skills
estado: aprobado
depende_de: [agentes-equipo, D-13, D-14]
---

# Herramientas del agente: MCP y skills

## Servidores MCP

Regla: **una sola entrada por servidor**. Verificación: `claude mcp list` y `/mcp` dentro de la sesión.

| MCP | Origen | Uso | Restricciones |
|---|---|---|---|
| Supabase **local** | `.mcp.json` del proyecto: `http://localhost:45621/mcp` | Inspeccionar el esquema y consultar la base de desarrollo | Requiere Docker Desktop en marcha y `supabase start`. Ofrece menos herramientas que el remoto y no usa OAuth. El modo de solo lectura no está verificado en local: **nunca DDL por MCP**, los cambios de esquema van como migraciones en `supabase/` |
| Figma | Conector de claude.ai o plugin `figma@claude-plugins-official` | Solo la fase 2: extracción única al brief ([ADR-001](../00-proyecto/decisiones/ADR-001-figma-fuente-extraccion.md)) | Solo `disenador-ui`, solo lectura |
| Playwright | Plugin de usuario | Capturas, E2E, verificación visual y de accesibilidad | Solo desarrollo y pruebas |
| Context7 | Plugin de usuario | Documentación actualizada de Astro, FastAPI, Supabase y `uv` | Consulta; no reemplaza `docs/` |
| GitHub | CLI `gh` | Issues y PR | Sin merge automático |

No hay suscripción a Supabase: no existe proyecto alojado y no se usa el MCP remoto (`mcp.supabase.com`). Ninguna credencial se versiona; el validador lo comprueba sobre `.mcp.json`.

## Matriz MCP por rol

Cada agente declara su lista permitida en `tools` ([equipo](../04-agentes/equipo.md)); lo que no figura, no lo ve.

| MCP | leader | disenador-ui | dev-backend | dev-frontend | dev-audit | documentador |
|---|---|---|---|---|---|---|
| Supabase local | Sí | — | Sí | — | Sí | — |
| Figma (lectura) | — | Fase 2 | — | — | — | — |
| Playwright | — | — | — | Sí | Sí | — |
| Context7 | Sí | — | Sí | Sí | Sí | — |
| claude-mem | Escritura | — | — | — | — | — |

## Skills externas

| Skill | Origen | Rol | Estado |
|---|---|---|---|
| Plugin de Figma (`figma:figma-design-to-code`) | Plugin oficial | disenador-ui (fase 2) | Instalado (usuario) |
| `frontend-design` | Plugin oficial de Anthropic | dev-frontend | Instalado (usuario) |
| `supabase/agent-skills@supabase-postgres-best-practices` | skills.sh (oficial, 486K instalaciones) | dev-backend | Candidata (fase 3) |
| `supabase/agent-skills@supabase` | skills.sh (oficial, 366K) | dev-backend | Candidata (fase 3) |
| `fastapi/fastapi@fastapi` | skills.sh (oficial, 15.5K) | dev-backend | Candidata (fase 3) |
| `astrolicious/agent-skills@astro` | skills.sh (19.6K) | dev-frontend | Candidata (fase 4) |

Las candidatas se verificaron el 2026-11-14 y se instalan con aprobación del usuario (`npx skills add <owner/repo@skill>`). Cuándo usar cada una: [skills-por-fase](../04-agentes/skills-por-fase.md).

## Skills propias del proyecto

En `.claude/skills/<nombre>/SKILL.md`, en español; cada una enlaza a sus specs en vez de copiarlas.

| Skill | Procedimiento | Rol | Autor · fase |
|---|---|---|---|
| `aplicar-brief` | Reglas del brief en ≤3.000 caracteres y enlaces a `07-diseno/` | disenador-ui, dev-frontend | disenador-ui · 2 |
| `disenar-pantalla` | RF → composición con componentes del catálogo → estados → copy → accesibilidad | disenador-ui | disenador-ui · 2 |
| `crear-componente` | Componente `.astro` con tokens, variantes, estados, prueba y enlace a su ficha | dev-frontend | leader · 5 |
| `crear-isla` | Isla `.astro` con Web Component, tokens y prueba | dev-frontend | leader · 5 |
| `crear-slice-backend` | Estructura `dominio/aplicacion/infraestructura` de un caso de uso con pruebas base | dev-backend | leader · 5 |
| `crear-migracion` | Migración SQL versionada con RLS que actualiza `modelo-datos.md` | dev-backend | leader · 5 |
| `auditar-entrega` | Criterios de [dev-audit](../04-agentes/dev-audit.md) en formato de informe | dev-audit | leader · 5 |
| `crear-tarea` | TAREA en [formato estándar](../05-protocolos/implementacion.md#formato-de-tarea) a partir de un RF | leader | leader · 5 |

Regla: si un procedimiento se repite dos veces, se convierte en skill.
