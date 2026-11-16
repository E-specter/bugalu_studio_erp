---
id: operacion-despliegue
titulo: Despliegue
estado: borrador
depende_de: [operacion-entornos, ADR-014]
---

# Despliegue

Producción en el servidor del estudio ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)): montaje en [produccion](produccion.md) y pasos de cada actualización en [produccion-mantenimiento](produccion-mantenimiento.md#actualizaciones).

Principios ya fijados ([entornos](entornos.md)):
- Pruebas: despliegue automático desde la rama de integración.
- Producción: despliegue controlado tras aprobación de `leader`.
