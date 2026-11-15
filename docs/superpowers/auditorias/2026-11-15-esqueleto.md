# Auditoría del esqueleto · Fase 6

> `dev-audit` con Opus · 2026-11-15 · Dos auditorías en paralelo sobre `7ca1797` (A: backend, base de datos y seguridad; B: frontend, brief y accesibilidad) y re-auditoría de las correcciones `7ca1797..a7c9477`.

## Ronda 1

**6-A · APROBADO**, con un riesgo de arquitectura: PostgREST exponía `public`, así que los `grant` que el backend necesita habrían abierto la escritura directa por la API REST de Supabase, saltándose las reglas de negocio de Python (no explotable aún: solo existe `usuario`). Además: backend conectado como superusuario (podía deshacer `set local role`), 404/405 de FastAPI sin el formato único, `site_url` en :3000, y los 500 pendientes (`sub` no UUID, base caída, JWKS no JSON).

**6-B · RECHAZADO** por un bloqueante: al pulsar Reintentar en el perfil el foco caía en `<body>` y el resultado no se anunciaba (WCAG 2.4.3, 4.1.3). También: "Inicio" frente a "Panel" (3.2.4), acciones antes del `<h1>` en el DOM (1.3.2), enlaces táctiles de 18 px, y deriva de docs (`frontend-islas.md`, catálogo, `montaje-local.md`).

**Decisión de `leader`** (consecuencia de ADR-007, ampliado): PostgREST sin `public` y rol de conexión `bugalu_api` (`noinherit`, sin `bypassrls`), que solo asume `anon` y `authenticated`.

Correcciones: 3fefb03 (docs), 68e832e (TAREA-602, frontend), a7c9477 (TAREA-601, backend, ADR-007, convenciones de API).

## Ronda 2 — `7ca1797..a7c9477` · APROBADO

PostgREST no da acceso a `usuario` ni a la función con JWT real; `bugalu_api` no alcanza `postgres`, `service_role`, `authenticator` ni `supabase_admin`; ningún token manipulado, JWKS roto o lento, ni base caída devuelve 500; 404/405/422 con formato único; foco al título y anuncio único al reintentar. 50 pruebas de backend, 23 pgTAP, 55 de Playwright; docs coherentes con el código.

## No bloqueantes (a la primera tarea de RF-01)

- JWKS con JSON válido pero sin forma de JWKS → 401 en lugar de 503 (`autenticacion.py:45-49`); falta prueba.
- Sin `backend/.env`, `pytest` no recoge las pruebas (`main.py:38` crea la app al importar); afectaría a una CI.
- `Perfil.astro:84,90` enfoca dos veces el título al reintentar.
- OpenAPI declara el 422 con el esquema por defecto de FastAPI; `OperationalError` agrupa deadlocks como 503; CSS huérfano del catálogo en `dist/`; pruebas solo en Chromium; `/docs` y `/openapi.json` públicos (decidir en D-08).
