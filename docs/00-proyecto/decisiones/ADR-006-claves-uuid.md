---
id: ADR-006
titulo: UUID como clave primaria
estado: aprobado
depende_de: [D-04]
---

# ADR-006: UUID como clave primaria

## Contexto

El informe usa claves enteras. Supabase Auth identifica a los usuarios con UUID ([ADR-005](ADR-005-supabase-auth.md)), y `usuario.id` tiene que coincidir con `auth.users.id`.

## Opciones consideradas

1. Enteros autoincrementales: legibles, pero mezclados con el UUID de `auth.users` y fáciles de enumerar desde la API.
2. **UUID en todas las tablas.**

## Decisión

Opción 2 (usuario, 2026-11-15). Todas las tablas usan `id uuid` como clave primaria, generado por la base de datos (`gen_random_uuid()`).

## Consecuencias

- Las referencias entre tablas son `uuid`, incluida `usuario.id` → `auth.users.id`.
- Los identificadores legibles para personas siguen como columnas aparte y únicas: `folio` de reserva y `codigo` de proyecto (`PRJnn`) ([modelo-datos](../../01-arquitectura/modelo-datos.md)).
- Los identificadores de la API no revelan cuántos registros hay.
