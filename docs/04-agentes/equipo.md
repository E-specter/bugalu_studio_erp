---
id: agentes-equipo
titulo: Equipo de agentes — configuración
estado: aprobado
depende_de: [agente-leader, protocolo-implementacion]
---

# Equipo de agentes

Fuente única de la configuración de cada agente. `.claude/agents/<agente>.md` la refleja y `python scripts/validar_docs.py docs` comprueba que coincidan (modelo, effort, maxTurns y precarga). Si cambias un valor, cambias esta tabla y el frontmatter en el mismo commit.

## Sesión principal

| Agente | Modelo | Effort | maxTurns | Precarga | Bajo demanda | Rol |
|---|---|---|---|---|---|---|
| `leader` | opus | high | — | — | `superpowers:brainstorming`, `superpowers:writing-plans`, `find-skills`, `claude-mem:mem-search` | [Orquesta, decide, planifica](leader.md) |

## Subagentes

| Agente | Modelo | Effort | maxTurns | Precarga | Bajo demanda | Rol |
|---|---|---|---|---|---|---|
| `disenador-ui` | opus | high | 80 | `design:design-system`, `aplicar-brief` | `figma:figma-design-to-code` (solo fase 2), `impeccable`, `design:ux-copy`, `design:accessibility-review`, `design:design-critique` | [Brief, specs de pantalla y revisión visual](disenador-ui.md) |
| `dev-frontend` | sonnet | medium | 40 | `aplicar-brief`, `superpowers:verification-before-completion` | `frontend-design`, skill externa de Astro (si se aprueba) | [Componentes, islas, páginas](dev-frontend.md) |
| `dev-backend` | sonnet | medium | 40 | `superpowers:test-driven-development`, `superpowers:verification-before-completion` | `superpowers:systematic-debugging`, skills externas de FastAPI/Supabase (si se aprueban) | [Slices, API, migraciones](dev-backend.md) |
| `dev-audit` | sonnet | high | 25 | `ponytail:ponytail-review`, `superpowers:verification-before-completion` | `design:accessibility-review`, `security-review` | [Único revisor](dev-audit.md) |
| `documentador` | haiku | low | 15 | — | — | [Mantenimiento mecánico de docs](documentador.md) |

Qué se carga en cada fase: [skills-por-fase](skills-por-fase.md).

## Compuertas Opus

`leader` lanza `dev-audit` con `model: "opus"` en:
- el cierre de cada fase;
- la revisión del brief (fase 2);
- toda tarea de los módulos `identidad` o `pagos`, o que incluya una migración con políticas RLS.

En el resto de tareas, `dev-audit` usa Sonnet.

## Reglas comunes

- Ponytail `full`: lo inyecta su hook `SubagentStart` en cada subagente; no se precarga.
- Precarga mínima: cada skill precargada se paga completa en cada ejecución. El resto se carga bajo demanda con la herramienta Skill.
- Memoria: solo claude-mem, y solo `leader` escribe en ella. Los subagentes tienen bloqueados `work_state_write` y `save_memory` e informan en su ENTREGA. Ningún agente usa el campo `memory`.
- Figma: nadie escribe en él. Solo `disenador-ui` lo lee, durante la fase 2.
- Herramientas MCP por rol: [matriz](../06-operacion/herramientas-mcp.md#matriz-mcp-por-rol).
- Herramientas: **cada agente declara una lista permitida (`tools`)**, nunca bloqueos. Así, un conector nuevo de claude.ai queda excluido automáticamente.

## Verificado (2026-11-15, ejecuciones de prueba con Haiku)

- `skills` acepta nombres de plugin (`superpowers:…`, `ponytail:…`, `design:…`) y los precarga completos.
- `tools` acepta herramientas MCP por nombre individual y por servidor (`mcp__<servidor>__*`).
- Un comodín entre servidores (`mcp__claude_ai_*`) en `disallowedTools` **no tiene efecto**: por eso se usan listas permitidas.
- Figma llega en sesiones nuevas por el conector de claude.ai (`mcp__claude_ai_Figma__*`); la lista de `disenador-ui` incluye también los nombres del plugin (`mcp__plugin_figma_figma__*`).
- Claude Code carga `.claude/agents/` **al iniciar la sesión**: tras crear o cambiar un agente, hay que reiniciar la sesión para usarlo.
