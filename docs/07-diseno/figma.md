---
id: diseno-figma
titulo: Figma — registro de origen de la extracción
estado: borrador
depende_de: [ADR-001]
---

# Figma — registro de origen

Figma es la **fuente de extracción única** del diseño ([ADR-001](../00-proyecto/decisiones/ADR-001-figma-fuente-extraccion.md)). Este archivo registra de dónde salió el brief; queda en `implementado` y congelado al terminar la extracción (fase 2). Después, el diseño se extiende desde el [brief](brief.md), no desde Figma.

## Archivo

| Campo | Valor |
|---|---|
| Nombre | `bugalu_studio_erp` |
| File key | `GxpFTDX6L0uFwg6xlulhXF` |
| Equipo requerido | «Integrador I» (plan Pro, asiento Full) |
| Volcado local de estructura | `.claude/cache/figma-metadata-2026-11-15.xml` (ignorado por git; tomado antes del reordenamiento de páginas) |

## Mapa de páginas (2026-11-15)

| Página | Contenido observado |
|---|---|
| `references` | Referencias visuales |
| `brief` | Guía de estilo brutalista (`bugalu-brutalist-design-guide`) y material de marca |
| `landing-page` | `bugalu-studio-landing` |
| `blueprint-funcional` | Blueprint funcional del portal |
| `login` | Acceso y registro, interno y de artista |
| `erp` | Portal del artista (escritorio y móvil: dashboard, proyecto, versión, revisión, historial, versión aprobada); flujo de contratación (servicio → brief → agenda de asesoría → cotización → revisión → proyecto activado); panel interno (dashboard operativo, clientes, tablero de proyectos, detalle interno, carga de WAV, publicar versión, centro de revisiones) |

Estado del archivo: hay unas 32 pantallas, pero no hay biblioteca de componentes (3 símbolos, casi todos del logo) ni variables confirmadas.

## Brecha detectada

Conciliación (fase 1, [spec 2026-11-15](../superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md)): el flujo de contratación diseñado (servicio → brief → agenda de asesoría → cotización → revisión → proyecto activado) es la **rama de asesoría** del flujo real y se conserva ([agendar-asesoria](../02-dominio/flujos/agendar-asesoria.md)).

No hay pantallas para estas partes, que se especifican desde el brief en la fase 2:

| Pantalla faltante | Requerimiento |
|---|---|
| Franjas de sala, tramo y simulación de precio | [RF-02](../03-requerimientos/RF-02.md), [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md) |
| Publicación de franjas (Administrador) | [RF-03](../03-requerimientos/RF-03.md) |
| Reserva de ensayo | [RF-04](../03-requerimientos/RF-04.md) |
| Horarios del profesional y modalidad de asesoría | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura y validación de pagos | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| Asignación de personal | [RF-07](../03-requerimientos/RF-07.md) |
| Reportes | [RF-14](../03-requerimientos/RF-14.md) |

## Extracción

La ejecuta `disenador-ui` siguiendo [su procedimiento](../04-agentes/disenador-ui.md#fase-2--extracción). Saldo de llamadas: se anota en la lista de trabajo `fase-2-diseno` de claude-mem.
