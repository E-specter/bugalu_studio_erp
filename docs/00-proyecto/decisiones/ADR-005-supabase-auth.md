---
id: ADR-005
titulo: Supabase Auth para la autenticación
estado: aprobado
depende_de: [D-03]
---

# ADR-005: Supabase Auth para la autenticación

## Contexto

El informe asume una tabla `usuario` con `passwordHash` y autenticación propia. El stack ya incluye Supabase, que trae autenticación, y las políticas RLS de la base de datos se apoyan en la identidad de Supabase ([RF-01](../../03-requerimientos/RF-01.md)).

## Opciones consideradas

1. Autenticación propia en FastAPI: hash de contraseñas, sesiones y recuperación de cuenta escritos y mantenidos por el proyecto.
2. **Supabase Auth: registro, inicio de sesión, recuperación y JWT ya resueltos, e integrados con RLS.**

## Decisión

Opción 2 (usuario, 2026-11-15).

- Las credenciales viven en `auth.users`; el proyecto no guarda `password_hash`.
- El perfil vive en `usuario`, con `id` igual a `auth.users.id`, más `rol` y `especialidad`.
- Roles de sistema: `cliente`, `personal` y `administrador`. El Profesional artístico es `personal` con especialidad `asesoria` ([actores-roles](../../02-dominio/actores-roles.md)).

## Consecuencias

- FastAPI valida el JWT de Supabase en cada petición y lee el rol del perfil.
- El rol se aplica en dos capas: RLS en la base de datos y autorización en los casos de uso.
- Los correos de alta y recuperación salen por el servicio de Supabase; en local se ven en Mailpit ([entornos](../../06-operacion/entornos.md)).
- Las claves son UUID ([ADR-006](ADR-006-claves-uuid.md)).
