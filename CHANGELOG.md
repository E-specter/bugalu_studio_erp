# Changelog

## 2026-11-15

- **Equipo multiagente:** seis roles (`leader`, `disenador-ui`, `dev-backend`, `dev-frontend`, `dev-audit`, `documentador`) con modelo, effort, maxTurns, skills precargadas y herramientas por lista permitida. Configuración en `docs/04-agentes/equipo.md`.
- **Ciclo de bajo consumo:** un implementador más `dev-audit` por tarea; Opus solo en las compuertas.
- **Decisiones:** ADR-001 (Figma como fuente de extracción única) y ADR-002 (Code Connect descartado) cierran D-13 y D-14.
- **Supabase solo local:** `.mcp.json` apunta al MCP del stack local.
- **Validador:** comprueba que los agentes coincidan con `equipo.md`.

## 2026-11-14

- **Fase 0:** `PROYECTO.md` se segmenta en `docs/` (RF-01..RF-14, reglas, arquitectura, protocolos), con `CLAUDE.md`, los subagentes iniciales, `.mcp.json` y el validador de documentación.
