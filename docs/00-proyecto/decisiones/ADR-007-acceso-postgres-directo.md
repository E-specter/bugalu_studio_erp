---
id: ADR-007
titulo: Acceso del backend a PostgreSQL directo, con RLS por transacción
estado: aprobado
depende_de: [ADR-005, ADR-006]
---

# ADR-007: Acceso del backend a PostgreSQL directo, con RLS por transacción

## Contexto

Los casos de uso necesitan escribir varias filas de forma atómica (una reserva y sus cuotas, [RN-13](../../02-dominio/reglas-negocio.md)) y mantener las reglas de negocio en el dominio de Python ([backend-hexagonal](../../01-arquitectura/backend-hexagonal.md)). Las políticas RLS de Supabase son la segunda capa de autorización ([ADR-005](ADR-005-supabase-auth.md)).

## Opciones consideradas

1. Cliente `supabase-py` (PostgREST por HTTP): menos código inicial, pero sin transacciones de varias sentencias; las operaciones atómicas obligan a funciones SQL y las reglas acaban en la base de datos.
2. **Conexión directa con `psycopg` 3 (asíncrono, con pool), una transacción por caso de uso que asume la identidad del usuario.**

## Decisión

Opción 2 (usuario, 2026-11-15). Cada transacción de un usuario autenticado ejecuta, antes de sus consultas:

```sql
set local role authenticated;
select set_config('request.jwt.claims', '<claims del JWT>', true);
```

Así `auth.uid()` y las políticas RLS se aplican igual que en PostgREST.

## Consecuencias

- El kernel `compartido/` ofrece la transacción con identidad; los repositorios de `infraestructura/salida/` la reciben y no abren conexiones propias.
- Las operaciones de sistema (triggers, tareas internas) usan el rol de servicio solo en adaptadores explícitos y documentados.
- Storage y Auth (subida de capturas, URL firmadas) usan su API HTTP desde adaptadores propios cuando su RF lo necesite.
- Las pruebas de integración corren contra el Supabase local de Bugalú ([entornos](../../06-operacion/entornos.md)).

### Ampliación (fase 6, 2026-11-15)

La auditoría del esqueleto mostró dos consecuencias que este ADR no recogía:

- **PostgREST no expone `public`.** Los `grant` que el backend necesita para `authenticated` también abrirían la API REST de Supabase, y un cliente podría escribir sin pasar por las reglas de negocio de Python. Como el backend es el único camino a los datos, `supabase/config.toml` saca `public` de los esquemas de la API. Supabase Auth y Storage no se ven afectados.
- **Rol de conexión propio.** El backend se conecta con `bugalu_api` (`noinherit`, sin superusuario ni `bypassrls`), que solo puede asumir `anon` y `authenticated`. Un superusuario podría deshacer `set local role` con `reset role`, y una inyección SQL saltaría la RLS. Las pruebas que necesitan privilegios usan una URL de administración aparte.
