---
id: operacion-montaje-local
titulo: Montaje del entorno local
estado: borrador
depende_de: [operacion-entornos]
---

# Montaje del entorno local

## Requisitos

- Docker Desktop en marcha y Node.js (para `npx supabase`).
- Python 3.14 y [`uv`](https://docs.astral.sh/uv/) (`requires-python >= 3.14`).
- Astro y Claude Code con los MCP de [herramientas-mcp](herramientas-mcp.md): se detallan al crear el frontend (fase 4).

## Backend

Desde la raíz del repositorio:

```bash
npx supabase start          # stack propio de Bugalú (project_id "bugalu", puertos 456xx)
npx supabase db reset       # aplica las migraciones de supabase/migrations
npx supabase status         # URLs y claves del stack local
cd backend
cp .env.example .env        # y completa los valores con `npx supabase status`
uv sync
uv run python -m bugalu     # API en http://127.0.0.1:8000 (docs en /docs)
```

Variables de `backend/.env` (`.env` está ignorado por git):

| Variable | Origen |
|---|---|
| `URL_BASE_DATOS` | `DB_URL` de `npx supabase status` (puerto 45622) |
| `URL_SUPABASE` | `API_URL` (puerto 45621); de ahí sale el JWKS con el que se verifican los JWT |
| `CLAVE_PUBLICABLE_SUPABASE` | `PUBLISHABLE_KEY`; solo la usan las pruebas de integración |

Comprueba que responde con `curl -i http://127.0.0.1:8000/api/v1/perfil`: sin token devuelve 401.

**Arranque con `python -m bugalu`, no con `fastapi dev`:** en Windows, uvicorn usa por defecto un bucle de eventos (`ProactorEventLoop`) con el que `psycopg` asíncrono no funciona. `bugalu/__main__.py` arranca uvicorn con un bucle compatible (`compartido/bucle.py`) y recarga automática.

## Calidad (desde `backend/`)

```bash
uv run pytest               # unitarias + integración contra el stack local
uv run pytest -m "not integracion"   # solo unitarias (no necesitan Supabase)
uv run ruff check .
uv run mypy src
```

Las pruebas de integración se saltan, con un mensaje, si el stack local no responde. Pruebas de la base de datos (pgTAP), desde la raíz: `npx supabase test db`.

## Verificación de la documentación

```bash
python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md
python -m unittest scripts/test_validar_docs.py
```
