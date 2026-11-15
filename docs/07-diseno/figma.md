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
| Horarios del profesional (la modalidad sí está en `141:29060`) | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura y validación de pagos | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| Asignación de personal | [RF-07](../03-requerimientos/RF-07.md) |
| Reportes | [RF-14](../03-requerimientos/RF-14.md) |
| Perfil de usuario (solo hay acceso y registro) | [RF-01](../03-requerimientos/RF-01.md) |
| Estado de reserva y su historial; las notificaciones son correo | [RF-06](../03-requerimientos/RF-06.md) |
| Evaluación de satisfacción (la versión aprobada solo trae los pasos de cierre) | [RF-13](../03-requerimientos/RF-13.md) |

Brechas transversales (sin RF propio): estados vacío, carga y error; diálogo de confirmación; notificación emergente. Se cubren con el patrón [estados del sistema](patrones/estados-sistema.md) y la sección "Fuera del catálogo" del [catálogo](componentes/README.md).

## Extracción

Ejecutada por `disenador-ui` ([procedimiento](../04-agentes/disenador-ui.md#fase-2--extracción)) el **2026-11-15** (TAREA-201).

| Campo | Valor |
|---|---|
| Llamadas al MCP de Figma | **0** de 60: las herramientas de Figma no se cargaron en la sesión del subagente (no fue posible ni `whoami`) |
| Fuente usada | Volcado local `.claude/cache/figma-metadata-2026-11-15.xml`: estructura, medidas y nombres de capa. Los textos de la guía y de la ficha de marca están en los nombres de capa, así que paleta, tipografía, specs de botón y etiqueta y el catálogo de efectos salen literales |
| Resultado | [brief](brief.md), `fundamentos/`, [tokens](tokens.md), [componentes](componentes/README.md), [patrones](patrones/README.md) |

Nodos fuente principales: guía `86:20` (principios `86:55`, paleta `86:70`, tipografía `86:100`, componentes `86:152`, imagen `86:198`, efectos `88:57`); ficha de marca `35:29` y `14:2`; logos `58:2`, `40:150`, `58:77`.

### Pendiente de verificación en Figma

Valores marcados `inferido` en [tokens](tokens.md) que el volcado no contiene. Una pasada de ≈ 12 llamadas (`get_variable_defs` + `get_design_context` sobre `86:152`, `161:609`, `141:28788`, `112:286` y `145:3617`, y `download_assets` de `58:2`, `40:150`, `58:77`) los confirma:

1. Superficie de paneles (`#FFFFFF` inferido) y texto secundario (`#4A4B7D`).
2. Desplazamiento de la sombra plana (2 / 4 px) y si los botones llevan sombra.
3. Fuente técnica (Geist Mono inferido) y peso de Unbounded "Heavy" (900).
4. Relleno del botón secundario `86:168` (navy inferido) y radio de botones y campos (0 inferido).
5. Tamaño real de los textos de ≈ 10 px (subidos a 11 px).
6. SVG del logotipo para `fundamentos/assets/`.

Este archivo pasa a `implementado` (congelado) cuando se cierre esa verificación o el usuario la descarte.
