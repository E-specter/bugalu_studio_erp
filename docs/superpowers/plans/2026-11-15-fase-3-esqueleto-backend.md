# Fase 3 — Esqueleto backend y Supabase local · Plan

> **Ejecución:** ciclo de bajo consumo ([implementacion](../../05-protocolos/implementacion.md#ciclo-de-bajo-consumo)). `dev-backend` implementa TAREA-301 y TAREA-302 en orden; `dev-audit` con `model: "opus"` cierra la fase (toca `identidad` y una migración con RLS: [compuertas](../../04-agentes/equipo.md#compuertas-opus)).

**Goal:** Backend FastAPI hexagonal con `uv` sobre un Supabase local propio de Bugalú, con el corte `identidad` → `GET /api/v1/perfil` probado de punta a punta.

**Diseño aprobado por el usuario (2026-11-15):** stack propio `project_id = "bugalu"` en puertos 553xx; acceso a datos por [ADR-007](../../00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md); módulo de ejemplo `identidad`; migraciones base solo `usuario` + buckets; `pytest`, `ruff`, `mypy`.

## Global Constraints

- Identificadores en español ASCII ([convenciones](../../01-arquitectura/convenciones.md)); estructura de [backend-hexagonal](../../01-arquitectura/backend-hexagonal.md); `dominio/` sin FastAPI, psycopg ni Supabase.
- Ningún secreto versionado: `.env` ignorado, `backend/.env.example` con los nombres de variable. Las claves del stack local se leen de `npx supabase status`.
- Esquema solo por migraciones en `supabase/migrations/`; nunca DDL por MCP ni por SQL suelto.
- Puertos del stack: API 55321, DB 55322, shadow 55320, Studio 55323, Mailpit 55324, analytics 55327, pooler 55329 (ninguno en 543xx).
- TDD (`superpowers:test-driven-development`, precargada). Cada tarea entrega `uv run pytest`, `uv run ruff check .` y `uv run mypy src` en verde.

## Review Focus

1. **Escalada de rol:** un usuario no puede cambiarse su propio `rol` (ni por RLS ni por la API).
2. **RLS efectiva:** el usuario A no lee el perfil de B; el administrador sí lee todos.
3. **Token inválido o caducado** → 401, nunca 500; perfil inexistente → 404.
4. **Transacción con identidad:** `set local` dentro de la transacción, sin fugas de identidad entre conexiones del pool.
5. **Stack equivocado:** nada apunta a 543xx (el stack `valmont` sigue corriendo en la máquina).

---

### TAREA-301: Supabase local de Bugalú y migraciones base (`dev-backend`)

**Files:** `supabase/config.toml`, `supabase/migrations/<ts>_identidad_usuario.sql`, `supabase/migrations/<ts>_storage_buckets.sql`, `supabase/tests/` (pgTAP) o pruebas de integración en TAREA-302, `.gitignore`.

- [ ] `npx supabase init`; `project_id = "bugalu"` y los puertos de Global Constraints.
- [ ] Migración `usuario`: `id uuid` PK → `auth.users(id)` on delete cascade; `nombre text`; `rol text not null default 'cliente' check (rol in ('cliente','personal','administrador'))`; `especialidad text`; `creado_en timestamptz not null default now()`. RLS activada: leer el propio perfil; el administrador lee todos (función `es_administrador()` `security definer` con `search_path` fijo); actualizar el propio perfil **sin** cambiar `rol` (trigger o privilegios de columna). Trigger en `auth.users` que crea el perfil con rol `cliente`.
- [ ] Migración de buckets privados `entregables` y `comprobantes` (`public = false`, sin políticas todavía: solo el rol de servicio accede).
- [ ] `npx supabase start` y `npx supabase db reset` sin errores; pruebas que demuestren los puntos 1 y 2 de Review Focus.
- [ ] Actualizar [modelo-datos](../../01-arquitectura/modelo-datos.md) (columnas reales de `usuario`). Commit lo hace `leader`.

### TAREA-302: Esqueleto FastAPI y corte `identidad` (`dev-backend`)

**Files:** `backend/` según [backend-hexagonal](../../01-arquitectura/backend-hexagonal.md#estructura); `docs/06-operacion/montaje-local.md` (sección backend).

- [ ] `uv init` en `backend/` (paquete `bugalu` en `src/`); dependencias: `fastapi`, `uvicorn`, `psycopg[binary,pool]`, `pydantic-settings`, `pyjwt[crypto]`; desarrollo: `pytest`, `httpx`, `ruff`, `mypy`.
- [ ] `compartido/`: `configuracion.py` (variables de entorno), `errores.py`, `base_datos.py` (pool + `transaccion_con_identidad(claims)` según ADR-007), `autenticacion.py` (dependencia FastAPI que valida el JWT del stack local: JWKS o secreto, según lo que exponga el CLI 3.x; consúltalo con Context7 y `npx supabase status`).
- [ ] `modulos/identidad/`: `dominio/usuario.py` (`Usuario`, `Rol`), `dominio/puertos.py` (`RepositorioUsuarios`), `aplicacion/obtener_perfil/caso_de_uso.py`, `infraestructura/salida/repositorio_postgres.py`, `infraestructura/entrada/http/{router,esquemas}.py`. `GET /api/v1/perfil` → 200 / 401 / 404 (Review Focus 3).
- [ ] Pruebas: unitarias (dominio y caso de uso con repositorio falso), integración (repositorio contra el stack local, puntos 2 y 4), API (cliente de pruebas con un usuario real creado en el stack).
- [ ] `montaje-local.md`: requisitos, `npx supabase start`, `.env` desde `.env.example`, `uv run fastapi dev`, comandos de calidad.

### Cierre (`leader`)

- [ ] Commits por tarea; `documentador`: changelog y hoja de ruta (fase 3 → Hecho).
- [ ] Compuerta: `dev-audit` Opus sobre el rango de la fase, con este Review Focus; informe en `docs/superpowers/auditorias/`.
- [ ] Con el stack de Bugalú arriba, listar las herramientas `mcp__supabase__*` y restringir a lectura (pendiente de la fase 0b).
