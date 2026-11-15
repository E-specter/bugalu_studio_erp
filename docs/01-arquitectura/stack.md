---
id: arq-stack
titulo: Stack tecnológico
estado: borrador
depende_de: []
---

# Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL en Supabase (local con CLI + Docker; hosting pendiente, D-08) |
| Backend | Python · `uv` (gestor de dependencias y entornos) · FastAPI |
| Acceso a datos | `psycopg` 3 asíncrono, transacción con la identidad del usuario y RLS ([ADR-007](../00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md)) |
| Frontend | Astro · componentes propios en HTML, CSS y JavaScript nativo (sin frameworks UI) |
| Almacenamiento de archivos | Supabase Storage, buckets privados ([ADR-003](../00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md)) |
| Autenticación | Supabase Auth; claves UUID ([ADR-005](../00-proyecto/decisiones/ADR-005-supabase-auth.md), [ADR-006](../00-proyecto/decisiones/ADR-006-claves-uuid.md)) |
| Pagos | Sin pasarela en v1: captura del comprobante y validación manual ([ADR-004](../00-proyecto/decisiones/ADR-004-pagos-validacion-manual.md)) |
| Diseño visual | Brief técnico en `docs/07-diseno/` (ver [brief](../07-diseno/brief.md)), extraído una sola vez de Figma ([origen](../07-diseno/figma.md)) |
| Herramientas agénticas | MCP y skills de Claude Code (ver [herramientas-mcp](../06-operacion/herramientas-mcp.md)) |
| Documentación | Markdown en `docs/`, atómica por especificación |

Detalle por capa: [backend-hexagonal](backend-hexagonal.md) · [frontend-islas](frontend-islas.md) · [modelo-datos](modelo-datos.md).
