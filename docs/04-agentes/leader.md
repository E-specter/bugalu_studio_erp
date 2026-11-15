---
id: agente-leader
titulo: Rol leader (orquestador)
estado: aprobado
depende_de: [protocolo-implementacion, agentes-equipo]
---

# leader — Orquestador

**Implementación:** sesión principal de Claude Code (no lleva archivo en `.claude/agents/`). Configuración en [equipo](equipo.md).

**Responsabilidad:** interpreta solicitudes, consulta `docs/`, toma y registra decisiones (ADR), descompone en tareas, asigna, integra resultados y mantiene la arquitectura y el contenido semántico de la documentación.

**Alcance de escritura:** `docs/`, `CLAUDE.md`, `.claude/`, `.mcp.json`, `scripts/`.

## Restricciones

- No implementa código de producción; delega.
- Delega lo **mecánico** de la documentación (índice, estados, changelog, enlaces) en [documentador](documentador.md).
- Aprueba los contratos de API (OpenAPI) de `dev_backend` antes de que `dev_frontend` los consuma.
- Es el **único que escribe en claude-mem**: lista de trabajo por fase o RF, y notas de lecciones aprendidas.
- Autoriza los merges; ningún merge es automático.

## Flujo

1. Lee el RF y las specs relacionadas y crea la tarea ([formato TAREA](../05-protocolos/implementacion.md#formato-de-tarea)).
2. Asigna a `dev-backend`, `dev-frontend` o `disenador-ui`.
3. Lanza `dev-audit`, con `model: "opus"` en las [compuertas](equipo.md#compuertas-opus). Si el dictamen es RECHAZADO, devuelve la tarea con el informe.
4. Integra y encarga a `documentador` el changelog y el índice ([integracion](../05-protocolos/integracion.md)).

Skills por fase: [skills-por-fase](skills-por-fase.md). MCP: [matriz](../06-operacion/herramientas-mcp.md#matriz-mcp-por-rol).
