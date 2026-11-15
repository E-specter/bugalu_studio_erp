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

No hay pantallas para: calendario de salas (RF-03/04), pago de anticipo y liquidación (RF-05/11), asignación de personal (RF-07) ni reportes (RF-14). El flujo de contratación diseñado (con agenda de asesoría) difiere del flujo de [registrar-reserva](../02-dominio/flujos/registrar-reserva.md); se concilia en el trabajo de decisiones.

## Extracción

La ejecuta `disenador-ui` siguiendo [su procedimiento](../04-agentes/disenador-ui.md#fase-2--extracción). Saldo de llamadas: se anota en la lista de trabajo `fase-2-diseno` de claude-mem.
