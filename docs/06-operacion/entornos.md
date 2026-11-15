---
id: operacion-entornos
titulo: Entornos
estado: borrador
depende_de: [D-08]
---

# Entornos

| Entorno | Base de datos | Ejecución |
|---|---|---|
| Desarrollo | Supabase local (CLI) | `uv run fastapi dev` · `npm run dev` |
| Pruebas | Proyecto Supabase independiente | Despliegue automático desde la rama de integración |
| Producción | Proyecto Supabase de producción | Despliegue controlado tras aprobación |

Hosting de backend y frontend: pendiente (D-08, ver [decisiones](../00-proyecto/decisiones/README.md)).

Montaje: [montaje-local](montaje-local.md) · Despliegue: [despliegue](despliegue.md).
