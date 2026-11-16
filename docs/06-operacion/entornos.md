---
id: operacion-entornos
titulo: Entornos
estado: borrador
depende_de: [D-08]
---

# Entornos

| Entorno | Base de datos | Ejecución |
|---|---|---|
| Desarrollo | Supabase **local** (CLI + Docker) | `npx supabase start` · `uv run python -m bugalu` (en `backend/`, ver [montaje-local](montaje-local.md)) · `npm run dev` |
| Pruebas | Pendiente | — |
| Producción | Supabase **autoalojado** (Docker Compose) en el servidor del estudio ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)) | Backend como servicio, frontend estático y proxy con HTTPS ([produccion](produccion.md)); despliegue controlado tras aprobación |

No hay suscripción a Supabase: el desarrollo usa el stack del CLI y la producción, Supabase autoalojado en el servidor del estudio. El entorno de pruebas no está decidido.

## Servicios del stack local de Supabase

Bugalú usa su propio stack (`project_id = "bugalu"`, puertos **456xx**) para convivir con otros proyectos de Supabase en la misma máquina, que ocupan los 543xx por defecto. Los puertos quedan por debajo del rango dinámico de Windows (49152-65535), donde el sistema reserva bloques que cambian tras cada reinicio. Antes de usar el MCP, comprueba con `npx supabase status` que el stack activo es el de Bugalú.

| Servicio | URL |
|---|---|
| API | `http://127.0.0.1:45621` |
| MCP | `http://127.0.0.1:45621/mcp` |
| PostgreSQL (backend) | `postgresql://bugalu_api:bugalu_api_dev@127.0.0.1:45622/postgres` (rol `bugalu_api`, [ADR-007](../00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md)) |
| PostgreSQL (administración, solo pruebas y CLI) | `postgresql://postgres:postgres@127.0.0.1:45622/postgres` |
| Studio | `http://127.0.0.1:45623` |
| Mailpit (correos de prueba) | `http://127.0.0.1:45624` |

Requisitos: Docker Desktop en marcha y el CLI de Supabase (`npx supabase` o instalación global). Montaje: [montaje-local](montaje-local.md) · Despliegue: [despliegue](despliegue.md).
