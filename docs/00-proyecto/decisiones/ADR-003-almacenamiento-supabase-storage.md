---
id: ADR-003
titulo: Supabase Storage para audio y comprobantes
estado: aprobado
depende_de: [D-01]
---

# ADR-003: Supabase Storage para audio y comprobantes

## Contexto

El informe indicaba AWS S3 para custodiar multipistas, mezclas y másteres ([RF-09](../../03-requerimientos/RF-09.md), [RF-12](../../03-requerimientos/RF-12.md)). El proyecto corre sobre Supabase **local** (CLI + Docker), sin suscripción ni hosting (D-08). Además, la validación manual de pagos ([ADR-004](ADR-004-pagos-validacion-manual.md)) necesita guardar capturas de comprobantes.

## Opciones consideradas

1. AWS S3: otra cuenta, otras credenciales y otro servicio que montar en local.
2. **Supabase Storage: ya viene en el stack local y su API es compatible con S3.**

## Decisión

Opción 2 (usuario, 2026-11-15). Dos buckets **privados**:

| Bucket | Contenido |
|---|---|
| `entregables` | WAV de versiones y másteres ([RN-09](../../02-dominio/reglas-negocio.md)) |
| `comprobantes` | Capturas de pago ([RN-04](../../02-dominio/reglas-negocio.md)) |

## Consecuencias

- El acceso se controla con políticas RLS sobre `storage.objects`; nada es público.
- La descarga del máster usa una URL firmada con caducidad de 7 días ([RN-07](../../02-dominio/reglas-negocio.md)).
- El almacenamiento es un adaptador del módulo `entregables` ([backend-hexagonal](../../01-arquitectura/backend-hexagonal.md)): migrar a S3 cambia el adaptador, no el dominio.
- El actor "Almacenamiento Cloud" es Supabase Storage ([actores-roles](../../02-dominio/actores-roles.md)).
