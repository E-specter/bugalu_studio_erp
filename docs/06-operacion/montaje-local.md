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
- Node.js 22.23 o superior (Astro 7) y `npm` para el frontend.
- Claude Code con los MCP de [herramientas-mcp](herramientas-mcp.md).

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
| `ORIGENES_PERMITIDOS` | Orígenes del frontend, separados por comas (`http://localhost:4321`). Vacío = sin CORS: el navegador bloquea las llamadas del frontend |

Comprueba que responde con `curl -i http://127.0.0.1:8000/api/v1/perfil`: sin token devuelve 401.

**Arranque con `python -m bugalu`, no con `fastapi dev`:** en Windows, uvicorn usa por defecto un bucle de eventos (`ProactorEventLoop`) con el que `psycopg` asíncrono no funciona. `bugalu/__main__.py` arranca uvicorn con un bucle compatible (`compartido/bucle.py`) y recarga automática.

## Frontend

Astro estático con `npm`, desde `frontend/`:

```bash
cd frontend
npm install
cp .env.example .env        # y completa la clave publicable (abajo)
npm run dev                 # http://localhost:4321
```

Variables de `frontend/.env` (ignorado por git; solo `PUBLIC_*`, llegan al navegador):

| Variable | Origen |
|---|---|
| `PUBLIC_URL_API` | Backend de desarrollo, `http://127.0.0.1:8000` |
| `PUBLIC_URL_SUPABASE` | `API_URL` de `npx supabase status` (puerto 45621): la sesión se lee de ahí |
| `PUBLIC_CLAVE_PUBLICABLE_SUPABASE` | `PUBLISHABLE_KEY` de `npx supabase status`. Nunca pongas la clave secreta ni la de servicio |

Para que el navegador pueda llamar al backend, añade `ORIGENES_PERMITIDOS=http://localhost:4321` a `backend/.env` y reinicia la API. Sin sesión, `http://localhost:4321/app/perfil` muestra el estado "Tu sesión no es válida" (la pantalla de acceso llega con RF-01).

Calidad y pruebas:

```bash
npm run check               # tokens, literales visuales y astro check
npm run build               # salida estática en dist/
npm run test:e2e            # Playwright + axe; construye el sitio y simula la API con page.route
```

`test:e2e` no necesita backend ni Supabase (usa valores ficticios) y deja capturas en `frontend/pruebas/capturas/`. La primera vez, instala el navegador con `npx playwright install chromium`. `/catalogo` existe en `npm run dev` y en el build de pruebas (`PUBLIC_CATALOGO=1`, en `dist-pruebas/`, lo activa `test:e2e`); nunca en `npm run build`.

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
