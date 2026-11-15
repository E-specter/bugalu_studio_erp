---
id: operacion-entornos
titulo: Entornos
estado: borrador
depende_de: [D-08]
---

# Entornos

| Entorno | Base de datos | Ejecución |
|---|---|---|
| Desarrollo | Supabase **local** (CLI + Docker) | `supabase start` · `uv run fastapi dev` · `npm run dev` |
| Pruebas | Pendiente (D-08) | — |
| Producción | Pendiente (D-08) | Despliegue controlado tras aprobación |

No hay suscripción a Supabase: por ahora todo corre en local. Pruebas y producción dependen del hosting (D-08, ver [decisiones](../00-proyecto/decisiones/README.md)).

## Servicios del stack local de Supabase

Bugalú usa su propio stack (`project_id = "bugalu"`, puertos **553xx**) para convivir con otros proyectos de Supabase en la misma máquina, que ocupan los 543xx por defecto. Antes de usar el MCP, comprueba con `npx supabase status` que el stack activo es el de Bugalú.

| Servicio | URL |
|---|---|
| API | `http://127.0.0.1:55321` |
| MCP | `http://127.0.0.1:55321/mcp` |
| PostgreSQL | `postgresql://postgres:postgres@127.0.0.1:55322/postgres` |
| Studio | `http://127.0.0.1:55323` |
| Mailpit (correos de prueba) | `http://127.0.0.1:55324` |

Requisitos: Docker Desktop en marcha y el CLI de Supabase (`npx supabase` o instalación global). Montaje: [montaje-local](montaje-local.md) · Despliegue: [despliegue](despliegue.md).
