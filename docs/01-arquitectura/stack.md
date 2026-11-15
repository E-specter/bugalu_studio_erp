---
id: arq-stack
titulo: Stack tecnológico
estado: borrador
depende_de: []
---

# Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL gestionado en Supabase |
| Backend | Python · `uv` (gestor de dependencias y entornos) · FastAPI |
| Frontend | Astro · componentes propios en HTML, CSS y JavaScript nativo (sin frameworks UI) |
| Almacenamiento de archivos | Pendiente: AWS S3 o Supabase Storage (D-01, ver [decisiones](../00-proyecto/decisiones/README.md)) |
| Diseño visual | Figma, conectado a Claude Code mediante el MCP oficial (ver [figma](../07-diseno/figma.md)) |
| Herramientas agénticas | MCP y skills de Claude Code (ver [herramientas-mcp](../06-operacion/herramientas-mcp.md)) |
| Documentación | Markdown en `docs/`, atómica por especificación |

Detalle por capa: [backend-hexagonal](backend-hexagonal.md) · [frontend-islas](frontend-islas.md) · [modelo-datos](modelo-datos.md).
