---
id: operacion-herramientas-mcp
titulo: Herramientas del agente — MCP y skills
estado: borrador
depende_de: [D-13, D-14]
---

# Herramientas del agente: MCP y skills

## Servidores MCP

Configurados en `.mcp.json` (alcance de proyecto, sin credenciales). Verificación: `claude mcp list` y `/mcp` dentro de la sesión.

| MCP | Uso | Restricciones |
|---|---|---|
| Figma (oficial, remoto) | Leer frames, componentes, variables y capturas; generar reglas del sistema de diseño. Alternativa con skills: `claude plugin install figma@claude-plugins-official` | Solo lectura salvo aprobación del usuario |
| Supabase (oficial, remoto) | Inspeccionar esquema, ejecutar SQL, revisar logs, ejecutar asesores de seguridad y rendimiento, generar tipos | Limitado por `project_ref` y en solo lectura. Solo el proyecto de desarrollo; nunca producción. Los cambios de esquema van como migraciones en `supabase/` |
| Playwright (Microsoft) | Navegar la app local, capturas, E2E, verificación visual y de accesibilidad | Solo desarrollo y pruebas |
| Context7 (opcional) | Documentación actualizada de Astro, FastAPI, Supabase y `uv` | Consulta; no reemplaza `docs/` |
| GitHub (opcional) | Issues, PR y revisiones | No incluido en `.mcp.json`; se usa la CLI `gh`. Sin merge automático |

## Variables de entorno requeridas

| Variable | Uso |
|---|---|
| `SUPABASE_PROJECT_REF` | Proyecto de **desarrollo** al que se limita el MCP de Supabase |

Figma, Supabase y Context7 se autentican por OAuth desde `/mcp`. Ninguna credencial se versiona; el validador lo comprueba sobre `.mcp.json`.

## Matriz MCP por rol

| MCP | leader | dev_backend | dev_frontend | dev_audit |
|---|---|---|---|---|
| Figma | Lectura | — | Lectura | Lectura |
| Supabase | Lectura | Lectura (desarrollo) | — | Lectura (asesores) |
| Playwright | — | — | Sí | Sí |
| Context7 | Sí | Sí | Sí | Sí |
| GitHub | Sí | Lectura | Lectura | Lectura + comentarios |

## Skills externas

| Skill | Origen | Rol | Estado |
|---|---|---|---|
| Skills de Figma (implementar diseño, reglas del sistema de diseño, Code Connect) | Plugin oficial de Figma | dev_frontend, leader | Instalado (usuario) |
| `frontend-design` | Plugin oficial de Anthropic | dev_frontend | Instalado (usuario) |
| `supabase/agent-skills@supabase-postgres-best-practices` | skills.sh (oficial, 486K instalaciones) | dev_backend | Candidata |
| `supabase/agent-skills@supabase` | skills.sh (oficial, 366K) | dev_backend | Candidata |
| `fastapi/fastapi@fastapi` | skills.sh (oficial, 15.5K) | dev_backend | Candidata |
| `astrolicious/agent-skills@astro` | skills.sh (19.6K) | dev_frontend | Candidata |

Las candidatas se verificaron el 2026-11-14 y se instalan con aprobación del usuario: `npx skills add <owner/repo@skill>`.

## Skills propias del proyecto (fase 5)

En `.claude/skills/<nombre>/SKILL.md`, en español, cada una remite a sus specs.

| Skill | Procedimiento | Rol |
|---|---|---|
| `crear-slice-backend` | Genera la estructura `dominio/aplicacion/infraestructura` de un caso de uso con pruebas base | dev_backend |
| `crear-migracion` | Crea una migración SQL versionada con políticas RLS y actualiza `modelo-datos.md` | dev_backend |
| `crear-isla` | Genera una isla `.astro` con Web Component, tokens y prueba | dev_frontend |
| `implementar-pantalla-figma` | Ejecuta los pasos 3–4 del [flujo diseño → código](../07-diseno/figma.md#flujo-diseno-codigo) | dev_frontend |
| `sincronizar-tokens` | Lee variables de Figma y actualiza `tokens.css` y [tokens](../07-diseno/tokens.md) | dev_frontend |
| `auditar-entrega` | Aplica los criterios de [dev-audit](../04-agentes/dev-audit.md) y emite el informe | dev_audit |
| `crear-tarea` | Redacta una tarea con el [formato TAREA](../05-protocolos/implementacion.md#formato-de-tarea) a partir de un RF | leader |

Regla: si un procedimiento se repite dos veces, se convierte en skill.
