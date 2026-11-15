# Changelog

## 2026-11-15

- **Diseño (fase 2):** brief técnico extraído de Figma y verificado (12 llamadas; figma.md congelado): fundamentos, 90+ tokens con contraste WCAG 2.2 AA, 28 fichas de componentes, patrones y logotipo en SVG. Skills `aplicar-brief` (precargada en disenador-ui y dev-frontend) y `disenar-pantalla`.
- **Contratación y D-01..D-04 (fase 1):** ADR-003..006 (Supabase Storage, pagos sin pasarela con validación manual, Supabase Auth, claves UUID). Flujo real del estudio: franjas semanales por sala, reserva de grabación o ensayo en múltiplos de 30 min, asesoría con profesional (presencial o virtual), cuotas 50/50 o plan a medida, posproducción 50/50. Reglas RN-12..RN-16, RF-02..05 y RF-11 reescritos, RF-15 nuevo. Spec: docs/superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md.
- **Equipo multiagente:** seis roles (`leader`, `disenador-ui`, `dev-backend`, `dev-frontend`, `dev-audit`, `documentador`) con modelo, effort, maxTurns, skills precargadas y herramientas por lista permitida. Configuración en `docs/04-agentes/equipo.md`.
- **Ciclo de bajo consumo:** un implementador más `dev-audit` por tarea; Opus solo en las compuertas.
- **Decisiones:** ADR-001 (Figma como fuente de extracción única) y ADR-002 (Code Connect descartado) cierran D-13 y D-14.
- **Supabase solo local:** `.mcp.json` apunta al MCP del stack local.
- **Validador:** comprueba que los agentes coincidan con `equipo.md`.

## 2026-11-14

- **Fase 0:** `PROYECTO.md` se segmenta en `docs/` (RF-01..RF-14, reglas, arquitectura, protocolos), con `CLAUDE.md`, los subagentes iniciales, `.mcp.json` y el validador de documentación.
