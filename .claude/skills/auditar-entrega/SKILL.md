---
name: auditar-entrega
description: Úsala cuando dev-audit deba revisar una ENTREGA de Bugalú (tarea, rango de commits o cierre de fase) y emitir el dictamen APROBADO o RECHAZADO.
---

# Auditar una entrega

Criterios e informe: [dev-audit](../../../docs/04-agentes/dev-audit.md). Solo lees y ejecutas: no editas archivos ni cambias el estado de git. Anota `git status --short` al empezar y compruébalo al terminar.

## Pasos

1. **Delimita:** tarea o plan, su Review Focus y el diff exacto (`git diff <base>..<head> -- <rutas>`). Con pocos turnos, trabaja en lote (diff + grep) y entrega antes de agotarlos.
2. **Ejecuta** las comprobaciones del área tocada, una vez, y copia la salida resumida:
   - backend: `uv run pytest -q` desde `backend/` **y** desde la raíz (`uv run --project backend pytest backend/tests -q`), `uv run ruff check .`, `uv run mypy src`;
   - base de datos: `npx supabase status` (stack `bugalu` en 456xx) y `npx supabase test db`;
   - frontend: `npm run check`, `npm run build` (sin `/catalogo`), `npm run test:e2e`, y que `dist/` no quede con artefactos de pruebas;
   - docs: `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`.
3. **Intenta romperlo** contra la app real (`crear_app()` con el cliente de pruebas), no solo leyendo:
   - **token real manipulado:** obtén un token real (alta con la fixture `crear_usuario` de `backend/tests/conftest.py`) y, **conservando su firma y su `kid` reales**, cambia solo la cabecera `alg` (RS256, PS256, ES384, HS256, `none`, EdDSA); aparte, `kid` falso, caducado, sin `sub`. Además, si puedes firmar con una clave de prueba propia, claims raros (`sub` que no es UUID, `aud` o `iss` ajenos);
   - **dependencias caídas:** servicio de claves (`URL_SUPABASE` a un puerto cerrado) y base de datos: 503 con el formato único, nunca 500 ni 401;
   - **RLS:** otro usuario, `anon`, rol sin permiso, columnas protegidas, fila ajena intacta;
   - **pruebas:** ¿pasan con el `.env` montado según la guía? ¿alguna se salta en silencio?
   - **frontend:** estados solo por color, foco tapado por lo fijo, zoom 200 %, sin JS, respuestas 401/503/red caída/no JSON;
   - **secretos:** solo la clave publicable en el frontend; el token nunca en URL ni logs.
   En Windows, los scripts asíncronos sueltos necesitan el bucle de `compartido/bucle.py`, y `uv run` necesita rutas Windows (no `/tmp` de Git Bash).
4. **Clasifica:**
   - **Bloqueante:** incumple un criterio; un 500 que un cliente puede provocar con una petición que él mismo puede construir; fuga de datos o escalada; prueba que falla según la guía de montaje; datos o usuarios en mal estado.
   - **No bloqueante:** lo demás, incluido un 500 que solo aparece con datos que solo el servidor puede emitir (nómbralo y pide la prueba).
   Cada hallazgo con `archivo:línea` y evidencia (comando y salida, o caso reproducible).
5. **Informe** con el formato de dev-audit, en este orden: dictamen, criterios incumplidos, observaciones no bloqueantes, verificado, y `No verificado:` con lo que no alcanzaste.

## Hallazgos reales de fases anteriores (búscalos siempre)

| Fase | Hallazgo |
|---|---|
| 1 | Decisiones cerradas que seguían como abiertas en otros docs |
| 2 | Estados solo por color; revisión que leyó 11 de 28 fichas (cubre todo o di qué no) |
| 3 | Token real con solo `alg` cambiado → 500 (con `kid` falso no aparecía) |
| 4 | Prueba dependiente del `.env` local; catálogo de desarrollo dentro de `dist/` |
| 3 | Servicio de claves caído → 401 (su excepción hereda de `PyJWTError`); base caída → 500 por `PoolTimeout` |
| 5 | `sub` no UUID con firma válida → 500 en `router.py` |
