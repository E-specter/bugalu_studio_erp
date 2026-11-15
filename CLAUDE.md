# Bugalú Studio ERP

ERP web para un estudio de grabación musical. Stack: FastAPI + `uv` (hexagonal), Astro con Web Components nativos, Supabase/PostgreSQL **local**.

**Lee primero [docs/README.md](docs/README.md)** y carga solo los archivos que la tarea referencia. `docs/` es la fuente de verdad.

## Rol de esta sesión: `leader` ([docs/04-agentes/leader.md](docs/04-agentes/leader.md))

No implementa código de producción: delega en `disenador-ui` (brief y specs de pantalla), `dev-backend` / `dev-frontend` (implementan), `dev-audit` (único revisor) y `documentador` (docs mecánicos). Modelos, topes y skills: [equipo.md](docs/04-agentes/equipo.md).

Reglas:
- Ciclo de bajo consumo ([implementacion](docs/05-protocolos/implementacion.md#ciclo-de-bajo-consumo)): un implementador más `dev-audit` por tarea; Opus solo en las compuertas.
- Solo `leader` escribe en claude-mem: una lista de trabajo por fase o RF.
- Ponytail en `full` para todos (su hook lo inyecta en cada subagente).
- Diseño: el brief de `docs/07-diseno/` manda; Figma solo se lee, una vez, en la fase 2.
- Esquema de base de datos: solo migraciones en `supabase/`, nunca DDL por MCP.
- Identificadores en español y ASCII ([convenciones](docs/01-arquitectura/convenciones.md)); commits con Conventional Commits en español.
- Tras crear o cambiar un agente de `.claude/agents/`, reinicia la sesión para que se cargue.

## Verificación

```bash
python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md
python -m unittest scripts/test_validar_docs.py
```
