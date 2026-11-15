---
name: crear-slice-backend
description: Úsala cuando dev-backend deba implementar un caso de uso nuevo de Bugalú en FastAPI (endpoint + lógica + acceso a datos) dentro de un módulo hexagonal de backend/src/bugalu/modulos/.
---

# Crear un corte (slice) de backend

TDD con la skill precargada. Estructura y reglas: [backend-hexagonal](../../../docs/01-arquitectura/backend-hexagonal.md), acceso a datos: [ADR-007](../../../docs/00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md).

**Ejemplo canónico:** el módulo `identidad` (`GET /api/v1/perfil`):
- dominio: [usuario.py](../../../backend/src/bugalu/modulos/identidad/dominio/usuario.py), [puertos.py](../../../backend/src/bugalu/modulos/identidad/dominio/puertos.py)
- aplicación: [caso_de_uso.py](../../../backend/src/bugalu/modulos/identidad/aplicacion/obtener_perfil/caso_de_uso.py)
- infraestructura: [repositorio_postgres.py](../../../backend/src/bugalu/modulos/identidad/infraestructura/salida/repositorio_postgres.py), [router.py](../../../backend/src/bugalu/modulos/identidad/infraestructura/entrada/http/router.py)
- pruebas espejo en `backend/tests/modulos/identidad/`.

El pool se conecta como `bugalu_api`, que solo puede asumir `anon` o `authenticated`; PostgREST no expone `public` ([ADR-007](../../../docs/00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md)), así que el backend es el único camino a los datos.

## Pasos

0. **Lee el ejemplo canónico entero** antes de planificar.
1. **Lee** el RF (criterios y sección `## Contrato API`), sus reglas RN y el flujo. Si una regla está abierta (D-xx) o falta el contrato, no la inventes: avisa a `leader`.
2. **Contrato:** implementa el de la sección `## Contrato API` del RF (rutas `kebab-case` plural bajo `/api/v1`). Si necesitas cambiarlo, propónlo en la ENTREGA. Módulo nuevo: crea la estructura de backend-hexagonal y registra su router en `main.py`.
3. **Dominio** (`dominio/`): entidades inmutables, reglas RN como funciones puras, puertos como `Protocol`. Solo biblioteca estándar: nada de fastapi, psycopg, pydantic ni supabase (compruébalo con grep).
4. **Aplicación** (`aplicacion/<caso>/caso_de_uso.py`): orquesta el dominio a través de puertos; errores de dominio de `compartido/errores.py`, sin HTTP.
5. **Infraestructura:**
   - salida: el repositorio recibe la conexión de `transaccion_con_identidad(pool, claims)`; nunca abre conexiones propias; SQL parametrizado;
   - entrada: el router abre la transacción **dentro** del endpoint (no en una dependencia con `yield`), traduce errores con el formato único y declara todos los códigos en OpenAPI.
   - **Endpoint público** (visitante sin sesión): transacción con `set local role anon`, nunca la conexión del pool sin asumir rol (`bugalu_api` no lee nada sin él). Si `compartido/base_datos.py` aún no la ofrece, añádela junto a `transaccion_con_identidad`, con su prueba, y dilo en la ENTREGA. Lo mismo para una dependencia de claims opcionales en `autenticacion.py`: solo con pruebas de cabeceras manipuladas.
   - Errores nuevos (403 `sin_permiso`, 409 `conflicto`…): una clase en `compartido/errores.py` y su traducción en `manejadores_http.py`; códigos `snake_case` en español.
   - Convierte y valida los claims antes de usarlos (p. ej. `sub` a UUID → si falla, 401, nunca 500).
   - Si varias filas deben guardarse juntas, una sola transacción.
6. **Pruebas** (mira cada una fallar antes):
   - unitarias de dominio y caso de uso con repositorio falso;
   - integración contra el stack de Bugalú (456xx) con RLS: el usuario A no ve ni cambia datos de B; el rol correcto sí;
   - API: éxito; en endpoints protegidos, 401 (sin token, token real con `alg` cambiado, caducado); 403 si hay rol; 404/409/422 según el contrato; 503 si cae Auth o la base. Para un administrador, crea el usuario con la fixture `crear_usuario` y súbele el rol por SQL con la conexión de `URL_BASE_DATOS_ADMIN` (solo pruebas) en la propia prueba;
   - ninguna prueba depende del `.env` local: fija las variables con `monkeypatch.setenv` (las de entorno ganan al `.env`).
7. **Verifica** en `backend/`: `uv run pytest -q` (0 saltadas con el stack arriba), `uv run ruff check .`, `uv run mypy src`. Actualiza el RF y `modelo-datos.md` si cambian.

## Errores que ya ocurrieron

| Error | Cómo evitarlo |
|---|---|
| Token con `alg` cambiado → 500 | No toques `compartido/autenticacion.py`; si lo haces, prueba cabeceras manipuladas |
| Prueba que pasa solo sin `.env` | `setenv`, nunca solo `delenv` |
| Identidad filtrada entre conexiones del pool | Usa siempre `transaccion_con_identidad`; prueba dos usuarios seguidos |
