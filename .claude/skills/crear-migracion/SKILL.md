---
name: crear-migracion
description: Úsala cuando dev-backend deba crear o cambiar tablas, columnas, políticas RLS, funciones, triggers o buckets en la base de datos de Bugalú (Supabase local, carpeta supabase/).
---

# Crear una migración

El esquema solo cambia con migraciones versionadas en `supabase/migrations/`. Nunca DDL por MCP ni SQL suelto (`apply_migration` y `execute_sql` están denegadas).

**Ejemplo canónico:** [identidad_usuario.sql](../../../supabase/migrations/20261115100000_identidad_usuario.sql) (RLS, privilegios de columna, `security definer` con `search_path` vacío, trigger) y su prueba [usuario.test.sql](../../../supabase/tests/usuario.test.sql).

## Pasos

1. **Lee** el ejemplo canónico entero, [modelo-datos](../../../docs/01-arquitectura/modelo-datos.md), [convenciones](../../../docs/01-arquitectura/convenciones.md) (tablas y columnas `snake_case` singular en español ASCII; claves foráneas `id_<tabla>`; fechas `timestamptz`), las reglas RN y el contrato del RF, y [ADR-006](../../../docs/00-proyecto/decisiones/ADR-006-claves-uuid.md) (`id uuid default gen_random_uuid()`).
   - Si una tabla referenciada no existe todavía, **detente y avisa a `leader`**: no la crees de paso.
   - Si `modelo-datos.md` no nombra una columna que necesitas (p. ej. quién publicó), propónla en la ENTREGA y añádela al modelo en la misma tarea.
2. **Antes de tocar nada:** `npx supabase status` muestra el stack `bugalu` en **456xx**. Si ves 543xx, es otro proyecto: no sigas.
3. **Prueba primero** (pgTAP en `supabase/tests/`), y mírala fallar con `npx supabase test db`. Cubre siempre:
   - quién lee: el dueño sí, otro usuario no, el rol que corresponda sí, `anon` no (o sí, si el RF lo pide);
   - quién escribe: insert/update/delete permitidos y prohibidos (código `42501`), y que la fila ajena queda **intacta** (no basta con "no dio error");
   - columnas protegidas (`rol`, dueños, estados que solo cambia el sistema) no editables por el usuario;
   - restricciones de negocio en la base cuando son invariantes (`check`, `unique`, exclusión de solapes).
4. **Escribe la migración** `npx supabase migration new <tema>`:
   - `alter table … enable row level security` en toda tabla nueva;
   - `revoke all … from anon, authenticated` y luego `grant` mínimo (por columna si el usuario solo edita algunas);
   - políticas con `auth.uid()`; funciones `security definer` con `set search_path = ''`, `revoke execute` de `public, anon` y nombres totalmente calificados;
   - **lectura pública, escritura de administrador** (catálogos, franjas): `grant select … to anon, authenticated` + política `for select using (true)`; `grant insert, delete … to authenticated` + `for insert … with check (public.es_administrador())` y `for delete … using (public.es_administrador())` (`with check` no existe en `for delete`);
   - extensiones (p. ej. `btree_gist` para `exclude using gist` contra solapes): `create extension if not exists <ext> with schema extensions;` en la misma migración;
   - buckets privados y políticas de `storage.objects` por dueño cuando el RF suba archivos ([ADR-003](../../../docs/00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md)).
   Una migración ya aplicada en otro entorno no se edita: se añade otra.
5. **Verifica:** `npx supabase db reset` sin errores y `npx supabase test db` en verde.
6. **Docs en la misma tarea:** actualiza la tabla en `modelo-datos.md` (columnas reales y resumen de RLS) y corre `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`.

## Errores que ya ocurrieron

| Error | Cómo evitarlo |
|---|---|
| Usuario podía editar su `especialidad` y autoasignarse permisos | Paso 3: probar cada columna editable; `grant update (…)` mínimo |
| Prueba de "A no cambia B" que solo miraba que no hubiera error | Comprobar que la fila de B no cambió |
| Puertos 543xx del stack de otro proyecto | Paso 2 |
