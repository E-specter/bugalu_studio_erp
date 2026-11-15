---
id: operacion-montaje-local
titulo: Montaje del entorno local
estado: borrador
depende_de: [operacion-entornos]
---

# Montaje del entorno local

Pendiente (fases 3–4): se completa al crear los esqueletos de backend y frontend.

## Requisitos previstos

- Python con `uv`
- Node.js (Astro)
- Supabase CLI (Docker)
- Claude Code con los MCP de [herramientas-mcp](herramientas-mcp.md)

## Verificación de la documentación

```bash
python scripts/validar_docs.py docs
python -m unittest scripts/test_validar_docs.py
```
