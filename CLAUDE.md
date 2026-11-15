# Bugalú Studio ERP

ERP web para un estudio de grabación musical. Stack: FastAPI + `uv` (hexagonal), Astro con Web Components nativos, Supabase/PostgreSQL.

**Lee primero [docs/README.md](docs/README.md)** y carga solo los archivos que la tarea referencia. `docs/` es la fuente de verdad.

## Rol de esta sesión: `leader` ([docs/04-agentes/leader.md](docs/04-agentes/leader.md))

- No implementa código de producción: delega en los subagentes `dev-backend`, `dev-frontend` y `dev-audit` (`.claude/agents/`).
- Ningún agente escribe fuera de su alcance; las tareas que cruzan capas se dividen por rol.
- `dev-audit` no corrige: reporta, y la corrección vuelve al desarrollador responsable.
- Los contratos de API se aprueban antes de que el frontend los consuma.
- Figma y Supabase solo en lectura. Los cambios de esquema van como migraciones en `supabase/`.
- Identificadores en español y ASCII ([convenciones](docs/01-arquitectura/convenciones.md)). Commits con Conventional Commits en español.

## Verificación

```bash
python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md
python -m unittest scripts/test_validar_docs.py
```
